from fastapi import FastAPI
from pydantic import BaseModel
from emotion_model import EmotionAnalyzer

app = FastAPI()
analyzer = EmotionAnalyzer()


class Query(BaseModel):
    query: str
    session_id: str


@app.post("/analyze")
async def analyze(q: Query):
    result = analyzer.analyze(q.query)
    return {
        "agent": "empath",
        "session_id": q.session_id,
        "output": result
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "empath"}
