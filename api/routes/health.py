from fastapi import APIRouter
import requests

router = APIRouter()

AGENTS = {
    "sage": "http://sage:5000/health",
    "guardian": "http://guardian:5000/health",
    "empath": "http://empath:5000/health",
    "oracle": "http://oracle:5000/health"
}


@router.get("/health")
async def health_check():
    statuses = {}
    for name, url in AGENTS.items():
        try:
            r = requests.get(url, timeout=2)
            statuses[name] = r.json()
        except Exception:
            statuses[name] = {"status": "unreachable"}
    return {"gateway": "healthy", "agents": statuses}
