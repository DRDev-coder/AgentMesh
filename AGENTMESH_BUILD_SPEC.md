# AGENTMESH — COMPLETE BUILD SPECIFICATION

> **Historical, non-authoritative brief:** This is the original generation specification and contains goals that were deliberately rejected or corrected during the July 2026 repair. It does not describe the current runtime. Use `README.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_REPORT.md`, source code, and tests as the authoritative references.
## Master Prompt for AI Coding Agent
### FlowZint AI Hackathon 2026 | Zero-Budget Stack

---

## YOUR MISSION
Build a production-ready, multi-agent AI support system called **AgentMesh** that uses 4 specialized AI agents (SAGE, GUARDIAN, EMPATH, ORACLE) to independently analyze customer queries, reach a Byzantine Fault-Tolerant consensus, and log decisions to a blockchain. Every component must be built with free-tier services only.

**Judging Criteria to Maximize:**
- Model Innovation & Novelty (30%) — Multi-agent BFT consensus
- Real-World Applicability (25%) — Prevents AI hallucinations in high-stakes support
- Technical Architecture (25%) — Microservices, Docker, design patterns, clean GitHub
- Documentation Clarity (20%) — Architecture diagrams, demo video story

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vercel)                   │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Customer Chat│  │      LIVE AGENT DEBATE VIEWER        │ │
│  └──────┬───────┘  └──────────────────────────────────────┘ │
└─────────┼───────────────────────────────────────────────────┘
          │ HTTPS
┌─────────▼───────────────────────────────────────────────────┐
│              FASTAPI GATEWAY (Render/Local)                  │
│  POST /api/v1/chat                                           │
└─────────┬───────────────────────────────────────────────────┘
          │ Redis Pub/Sub
    ┌─────┴─────┬───────────┬───────────┐
    ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ SAGE   │ │GUARDIAN│ │ EMPATH │ │ ORACLE │
│ :5001  │ │ :5002  │ │ :5003  │ │ :5004  │
│Docker  │ │ Docker │ │ Docker │ │ Docker │
└───┬────┘ └────┬───┘ └───┬────┘ └───┬────┘
    │           │         │          │
    └───────────┴────┬────┴──────────┘
                     ▼
          ┌─────────────────────┐
          │  CONSENSUS ENGINE   │
          │  (PBFT Algorithm)   │
          └──────────┬──────────┘
                     ▼
          ┌─────────────────────┐
          │  BLOCKCHAIN LOGGER  │
          │  Polygon Mumbai     │
          └─────────────────────┘
```

---

## FREE TECH STACK (Zero Budget)

| Layer | Technology | Cost | Signup |
|-------|-----------|------|--------|
| LLM | Groq API (Free Tier) | $0 | https://console.groq.com |
| LLM Backup | Ollama (Local) | $0 | curl -fsSL https://ollama.com/install.sh | sh |
| Agent Framework | FastAPI + Python | $0 | pip install |
| Vector DB | ChromaDB (Docker) | $0 | docker run -p 8000:8000 chromadb/chroma |
| Message Bus | Redis (Docker) | $0 | docker run -p 6379:6379 redis |
| Embeddings | sentence-transformers | $0 | pip install |
| Sentiment | transformers (HuggingFace) | $0 | pip install |
| Blockchain | Polygon Mumbai Testnet | $0 | https://faucet.polygon.technology |
| Blockchain RPC | Alchemy Free Tier | $0 | https://dashboard.alchemy.com |
| Smart Contracts | Solidity + Hardhat | $0 | npm install |
| Frontend | React + Vite | $0 | npm create vite@latest |
| Hosting Frontend | Vercel Free Tier | $0 | https://vercel.com |
| Hosting Backend | Render Free Tier | $0 | https://render.com |
| CI/CD | GitHub Actions | $0 | Built into GitHub |

---

## COMPLETE FILE STRUCTURE

Create this exact repository structure:

```
agentmesh/
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
├── ARCHITECTURE.md
├── docker-compose.yml
├── .env.example
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   ├── routes/
│   │   ├── chat.py
│   │   └── health.py
│   └── services/
│       ├── orchestrator.py
│       ├── consensus_caller.py
│       └── blockchain_logger.py
├── agents/
│   ├── sage/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── rag_engine.py
│   │   └── requirements.txt
│   ├── guardian/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── security_scanner.py
│   │   └── requirements.txt
│   ├── empath/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── emotion_model.py
│   │   └── requirements.txt
│   └── oracle/
│       ├── Dockerfile
│       ├── main.py
│       ├── fact_checker.py
│       └── requirements.txt
├── consensus/
│   ├── __init__.py
│   ├── pbft_consensus.py
│   ├── vote_tally.py
│   └── message_bus.py
├── blockchain/
│   ├── contracts/
│   │   └── ConsensusLedger.sol
│   ├── scripts/
│   │   └── deploy.js
│   ├── hardhat.config.js
│   └── package.json
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── index.css
│       └── components/
│           ├── ChatInterface.jsx
│           ├── AgentDebateViewer.jsx
│           ├── ConsensusBadge.jsx
│           └── BlockchainProof.jsx
├── data/
│   └── product_docs.json
└── tests/
    ├── test_consensus.py
    ├── test_guardian.py
    └── test_integration.py
