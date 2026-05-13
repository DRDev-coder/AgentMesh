# AgentMesh

**No AI decides alone.**

Multi-agent AI support system with Byzantine Fault-Tolerant consensus. 4 specialized agents (SAGE, GUARDIAN, EMPATH, ORACLE) debate and vote before answering. Every decision logged to Polygon Amoy blockchain for immutable audit.

AgentMesh is a Byzantine Fault-Tolerant multi-agent AI support system where 4 specialized agents (SAGE, GUARDIAN, EMPATH, ORACLE) independently analyze every customer query, debate the correct response, and reach a cryptographically-verified consensus before any answer reaches the customer.

## The Problem

Current AI support relies on a single LLM. One hallucination can cost millions:
- Air Canada bot invented a bereavement policy → lawsuit
- Chevy bot offered $1 cars → had to honor deals
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
# .env is already configured with your keys

# 2. Start everything
docker-compose up --build

# 3. Seed knowledge base (in another terminal)
docker-compose exec gateway python /app/api/seed_docs.py

# 4. Open frontend
cd frontend && npm install && npm run dev
```

## Blockchain Setup (3 Options)

### Option A: Public RPC (Easiest — No Signup)
Already configured in `.env`. The app will auto-try these free public endpoints:
- **Ankr**: `https://rpc.ankr.com/polygon_mumbai`
- **PublicNode**: `https://polygon-mumbai-bor-rpc.publicnode.com`
- **MaticVigil**: `https://rpc-mumbai.maticvigil.com`

No account needed. Just get free test MATIC from [Polygon Faucet](https://faucet.polygon.technology).

### Option B: Infura (Free Tier)
1. Go to [infura.io](https://infura.io) → Sign up (free)
2. Create a Polygon Mumbai endpoint
3. Update `.env`: `ALCHEMY_URL=https://polygon-mumbai.infura.io/v3/YOUR_KEY`

### Option C: Local Hardhat (Offline Demo)
Perfect for hackathon demos without internet:
```bash
cd blockchain
npm install
npx hardhat node
# In another terminal:
npx hardhat run scripts/start-local.js --network localhost
```
Then update `.env` with the printed `CONTRACT_ADDRESS` and `ALCHEMY_URL=http://host.docker.internal:8545`.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design, BFT algorithm explanation, and design patterns.

## Tech Stack

- **AI:** Groq API (Llama 3 70B) + Local transformers
- **Backend:** FastAPI, Redis, ChromaDB
- **Blockchain:** Solidity, Hardhat, Polygon Mumbai (or local)
- **Frontend:** React, Vite
- **DevOps:** Docker Compose, GitHub Actions

## Deploy to Production

### Backend (Render Free Tier)
1. Push to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect repo, choose Docker environment
4. Add environment variables from `.env`
5. Deploy

### Frontend (Vercel Free Tier)
```bash
cd frontend
npm run build
# Or use Vercel CLI:
vercel --prod
```

## Demo Video Script (2 Minutes)

| Time | Scene |
|------|-------|
| 0:00-0:15 | Show bad chatbot: "Share your OTP for instant refund" |
| 0:15-0:30 | News headlines of AI support disasters |
| 0:30-0:35 | AgentMesh logo: "No AI decides alone" |
| 0:35-1:05 | Live demo: 4 agent cards animate, debate, reach consensus |
| 1:05-1:20 | Blocked query: "BLOCKED — Escalating to Human" |
| 1:20-1:35 | Click badge → show blockchain transaction on Polygonscan |
| 1:35-1:50 | Show GitHub repo, architecture, CI passing |
| 1:50-2:00 | URLs, team names, "AgentMesh. Because one brain is never enough." |

## Team

- [Your Name] — AI & Backend
- [Teammate] — Blockchain & DevOps
- [Teammate] — Frontend & Design
