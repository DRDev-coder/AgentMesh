from fastapi import FastAPI
from pydantic import BaseModel
import groq
import os
from fact_checker import FactChecker

app = FastAPI()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
checker = FactChecker()


class CompareRequest(BaseModel):
    session_id: str
    query: str
    sage_answer: str
    context: str = ""


@app.post("/analyze")
async def analyze(data: CompareRequest):
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": "You are ORACLE, a fact-checking agent. Answer based ONLY on provided context. Be concise."
            },
            {
                "role": "user",
                "content": f"Context: {data.context}\n\nQuery: {data.query}"
            }
        ],
        temperature=0.1
    )
    oracle_answer = response.choices[0].message.content

    similarity = checker.compare_answers(data.sage_answer, oracle_answer)
    context_similarity = checker.check_against_context(data.sage_answer, data.context)

    hallucination_flag = similarity < 0.65 or context_similarity < 0.5

    return {
        "agent": "oracle",
        "session_id": data.session_id,
        "output": {
            "oracle_answer": oracle_answer,
            "similarity_to_sage": round(similarity, 3),
            "context_alignment": round(context_similarity, 3),
            "hallucination_flag": hallucination_flag,
            "confidence": "HIGH" if similarity > 0.8 else "MEDIUM" if similarity > 0.65 else "LOW",
            "flags": ["HALLUCINATION"] if hallucination_flag else []
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "oracle"}