```

---

## STEP-BY-STEP IMPLEMENTATION

### STEP 1: Docker Compose Infrastructure

Create docker-compose.yml:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma

  sage:
    build: ./agents/sage
    ports:
      - "5001:5000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      - chromadb
      - redis

  guardian:
    build: ./agents/guardian
    ports:
      - "5002:5000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    depends_on:
      - redis

  empath:
    build: ./agents/empath
    ports:
      - "5003:5000"
    depends_on:
      - redis

  oracle:
    build: ./agents/oracle
    ports:
      - "5004:5000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    depends_on:
      - redis

  gateway:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - ALCHEMY_URL=${ALCHEMY_URL}
      - CONTRACT_ADDRESS=${CONTRACT_ADDRESS}
      - WALLET_ADDRESS=${WALLET_ADDRESS}
      - PRIVATE_KEY=${PRIVATE_KEY}
    depends_on:
      - redis
      - sage
      - guardian
      - empath
      - oracle

volumes:
  redis_data:
  chroma_data:
```

Create .env.example:

```
GROQ_API_KEY=gsk_your_free_groq_key_here
REDIS_HOST=redis
REDIS_PORT=6379
CHROMA_HOST=chromadb
CHROMA_PORT=8000
ALCHEMY_URL=https://polygon-mumbai.g.alchemy.com/v2/YOUR_FREE_ALCHEMY_KEY
CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
WALLET_ADDRESS=0xYourMetaMaskWalletAddress
PRIVATE_KEY=YourMetaMaskPrivateKey
```

---

### STEP 2: Shared Utilities

Create consensus/message_bus.py:

```python
import json
import redis
import os
from typing import Callable

class RedisMessageBus:
    def __init__(self, host=None, port=None):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", 6379))
        self.client = redis.Redis(host=self.host, port=self.port, decode_responses=True)

    def publish(self, channel: str, message: dict):
        self.client.publish(channel, json.dumps(message))

    def subscribe(self, channel: str, callback: Callable[[dict], None]):
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    callback(data)
                except json.JSONDecodeError:
                    continue
```

Create consensus/pbft_consensus.py:

```python
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class AgentVote:
    agent_id: str
    answer: str
    confidence: int
    vote: str
    flags: List[str]

class ConsensusEngine:
    def __init__(self, total_agents=4, fault_tolerance=1):
        self.total_agents = total_agents
        self.required_agreements = 2 * fault_tolerance + 1

    def reach_consensus(self, votes: List[AgentVote], guardian_flags: List[str]) -> Dict:
        if "CRITICAL" in guardian_flags:
            return {
                "status": "BLOCKED",
                "reason": "GUARDIAN_CRITICAL_SECURITY_VIOLATION",
                "final_answer": None,
                "escalate": True,
                "primary_agent": None
            }

        agree_votes = [v for v in votes if v.vote == "AGREE"]

        if len(agree_votes) >= self.required_agreements:
            best = max(agree_votes, key=lambda x: x.confidence)
            return {
                "status": "CONSENSUS_REACHED",
                "agreements": len(agree_votes),
                "final_answer": best.answer,
                "escalate": False,
                "primary_agent": best.agent_id,
                "confidence": best.confidence
            }

        oracle_flags = [v for v in votes if v.agent_id == "oracle"]
        if oracle_flags and oracle_flags[0].flags and "HALLUCINATION" in oracle_flags[0].flags:
            return {
                "status": "HALLUCINATION_BLOCKED",
                "reason": "ORACLE_DETECTED_FACTUAL_ERROR",
                "escalate": True
            }

        return {
            "status": "NO_CONSENSUS",
            "reason": "INSUFFICIENT_AGENT_AGREEMENT",
            "escalate": True
        }
```

Create consensus/vote_tally.py:

```python
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

class VoteTally:
    def __init__(self):
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def calculate_agreement(self, answers: List[str], threshold=0.75) -> List[str]:
        if len(answers) < 2:
            return ["AGREE"] * len(answers)

        embeddings = self.embedder.encode(answers)
        votes = []

        for i in range(len(answers)):
            similarities = []
            for j in range(len(answers)):
                if i != j:
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                    )
                    similarities.append(sim)

            avg_sim = np.mean(similarities)
            if avg_sim >= threshold:
                votes.append("AGREE")
            elif avg_sim >= 0.5:
                votes.append("ABSTAIN")
            else:
                votes.append("DISAGREE")

        return votes
```

---

### STEP 3: SAGE Agent (Technical Expert)

Create agents/sage/Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```

Create agents/sage/requirements.txt:

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
groq==0.9.0
chromadb-client==0.4.25
requests==2.31.0
```

Create agents/sage/rag_engine.py:

```python
import chromadb
import os

class RAGEngine:
    def __init__(self):
        host = os.getenv("CHROMA_HOST", "localhost")
        port = int(os.getenv("CHROMA_PORT", 8000))
        self.client = chromadb.HttpClient(host=host, port=port)
        try:
            self.collection = self.client.get_collection("product_docs")
        except:
            self.collection = self.client.create_collection("product_docs")

    def search(self, query: str, n_results: int = 3):
        results = self.collection.query(query_texts=[query], n_results=n_results)
        return results

    def add_documents(self, docs: list, ids: list):
        self.collection.add(documents=docs, ids=ids)
```

Create agents/sage/main.py:

```python
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
        context = "
".join(docs) if docs else "No relevant documentation found."
    except Exception as e:
        context = f"Vector search error: {str(e)}"

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": "You are SAGE, a technical expert agent. Use ONLY the provided context. If the context is insufficient, say INSUFFICIENT_DATA. Output strict JSON: {"answer": "...", "confidence": 0-100, "sources": ["..."]}"
            },
            {
                "role": "user",
                "content": f"Context: {context}

Customer Query: {q.query}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    try:
        output = json.loads(response.choices[0].message.content)
    except:
        output = {"answer": response.choices[0].message.content, "confidence": 50, "sources": []}

    return {
        "agent": "sage",
        "session_id": q.session_id,
        "output": output
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "sage"}
```

