# AgentMesh — Hackathon Submission

## Submission description

AgentMesh is a risk-aware AI customer-support council for high-stakes financial questions. Instead of allowing one model to generate and approve its own response, AgentMesh separates policy retrieval, response drafting, deterministic security enforcement, evidence verification, and emotion-aware presentation into explicit roles. A deterministic policy then approves, rewrites, blocks, requests clarification, or creates a ticket in a persistent prototype review queue. Every result includes an inspectable decision trace, and grounded results cite application-controlled policy text. The default system runs as one FastAPI backend with SQLite audit storage and a separate React interface; hosted generation and blockchain anchoring are optional, so unavailable external services do not determine the safety decision.

## Track and users

- Track: Support Chat Bot
- Primary demo domain: financial customer support
- Intended users: customers asking policy-covered questions and prototype reviewers triaging unsafe, urgent, or unsupported cases
- Status: demonstrable hackathon prototype, not a production bank deployment

## Problem

Fluent support answers can still be unsafe or wrong. A customer may be asked for an OTP, receive an invented refund promise, or get a tone-deaf response during an urgent fraud or medical-payment situation. Confidence scores and majority votes do not solve that problem when the same model supplies the answer and the judgment.

## Approach

AgentMesh gives each role a distinct responsibility:

| Role | Evidence produced |
| --- | --- |
| SAGE | Retrieved policy chunks, controlled citations, and a grounded customer-facing draft |
| GUARDIAN | Deterministic and semantic security findings with blocking precedence |
| ORACLE | Claim-level support findings against the exact retrieved policy text |
| EMPATH | Emotion, sentiment, urgency, churn risk, and a fact-preserving tone strategy |

The decision engine does not call this PBFT and does not count duplicated answers. GUARDIAN and ORACLE can veto normal approval. SQLite records the decision trace and powers a prototype review queue for escalation, approval, editing, rejection, and resolution.

## What makes the prototype useful

- Safety rules are enforced in code and cannot be removed by optional model output.
- Citations come from application-controlled retrieval records rather than model-invented source names.
- Unsupported material claims cannot pass merely because their wording is semantically similar.
- Emotion analysis changes how supported facts are presented without changing those facts.
- Critical and unsupported cases create durable tickets that can be demonstrated end to end.
- The same consolidated backend runs directly and is configured for Docker Compose or one disk-backed Render service.
- Groq assistance and blockchain anchoring are optional; SQLite is the primary audit record.

## Demonstration

The recommended walkthrough in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) covers:

1. a grounded refund-policy answer with citations;
2. a critical OTP-sharing question blocked by a deterministic rule;
3. an unsupported Bitcoin guarantee that is not approved;
4. a frustrated, urgent hospital-payment case routed to high-priority review;
5. a prompt-injection and verification-bypass attempt;
6. a reviewer inspecting and resolving a generated ticket.

The interface shows a completed multi-agent decision trace. It does not simulate or claim a streamed live debate.

## Technical outline

- FastAPI and typed Python role contracts
- React 18 and Vite frontend
- SQLite decision/audit and escalation persistence
- JSON policy corpus with controlled source identifiers
- Docker Compose gateway-only runtime
- Render Blueprint with a persistent state disk and readiness health check
- Optional Groq-compatible generation
- Optional best-effort Solidity contract anchor
- Automated Python, frontend-build, and Compose-configuration checks

## Evidence and reproducibility

The repository contains a 65-case labeled evaluation set spanning grounded policy questions, unsupported requests, credential/phishing risks, frustrated customers, urgent fraud, and prompt injection. The checked-in deterministic local [evaluation report](evaluation/report.json), generated with external services disabled, measured 15/15 grounded cases, 10/10 unsupported rejections, 20/20 critical-risk detections, 0/45 critical false positives, and 10/10 urgent-fraud detections. It also exposes current tuning targets: 38/43 retrieval hits and 30/45 escalation precision.

Those figures describe this small labeled dataset and rule-based runner, not production accuracy or human-rated response quality. Its 0.552 ms mean is component-only local evaluation time, not browser or API latency. No public deployment, uptime, user-traffic latency, or blockchain transaction is claimed without a recorded smoke test. Local setup, verification commands, and deployment gates are documented in [README.md](README.md) and [DEPLOY.md](DEPLOY.md).

## Implemented versus future work

Implemented for the prototype:

- grounded support workflow and controlled citations;
- deterministic security precedence and claim verification;
- emotion/urgency analysis and fact-preserving response adaptation;
- explicit six-state decision model;
- SQLite audit/escalation records and prototype review actions;
- consolidated deployment, health/readiness, CI checks, and decision-trace UI.

Future production work:

- authenticated reviewer identities, RBAC, SSO, and case ownership;
- a real bank-approved and versioned policy ingestion process;
- external case-management and notification integrations;
- managed database, distributed throttling, observability, and privacy controls;
- larger blinded evaluation, red-team testing, and human-factors validation.

## Honest limitations

The included policies and tickets are demo data. The shared review key is not production authentication. SQLite limits the default service to one durable instance, the rate limiter is process-local, model-derived emotion signals can be wrong, and optional blockchain anchoring is not a substitute for the application audit database. AgentMesh must not be used for financial decisions or real customer data without domain approval, security review, and operational controls.
