from __future__ import annotations

import json
import os

import httpx
from pydantic import BaseModel, ConfigDict, Field

from agents.sage.rag_engine import RAGEngine
from shared.schemas import SageOutput, SourceRecord


class _ModelDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=10000)


class SageService:
    def __init__(self, engine: RAGEngine | None = None):
        self.engine = engine or RAGEngine()
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.base_url = os.getenv(
            "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
        ).rstrip("/")

    @property
    def ready(self) -> bool:
        return self.engine.ready

    async def analyze(self, query: str) -> SageOutput:
        sources = self.engine.search(query, n_results=3)
        if not sources:
            return SageOutput(
                answer=(
                    "I do not have enough approved policy information to answer that "
                    "safely. Please clarify the request or send it to human review."
                ),
                confidence=0,
                citations=[],
                retrieval_quality=0,
                insufficient_data=True,
                generation_mode="deterministic",
            )

        retrieval_quality = max(source.distance_or_similarity for source in sources)
        warnings: list[str] = []
        if self.api_key:
            try:
                answer = await self._generate_with_groq(query, sources)
                mode = "groq"
            except Exception as exc:
                answer = self._deterministic_answer(sources)
                mode = "deterministic_fallback"
                warnings.append(f"model unavailable: {type(exc).__name__}")
        else:
            answer = self._deterministic_answer(sources)
            mode = "deterministic"

        return SageOutput(
            answer=answer,
            confidence=round(min(95.0, 55.0 + (retrieval_quality * 40.0)), 1),
            citations=sources,
            retrieval_quality=retrieval_quality,
            insufficient_data=False,
            generation_mode=mode,
            warnings=warnings,
        )

    @staticmethod
    def _deterministic_answer(sources: list[SourceRecord]) -> str:
        evidence = "\n".join(
            f"- [{source.document_id}] {source.text}" for source in sources
        )
        return f"According to the approved policy:\n{evidence}"

    async def _generate_with_groq(
        self, query: str, sources: list[SourceRecord]
    ) -> str:
        evidence = "\n".join(
            f"[{source.document_id}] {source.text}" for source in sources
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft concise financial-support answers using only the "
                        "approved evidence. Cite source IDs in square brackets. Do not "
                        "invent policy, guarantees, or actions. Return JSON with exactly "
                        "one string field named answer."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Approved evidence:\n{evidence}\n\nCustomer query:\n{query}",
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        timeout = httpx.Timeout(connect=3.0, read=12.0, write=5.0, pool=3.0)
        transport = httpx.AsyncHTTPTransport(retries=1)
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = _ModelDraft.model_validate(json.loads(content))
        return parsed.answer