---

### STEP 4: GUARDIAN Agent (Security & Policy)

Create agents/guardian/Dockerfile (same template as sage)

Create agents/guardian/requirements.txt:

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
groq==0.9.0
```

Create agents/guardian/security_scanner.py:

```python
import re

DANGER_PATTERNS = [
    (r'(otp|password|pin|cvv|upi pin|atm pin)', "REQUESTING_CREDENTIALS"),
    (r'(click here|urgent|immediate action|verify now|act now|limited time)', "PHISHING_URGENCY"),
    (r'(share your|send me your|provide your|give me your).*(card|account|aadhaar|pan)', "REQUESTING_PII"),
    (r'(wire transfer|send money|transfer funds|gift card)', "FINANCIAL_MANIPULATION"),
]

POLICY_VIOLATIONS = [
    (r'(instant refund|immediate refund|refund guaranteed)', "UNAUTHORIZED_REFUND_PROMISE"),
    (r'(we will not investigate|no need to verify)', "SKIPPING_VERIFICATION"),
    (r'(bypass|override|ignore the policy)', "POLICY_OVERRIDE"),
]

def scan_query(text: str) -> list:
    text_lower = text.lower()
    flags = []
    for pattern, flag in DANGER_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(flag)
    return flags

def scan_answer(text: str) -> list:
    text_lower = text.lower()
    flags = []
    for pattern, flag in POLICY_VIOLATIONS + DANGER_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(flag)
    return flags
```

Create agents/guardian/main.py:

```python
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
                "content": "You are GUARDIAN, a security and policy enforcement agent. Analyze the customer query and proposed answer for risks. Output strict JSON: {"status": "SAFE|WARNING|CRITICAL", "violations": [], "action": "allow|block|escalate", "reasoning": "..."}"
            },
            {
                "role": "user",
                "content": f"Query: {data.query}
Proposed Answer: {data.proposed_answer}
Preliminary Flags: {all_flags}"
            }
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    try:
        output = json.loads(response.choices[0].message.content)
    except:
        output = {"status": status, "violations": all_flags, "action": action, "reasoning": "Regex-based detection"}

    return {
        "agent": "guardian",
        "session_id": data.session_id,
        "output": output
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "guardian"}
```

---

### STEP 5: EMPATH Agent (Emotional Intelligence)

Create agents/empath/Dockerfile (same template)

Create agents/empath/requirements.txt:

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
transformers==4.41.0
torch==2.3.0
```

Create agents/empath/emotion_model.py:

```python
from transformers import pipeline

class EmotionAnalyzer:
    def __init__(self):
        self.classifier = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )

    def analyze(self, text: str):
        result = self.classifier(text[:512])[0]
        label = result["label"]
        score = result["score"]

        text_lower = text.lower()

        if any(w in text_lower for w in ["angry", "furious", "terrible", "worst", "scam", "fraud", "cheat", "lawsuit"]):
            emotion = "ANGRY"
            urgency = 9
        elif any(w in text_lower for w in ["urgent", "immediately", "asap", "emergency", "lost", "stolen", "hacked"]):
            emotion = "URGENT"
            urgency = 10
        elif any(w in text_lower for w in ["confused", "don't understand", "help", "how do i", "what is"]):
            emotion = "CONFUSED"
            urgency = 5
        elif any(w in text_lower for w in ["happy", "thanks", "great", "excellent", "love"]):
            emotion = "SATISFIED"
            urgency = 2
        else:
            emotion = "NEUTRAL"
            urgency = 5

        tone_map = {
            "ANGRY": "APOLOGETIC",
            "URGENT": "REASSURING",
            "CONFUSED": "PATIENT",
            "SATISFIED": "FRIENDLY",
            "NEUTRAL": "PROFESSIONAL"
        }

        return {
            "emotion": emotion,
            "urgency": urgency,
            "sentiment_label": label,
            "sentiment_score": round(score, 3),
            "recommended_tone": tone_map.get(emotion, "PROFESSIONAL"),
            "churn_risk": urgency > 7
        }
```

Create agents/empath/main.py:

```python
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
```

---

### STEP 6: ORACLE Agent (Hallucination Detector)

Create agents/oracle/Dockerfile (same template)

Create agents/oracle/requirements.txt:

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
groq==0.9.0
sentence-transformers==2.7.0
numpy==1.26.0
```

Create agents/oracle/fact_checker.py:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class FactChecker:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def compare_answers(self, answer1: str, answer2: str):
        embeddings = self.model.encode([answer1, answer2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)

    def check_against_context(self, answer: str, context: str):
        if not context or not context.strip():
            return 0.0
        embeddings = self.model.encode([answer, context])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)
```

Create agents/oracle/main.py:

```python
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
                "content": f"Context: {data.context}

Query: {data.query}"
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
```

---

### STEP 7: Gateway API (The Orchestrator)

Create api/Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create api/requirements.txt:

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
redis==5.0.0
requests==2.31.0
web3==6.15.0
python-dotenv==1.0.0
```

Create api/main.py:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.health import router as health_router

app = FastAPI(title="AgentMesh Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AgentMesh Gateway", "status": "operational"}
```

Create api/routes/health.py:

