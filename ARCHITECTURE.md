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
3. If blocked → Human escalation
4. If approved → Blockchain logging

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

1. Customer sends query → Gateway
2. Gateway publishes to Redis
3. All 4 agents receive simultaneously
4. Agents publish responses
5. Consensus engine tallies votes
6. If >=3 agree → Final answer
7. If <3 agree or CRITICAL flag → Escalate
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
