from fastapi import FastAPI
from pydantic import BaseModel
import groq
import os
import json
from rag_engine import RAGEngine

app = FastAPI()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
engine = RAGEngine()


class Query(BaseModel):
    query: str
    session_id: str


@app.post("/analyze")
async def analyze(q: Query):
    try:
        results = engine.search(q.query, n_results=3)
        docs = results.get("documents", [[]])[0] if results.get("documents") else []
        context = "\n".join(docs) if docs else "No relevant documentation found."
    except Exception as e:
        context = f"Vector search error: {str(e)}"

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are SAGE, a technical expert agent. Use ONLY the provided context. "
                    "If the context is insufficient, say INSUFFICIENT_DATA. "
                    "Output strict JSON: {"answer": "...", "confidence": 0-100, "sources": ["..."]}"
                )
            },
            {
                "role": "user",
                "content": f"Context: {context}\n\nCustomer Query: {q.query}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    try:
        output = json.loads(response.choices[0].message.content)
    except Exception:
        output = {
            "answer": response.choices[0].message.content,
            "confidence": 50,
            "sources": []
        }

    return {
        "agent": "sage",
        "session_id": q.session_id,
        "output": output
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "sage"}