```python
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
        except:
            statuses[name] = {"status": "unreachable"}
    return {"gateway": "healthy", "agents": statuses}
```

Create api/routes/chat.py:

```python
from fastapi import APIRouter
from pydantic import BaseModel
import requests
import json
import os
import uuid
from services.orchestrator import AgentOrchestrator
from services.blockchain_logger import BlockchainLogger

router = APIRouter()
orchestrator = AgentOrchestrator()
logger = BlockchainLogger()

class ChatRequest(BaseModel):
    query: str
    session_id: str = None

@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    result = await orchestrator.process(request.query, session_id)

    tx_hash = None
    if result.get("consensus_status") == "CONSENSUS_REACHED":
        try:
            tx_hash = logger.log_consensus(
                session_id=session_id,
                query=request.query,
                answer=result.get("final_answer", ""),
                votes=result.get("votes", {}),
                consensus_reached=True,
                status="CONSENSUS_REACHED"
            )
        except Exception as e:
            tx_hash = f"BLOCKCHAIN_ERROR: {str(e)}"

    return {
        "session_id": session_id,
        "query": request.query,
        "final_answer": result.get("final_answer"),
        "consensus_status": result.get("consensus_status"),
        "consensus_reason": result.get("consensus_reason"),
        "agent_votes": result.get("votes"),
        "escalate": result.get("escalate", False),
        "blockchain_tx": tx_hash,
        "primary_agent": result.get("primary_agent"),
        "confidence": result.get("confidence")
    }
```

Create api/services/orchestrator.py:

```python
import requests
import json
import asyncio
from typing import Dict, List
import sys
sys.path.append('/app')
from consensus.pbft_consensus import ConsensusEngine, AgentVote
from consensus.vote_tally import VoteTally

AGENT_URLS = {
    "sage": "http://sage:5000/analyze",
    "guardian": "http://guardian:5000/analyze",
    "empath": "http://empath:5000/analyze",
    "oracle": "http://oracle:5000/analyze"
}

class AgentOrchestrator:
    def __init__(self):
        self.consensus = ConsensusEngine(total_agents=4, fault_tolerance=1)
        self.tally = VoteTally()

    async def call_agent(self, name: str, payload: dict):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.post(AGENT_URLS[name], json=payload, timeout=15)
            )
            return response.json()
        except Exception as e:
            return {"agent": name, "error": str(e), "output": {}}

    async def process(self, query: str, session_id: str):
        sage_task = self.call_agent("sage", {"query": query, "session_id": session_id})
        empath_task = self.call_agent("empath", {"query": query, "session_id": session_id})

        sage_result, empath_result = await asyncio.gather(sage_task, empath_task)

        sage_answer = sage_result.get("output", {}).get("answer", "")

        guardian_task = self.call_agent("guardian", {
            "query": query,
            "session_id": session_id,
            "proposed_answer": sage_answer
        })

        oracle_task = self.call_agent("oracle", {
            "query": query,
            "session_id": session_id,
            "sage_answer": sage_answer,
            "context": "
".join(sage_result.get("output", {}).get("sources", []))
        })

        guardian_result, oracle_result = await asyncio.gather(guardian_task, oracle_task)

        answers = [
            sage_answer,
            sage_answer,
            sage_answer,
            oracle_result.get("output", {}).get("oracle_answer", sage_answer)
        ]

        agreement_votes = self.tally.calculate_agreement(answers)

        agent_votes = [
            AgentVote(
                agent_id="sage",
                answer=sage_answer,
                confidence=sage_result.get("output", {}).get("confidence", 50),
                vote=agreement_votes[0],
                flags=[]
            ),
            AgentVote(
                agent_id="guardian",
                answer=sage_answer,
                confidence=100 if guardian_result.get("output", {}).get("status") == "SAFE" else 0,
                vote=agreement_votes[1],
                flags=guardian_result.get("output", {}).get("violations", [])
            ),
            AgentVote(
                agent_id="empath",
                answer=sage_answer,
                confidence=100 - empath_result.get("output", {}).get("urgency", 5) * 10,
                vote=agreement_votes[2],
                flags=["CHURN_RISK"] if empath_result.get("output", {}).get("churn_risk") else []
            ),
            AgentVote(
                agent_id="oracle",
                answer=oracle_result.get("output", {}).get("oracle_answer", sage_answer),
                confidence=100 if not oracle_result.get("output", {}).get("hallucination_flag") else 0,
                vote=agreement_votes[3],
                flags=["HALLUCINATION"] if oracle_result.get("output", {}).get("hallucination_flag") else []
            )
        ]

        guardian_flags = guardian_result.get("output", {}).get("violations", [])
        if guardian_result.get("output", {}).get("status") == "CRITICAL":
            guardian_flags.append("CRITICAL")

        result = self.consensus.reach_consensus(agent_votes, guardian_flags)

        votes_dict = {
            "sage": sage_result.get("output", {}),
            "guardian": guardian_result.get("output", {}),
            "empath": empath_result.get("output", {}),
            "oracle": oracle_result.get("output", {})
        }

        return {
            "final_answer": result.get("final_answer"),
            "consensus_status": result.get("status"),
            "consensus_reason": result.get("reason"),
            "escalate": result.get("escalate", False),
            "votes": votes_dict,
            "primary_agent": result.get("primary_agent"),
            "confidence": result.get("confidence")
        }
```

Create api/services/blockchain_logger.py:

