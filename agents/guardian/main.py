from fastapi import FastAPI
from pydantic import BaseModel
import groq
import os
import json
from security_scanner import scan_query, scan_answer

app = FastAPI()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))


class AnalyzeRequest(BaseModel):
    session_id: str
    query: str
    proposed_answer: str = ""


@app.post("/analyze")
async def analyze(data: AnalyzeRequest):
    query_flags = scan_query(data.query)
    answer_flags = scan_answer(data.proposed_answer) if data.proposed_answer else []
    all_flags = list(set(query_flags + answer_flags))

    status = "SAFE"
    action = "allow"

    if any(f in ["REQUESTING_CREDENTIALS", "PHISHING_URGENCY", "FINANCIAL_MANIPULATION"] for f in all_flags):
        status = "CRITICAL"
        action = "block"
    elif any(f in ["REQUESTING_PII", "UNAUTHORIZED_REFUND_PROMISE"] for f in all_flags):
        status = "WARNING"
        action = "escalate"

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are GUARDIAN, a security and policy enforcement agent. "
                    "Analyze the customer query and proposed answer for risks. "
                    "Output strict JSON: {"status": "SAFE|WARNING|CRITICAL", "
                    ""violations": [], "action": "allow|block|escalate", "reasoning": "..."}"
                )
            },
            {
                "role": "user",
                "content": f"Query: {data.query}\nProposed Answer: {data.proposed_answer}\nPreliminary Flags: {all_flags}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    try:
        output = json.loads(response.choices[0].message.content)
    except Exception:
        output = {
            "status": status,
            "violations": all_flags,
            "action": action,
            "reasoning": "Regex-based detection"
        }

    return {
        "agent": "guardian",
        "session_id": data.session_id,
        "output": output
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "guardian"}
