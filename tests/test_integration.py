import pytest
import requests

GATEWAY = "http://gateway:8000"


def test_health_endpoint():
    r = requests.get(f"{GATEWAY}/api/v1/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["gateway"] == "healthy"


def test_chat_endpoint():
    payload = {"query": "What is the refund policy?"}
    r = requests.post(f"{GATEWAY}/api/v1/chat", json=payload, timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert "consensus_status" in data