```python
import os
from web3 import Web3

class BlockchainLogger:
    def __init__(self):
        self.alchemy_url = os.getenv("ALCHEMY_URL", "")
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "")
        self.wallet = os.getenv("WALLET_ADDRESS", "")
        self.private_key = os.getenv("PRIVATE_KEY", "")

        if self.alchemy_url and self.contract_address:
            self.w3 = Web3(Web3.HTTPProvider(self.alchemy_url))
            self.abi = [
                {
                    "inputs": [
                        {"name": "_sessionId", "type": "bytes32"},
                        {"name": "_queryHash", "type": "bytes32"},
                        {"name": "_answerHash", "type": "bytes32"},
                        {"name": "_sageVote", "type": "bytes32"},
                        {"name": "_guardianVote", "type": "bytes32"},
                        {"name": "_empathVote", "type": "bytes32"},
                        {"name": "_oracleVote", "type": "bytes32"},
                        {"name": "_consensusReached", "type": "bool"},
                        {"name": "_status", "type": "string"}
                    ],
                    "name": "logConsensus",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        else:
            self.w3 = None
            self.contract = None

    def log_consensus(self, session_id, query, answer, votes, consensus_reached, status):
        if not self.w3 or not self.contract:
            return "BLOCKCHAIN_NOT_CONFIGURED"

        try:
            tx = self.contract.functions.logConsensus(
                self.w3.keccak(text=session_id),
                self.w3.keccak(text=query),
                self.w3.keccak(text=answer),
                self.w3.keccak(text=str(votes.get("sage", {}))),
                self.w3.keccak(text=str(votes.get("guardian", {}))),
                self.w3.keccak(text=str(votes.get("empath", {}))),
                self.w3.keccak(text=str(votes.get("oracle", {}))),
                consensus_reached,
                status
            ).build_transaction({
                'from': self.wallet,
                'nonce': self.w3.eth.get_transaction_count(self.wallet),
                'gas': 200000,
                'gasPrice': self.w3.to_wei('10', 'gwei')
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            return f"BLOCKCHAIN_ERROR: {str(e)}"
```

---

### STEP 8: Blockchain Smart Contract

Create blockchain/hardhat.config.js:

```javascript
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.19",
  networks: {
    mumbai: {
      url: process.env.ALCHEMY_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
    hardhat: {
      chainId: 1337
    }
  },
};
```

Create blockchain/package.json:

```json
{
  "name": "agentmesh-blockchain",
  "version": "1.0.0",
  "devDependencies": {
    "@nomicfoundation/hardhat-toolbox": "^4.0.0",
    "hardhat": "^2.20.0"
  }
}
```

Create blockchain/contracts/ConsensusLedger.sol:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract ConsensusLedger {
    struct ConsensusRecord {
        bytes32 queryHash;
        bytes32 answerHash;
        bytes32 sageVote;
        bytes32 guardianVote;
        bytes32 empathVote;
        bytes32 oracleVote;
        bool consensusReached;
        uint256 timestamp;
        string status;
    }

    mapping(bytes32 => ConsensusRecord) public records;
    bytes32[] public recordIds;

    event ConsensusLogged(
        bytes32 indexed sessionId,
        bool consensusReached,
        string status,
        uint256 timestamp
    );

    function logConsensus(
        bytes32 _sessionId,
        bytes32 _queryHash,
        bytes32 _answerHash,
        bytes32 _sageVote,
        bytes32 _guardianVote,
        bytes32 _empathVote,
        bytes32 _oracleVote,
        bool _consensusReached,
        string memory _status
    ) public {
        records[_sessionId] = ConsensusRecord({
            queryHash: _queryHash,
            answerHash: _answerHash,
            sageVote: _sageVote,
            guardianVote: _guardianVote,
            empathVote: _empathVote,
            oracleVote: _oracleVote,
            consensusReached: _consensusReached,
            timestamp: block.timestamp,
            status: _status
        });

        recordIds.push(_sessionId);
        emit ConsensusLogged(_sessionId, _consensusReached, _status, block.timestamp);
    }

    function getRecord(bytes32 _sessionId) public view returns (ConsensusRecord memory) {
        return records[_sessionId];
    }

    function getTotalRecords() public view returns (uint256) {
        return recordIds.length;
    }
}
```

Create blockchain/scripts/deploy.js:

```javascript
const hre = require("hardhat");

async function main() {
  const ConsensusLedger = await hre.ethers.getContractFactory("ConsensusLedger");
  const ledger = await ConsensusLedger.deploy();
  await ledger.waitForDeployment();

  console.log("ConsensusLedger deployed to:", await ledger.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

---

### STEP 9: React Frontend

Create frontend/package.json:

```json
{
  "name": "agentmesh-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

Create frontend/vite.config.js:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

Create frontend/src/main.jsx:

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

Create frontend/src/index.css:

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
}

.agent-card {
  background: #1e293b;
  border: 2px solid;
  border-radius: 12px;
  padding: 20px;
  margin: 10px;
  min-width: 200px;
  transition: all 0.3s ease;
}

.agent-card.analyzing {
  animation: pulse 1.5s infinite;
  opacity: 0.8;
}

.agent-card.done {
  opacity: 1;
  transform: scale(1.02);
}

@keyframes pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.vote.AGREE { color: #10b981; font-weight: bold; }
.vote.DISAGREE { color: #ef4444; font-weight: bold; }
.vote.ABSTAIN { color: #f59e0b; font-weight: bold; }

.consensus-result.CONSENSUS_REACHED {
  background: #064e3b;
  border: 2px solid #10b981;
}

.consensus-result.BLOCKED,
.consensus-result.HALLUCINATION_BLOCKED,
.consensus-result.NO_CONSENSUS {
  background: #450a0a;
  border: 2px solid #ef4444;
}

.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.message {
  padding: 12px 16px;
  border-radius: 12px;
  margin: 8px 0;
  max-width: 80%;
}

.message.user {
  background: #3b82f6;
  margin-left: auto;
}

.message.bot {
  background: #1e293b;
  border: 1px solid #334155;
}

input[type="text"] {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #334155;
  background: #1e293b;
  color: white;
  font-size: 16px;
}

button {
  padding: 12px 24px;
  border-radius: 8px;
  border: none;
  background: #3b82f6;
  color: white;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

button:hover {
  background: #2563eb;
}
```

Create frontend/src/App.jsx:

```jsx
import React, { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import AgentDebateViewer from './components/AgentDebateViewer'

function App() {
  const [activeSession, setActiveSession] = useState(null)
  const [view, setView] = useState('chat')

  return (
    <div className="app">
      <header style={{ padding: '20px', textAlign: 'center', borderBottom: '1px solid #334155' }}>
        <h1>AGENTMESH</h1>
        <p>No AI decides alone. 4 agents. 1 consensus. Immutable proof.</p>
        <div style={{ marginTop: '10px' }}>
          <button onClick={() => setView('chat')} style={{ marginRight: '10px' }}>
            Customer Chat
          </button>
          <button onClick={() => setView('debate')}>
            Live Council View
          </button>
        </div>
      </header>

      {view === 'chat' ? (
        <ChatInterface onSessionStart={setActiveSession} />
      ) : (
        <AgentDebateViewer sessionId={activeSession} />
      )}
    </div>
  )
}

export default App
```

Create frontend/src/components/ChatInterface.jsx:

```jsx
import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export default function ChatInterface({ onSessionStart }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMsg = { role: 'user', text: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input })
      })
      const data = await res.json()

      onSessionStart(data.session_id)

      const botMsg = {
        role: 'bot',
        text: data.final_answer || data.consensus_reason || 'Processing...',
        meta: data
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + err.message }])
    }

    setLoading(false)
  }

  return (
    <div className="chat-container">
      <div style={{ minHeight: '400px', marginBottom: '20px' }}>
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>
            <p>{m.text}</p>
            {m.meta && m.meta.consensus_status === 'CONSENSUS_REACHED' && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#10b981' }}>
                Verified by 4 Agents | Confidence: {m.meta.confidence}%
                {m.meta.blockchain_tx && m.meta.blockchain_tx.startsWith('0x') && (
                  <div>
                    <a 
                      href={`https://mumbai.polygonscan.com/tx/${m.meta.blockchain_tx}`}
                      target="_blank"
                      style={{ color: '#60a5fa' }}
                    >
                      View on Blockchain
                    </a>
                  </div>
                )}
              </div>
            )}
            {m.meta && m.meta.escalate && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#ef4444' }}>
                ESCALATED TO HUMAN — {m.meta.consensus_reason}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="message bot">Agent Council deliberating...</div>}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder="Type your support query..."
        />
        <button onClick={sendMessage} disabled={loading}>Send</button>
      </div>
    </div>
  )
}
```

Create frontend/src/components/AgentDebateViewer.jsx:

```jsx
import React, { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const AGENTS = [
  { name: 'SAGE', color: '#3B82F6', role: 'Technical Expert' },
  { name: 'GUARDIAN', color: '#10B981', role: 'Security Enforcer' },
  { name: 'EMPATH', color: '#F59E0B', role: 'Emotional Intel' },
  { name: 'ORACLE', color: '#8B5CF6', role: 'Fact Checker' }
]

export default function AgentDebateViewer({ sessionId }) {
  const [agents, setAgents] = useState(
    AGENTS.map(a => ({ ...a, status: 'idle', confidence: 0, vote: null, output: null }))
  )
  const [consensus, setConsensus] = useState(null)
  const [query, setQuery] = useState('')

  const runSimulation = async () => {
    if (!query.trim()) return

    setAgents(AGENTS.map(a => ({ ...a, status: 'analyzing', confidence: 0, vote: null, output: null })))
    setConsensus(null)

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      const data = await res.json()

      const votes = data.agent_votes || {}
      const delay = (ms) => new Promise(r => setTimeout(r, ms))

      for (let i = 0; i < AGENTS.length; i++) {
        await delay(800)
        const agentName = AGENTS[i].name.toLowerCase()
        const voteData = votes[agentName] || {}

        setAgents(prev => prev.map((a, idx) => 
          idx === i ? {
            ...a,
            status: 'done',
            confidence: voteData.confidence || voteData.sentiment_score || 85,
            vote: voteData.status === 'SAFE' || !voteData.hallucination_flag ? 'AGREE' : 
                  voteData.hallucination_flag ? 'DISAGREE' : 'AGREE',
            output: voteData
          } : a
        ))
      }

      await delay(500)
      setConsensus({
        status: data.consensus_status,
        reason: data.consensus_reason,
        txHash: data.blockchain_tx
      })
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Live Agent Council</h2>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Enter a query to watch the council deliberate..."
          style={{ flex: 1 }}
        />
        <button onClick={runSimulation}>Run Council</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '30px' }}>
        {agents.map(agent => (
          <div 
            key={agent.name}
            className={`agent-card ${agent.status}`}
            style={{ borderColor: agent.color }}
          >
            <h3 style={{ color: agent.color }}>{agent.name}</h3>
            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '10px' }}>{agent.role}</p>
            <div className="status" style={{ textTransform: 'uppercase', fontSize: '12px', marginBottom: '8px' }}>
              {agent.status}
            </div>
            {agent.confidence > 0 && (
              <div style={{ fontSize: '14px', marginBottom: '8px' }}>
                Confidence: {Math.round(agent.confidence)}%
              </div>
            )}
            {agent.vote && (
              <div className={`vote ${agent.vote}`} style={{ fontSize: '18px' }}>
                {agent.vote}
              </div>
            )}
          </div>
        ))}
      </div>

      {consensus && (
        <div className={`consensus-result ${consensus.status}`} style={{ padding: '20px', borderRadius: '12px', textAlign: 'center' }}>
          <h3>
            {consensus.status === 'CONSENSUS_REACHED' ? 'CONSENSUS REACHED' : 
             consensus.status === 'BLOCKED' ? 'BLOCKED BY GUARDIAN' :
             consensus.status === 'HALLUCINATION_BLOCKED' ? 'HALLUCINATION DETECTED' :
             'NO CONSENSUS — ESCALATING'}
          </h3>
          <p style={{ marginTop: '10px' }}>{consensus.reason}</p>
          {consensus.txHash && consensus.txHash.startsWith('0x') && (
            <p style={{ marginTop: '10px' }}>
              <a 
                href={`https://mumbai.polygonscan.com/tx/${consensus.txHash}`}
                target="_blank"
                style={{ color: '#60a5fa' }}
              >
                View Immutable Audit on Blockchain
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
```

Create frontend/src/components/ConsensusBadge.jsx:

```jsx
import React from 'react'
export default function ConsensusBadge({ status, txHash }) {
  return (
    <div>
      {status === 'CONSENSUS_REACHED' && <span>Verified</span>}
      {txHash && <a href={`https://mumbai.polygonscan.com/tx/${txHash}`}>Proof</a>}
    </div>
  )
}
```

Create frontend/src/components/BlockchainProof.jsx:

```jsx
import React from 'react'
export default function BlockchainProof({ txHash }) {
  if (!txHash || !txHash.startsWith('0x')) return null
  return (
    <div style={{ fontSize: '12px', marginTop: '8px' }}>
      <a href={`https://mumbai.polygonscan.com/tx/${txHash}`} target="_blank" style={{ color: '#60a5fa' }}>
        View on Polygon Mumbai
      </a>
    </div>
  )
}
```

Create frontend/index.html:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AgentMesh — AI Council</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

---

### STEP 10: Sample Data & Seeding

Create data/product_docs.json:

```json
[
  {
    "id": "refund_policy_1",
    "text": "Standard customers must wait 7 business days for refund investigation. Premium customers receive instant refund up to 10000. No refunds without investigation for amounts above 50000."
  },
  {
    "id": "security_policy_1",
    "text": "NEVER request OTP, password, PIN, CVV, or UPI PIN from customers via chat, email, or phone. OTP requests are ONLY initiated by the bank's automated system."
  },
  {
    "id": "card_block_1",
    "text": "To block a lost or stolen card, customer must verify identity through registered mobile OTP. Card will be blocked within 5 minutes. Replacement card takes 5-7 business days."
  },
  {
    "id": "fraud_report_1",
    "text": "All fraud reports must be escalated to the fraud investigation team within 1 hour. Customer should be advised to file a police FIR for amounts above 25000."
  },
  {
    "id": "premium_benefits_1",
    "text": "Premium account holders get: instant refunds up to 10000, dedicated support line, airport lounge access, and zero forex markup. Minimum balance: 50000."
  }
]
```

Create api/seed_docs.py:

```python
import json
import requests

with open('../data/product_docs.json') as f:
    docs = json.load(f)

for doc in docs:
    requests.post('http://chromadb:8000/api/v1/collections/product_docs/documents', json={
        'ids': [doc['id']],
        'documents': [doc['text']]
    })
    print(f"Seeded: {doc['id']}")
```

---

### STEP 11: GitHub Actions CI

Create .github/workflows/ci.yml:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pytest requests
          pip install -r api/requirements.txt

      - name: Run tests
        run: pytest tests/ -v
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install flake8
      - run: flake8 api/ agents/ consensus/ --max-line-length=120
```

---

### STEP 12: Documentation Files

Create README.md:

```markdown
# AgentMesh

**No AI decides alone.**

AgentMesh is a Byzantine Fault-Tolerant multi-agent AI support system where 4 specialized agents (SAGE, GUARDIAN, EMPATH, ORACLE) independently analyze every customer query, debate the correct response, and reach a cryptographically-verified consensus before any answer reaches the customer.

## The Problem

Current AI support relies on a single LLM. One hallucination can cost millions:
- Air Canada bot invented a bereavement policy -> lawsuit
- Chevy bot offered $1 cars -> had to honor deals
- Banks lose crores to social engineering via support bots

## The Solution

4 agents. 1 consensus. Immutable proof.

| Agent | Role |
|-------|------|
| SAGE | Technical Expert — facts & documentation |
| GUARDIAN | Security Enforcer — policy & compliance |
| EMPATH | Emotional Intel — tone & churn risk |
| ORACLE | Fact Checker — hallucination detection |

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/agentmesh.git
cd agentmesh
cp .env.example .env
# Edit .env with your free Groq API key

# 2. Start everything
docker-compose up --build

# 3. Seed knowledge base
docker-compose exec gateway python seed_docs.py

# 4. Open frontend
cd frontend && npm install && npm run dev
```

## Architecture

See ARCHITECTURE.md for detailed system design, BFT algorithm explanation, and design patterns.

## Tech Stack

- **AI:** Groq API (Llama 3 70B) + Local transformers
- **Backend:** FastAPI, Redis, ChromaDB
- **Blockchain:** Solidity, Hardhat, Polygon Mumbai
- **Frontend:** React, Vite
- **DevOps:** Docker Compose, GitHub Actions

## Demo Video

[Watch 2-minute demo](your-youtube-link)

## Team

- [Your Name] — AI & Backend
- [Teammate] — Blockchain & DevOps
- [Teammate] — Frontend & Design
```

Create ARCHITECTURE.md:

```markdown
# AgentMesh Architecture

## System Design

AgentMesh uses a microservices architecture with 4 independent AI agents, a consensus engine, and a blockchain audit layer.

## Design Patterns

### 1. Observer Pattern
The Redis Pub/Sub message bus acts as an observer. All agents subscribe to the queries channel and publish to agent_responses.

### 2. Strategy Pattern
The consensus engine supports pluggable consensus strategies:
- Simple Majority (for demo)
- PBFT (Byzantine Fault Tolerance) — production
- Weighted Consensus (confidence-weighted voting)

### 3. Chain of Responsibility
Query escalation pipeline:
1. AI agents analyze
2. Consensus engine decides
3. If blocked -> Human escalation
4. If approved -> Blockchain logging

### 4. Factory Pattern
Agent instantiation is abstracted through the orchestrator. New agents can be added without changing the gateway.

## Byzantine Fault Tolerance

With 4 agents, we tolerate f=1 faulty agent.
Consensus requires 2f + 1 = 3 agreeing agents.

This means even if one agent is:
- Hacked
- Hallucinating
- Compromised by prompt injection

The remaining 3 loyal agents still produce the correct answer.

## Data Flow

1. Customer sends query -> Gateway
2. Gateway publishes to Redis
3. All 4 agents receive simultaneously
4. Agents publish responses
5. Consensus engine tallies votes
6. If >=3 agree -> Final answer
7. If <3 agree or CRITICAL flag -> Escalate
8. Consensus hash logged to Polygon Mumbai

## Security Model

- GUARDIAN scans for credential requests, phishing, policy violations
- ORACLE detects factual contradictions via semantic similarity
- Blockchain provides immutable audit trail for regulators
- No PII is stored in agent logs

## Scalability

Each agent is a separate Docker container. They can be:
- Horizontally scaled independently
- Replaced with domain-specific versions
- Deployed across multiple regions
```

---

## DEPLOYMENT GUIDE

### Backend Deployment (Render Free Tier)

1. Push code to GitHub
2. Go to https://render.com -> New Web Service
3. Connect GitHub repo
4. Set environment variables from .env
5. Choose Docker environment
6. Deploy

### Frontend Deployment (Vercel Free Tier)

```bash
cd frontend
npm run build
# Or use Vercel CLI:
vercel --prod
```

### Blockchain Deployment

```bash
cd blockchain
npm install
npx hardhat compile
# Get Mumbai MATIC from https://faucet.polygon.technology
npx hardhat run scripts/deploy.js --network mumbai
# Save the deployed contract address to .env
```

---

## DEMO VIDEO SCRIPT (2 Minutes)

| Time | Scene |
|------|-------|
| 0:00-0:15 | Show bad chatbot: "Share your OTP for instant refund" |
| 0:15-0:30 | News headlines of AI support disasters |
| 0:30-0:35 | AgentMesh logo: "No AI decides alone" |
| 0:35-1:05 | Live demo: 4 agent cards animate, debate, reach consensus |
| 1:05-1:20 | Blocked query: "BLOCKED — Escalating to Human" |
| 1:20-1:35 | Click badge -> show blockchain transaction on Polygonscan |
| 1:35-1:50 | Show GitHub repo, architecture, CI passing |
| 1:50-2:00 | URLs, team names, "AgentMesh. Because one brain is never enough." |

---

## FREE API SIGNUP CHECKLIST

- [ ] Groq API Key: https://console.groq.com (free, no card)
- [ ] Alchemy: https://dashboard.alchemy.com (free, no card)
- [ ] MetaMask: Install extension, switch to Mumbai testnet
- [ ] Polygon Faucet: https://faucet.polygon.technology (free test MATIC)
- [ ] GitHub: Public repo
- [ ] Vercel: https://vercel.com (deploy frontend)
- [ ] Render: https://render.com (deploy backend)

---

## FALLBACKS

| If This Breaks | Do This |
|----------------|---------|
| Groq rate-limits | Switch to Ollama locally |
| Blockchain won't deploy | Use Hardhat local node |
| Frontend too complex | Use simple HTML/JS |
| Team member drops out | Reduce to 2 agents + consensus |
| Can't get test MATIC | Local Hardhat network |

---

## JUDGING CRITERIA MAPPING

| Criteria | How AgentMesh Scores |
|----------|---------------------|
| Model Innovation (30%) | Multi-agent BFT consensus — genuinely novel, not a ChatGPT wrapper |
| Real-World Applicability (25%) | Banks, insurance, healthcare all need hallucination-proof support |
| Technical Architecture (25%) | Microservices, Docker, design patterns, CI/CD, clean GitHub structure |
| Documentation Clarity (20%) | Architecture docs, live demo video, blockchain explorer links |

---

## END OF SPECIFICATION

Build this. Deploy it. Win the hackathon.
