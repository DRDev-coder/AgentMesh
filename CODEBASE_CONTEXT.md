# Codebase Context

> **Historical baseline:** Sections below document the repository before the July 2026 repair. The implementation has since been consolidated and corrected. For current runtime behavior, contracts, commands, and limitations, treat `README.md`, `ARCHITECTURE.md`, `IMPLEMENTATION_REPORT.md`, source code, and tests as authoritative. This pre-repair analysis is retained to explain why the changes were made.

This document describes the repository as inspected on 2026-07-16. Runtime code, manifests, and tests are treated as authoritative when they conflict with prose documentation. No secret values were present or are reproduced here.

## 1. Executive Summary

AgentMesh is a hackathon-oriented prototype for bank/customer-support responses. A React client sends a query to a FastAPI gateway, which calls four nominally specialized FastAPI services:

- SAGE retrieves product-policy context from ChromaDB and asks a Groq-hosted Llama model to draft an answer.
- GUARDIAN applies regex security rules and asks the same Groq model to classify risk.
- EMPATH combines a Hugging Face sentiment model with keyword rules for emotion and urgency.
- ORACLE asks Groq for a second answer and compares embeddings to flag possible hallucination.

The gateway then runs a local threshol  d-based `ConsensusEngine` and, only for `CONSENSUS_REACHED`, attempts to hash the result into a Solidity contract. The frontend has a simple chat view and a simulated council/debate view. The main implementation is in `frontend/src/`, `api/`, `agents/`, `consensus/`, and `blockchain/`.

The repository is not currently runnable end to end and must not be treated as production-ready:

1. `agents/sage/main.py` and `agents/guardian/main.py` have confirmed Python syntax errors in their system-prompt string literals. Both containers fail before their FastAPI applications can start.
2. The implemented "PBFT" is not PBFT. It is an in-process 3-vote threshold, and the orchestrator supplies SAGE's answer as the SAGE, GUARDIAN, and EMPATH answers. Those three synthetic copies frequently guarantee agreement without three independent answers.
3. Parsed GUARDIAN LLM output replaces the deterministic regex decision instead of being constrained by it. A model response can therefore discard a deterministic critical flag.
4. `render.yaml` deploys only the gateway and Redis; it does not deploy any agent or ChromaDB service. The gateway's hard-coded agent hostnames cannot work in that topology.
5. There is no authentication, authorization, rate limiting, input-length limit, human-escalation integration, conversation persistence, or production monitoring.
6. Nine isolated consensus/scanner tests passed locally. The two integration tests failed because their hard-coded Docker hostname `gateway` was not resolvable with no stack running. The checked-in CI runs those same integration tests without starting the stack, so its test job is structurally expected to fail. Static parsing also confirmed the two syntax failures above.

The evidence in `AGENTMESH_BUILD_SPEC.md`, placeholder team and clone data in `README.md`, and the feature gaps classify this repository as an incomplete hackathon demo/prototype, not an MVP or production application.

## 2. Product Purpose

### Intended problem and users

The intended problem is reducing unsafe or hallucinated responses from a single support chatbot in high-stakes domains. The sample knowledge base is bank-oriented: refunds, credential handling, card blocking, fraud escalation, and premium-account benefits in `data/product_docs.json`.

Likely target users, based on `README.md`, `ARCHITECTURE.md`, and `AGENTMESH_BUILD_SPEC.md`, are:

- customers asking banking support questions;
- support or risk teams that want unsafe queries escalated;
- demo judges or operators viewing the four-agent decision process;
- auditors following a transaction link to a blockchain record.

### Intended use cases

- Answer a policy question using a small product-document collection.
- Block credential requests, phishing urgency, or financial-manipulation language.
- Detect frustration/urgency and expose a recommended support tone.
- Compare a drafted answer with a second model answer and source context.
- Require three nominal agent agreements before returning a response.
- Hash approved decisions and agent outputs into `ConsensusLedger`.
- Display per-agent output, consensus state, and a Polygon explorer link.

### Actual scope

Only a synchronous request/response demo exists. There is no customer/account system, ticket system, human escalation queue, admin interface, durable chat history, identity layer, policy authoring flow, or audit-record retrieval API. The "live debate" is a client-side timed reveal after one completed `/chat` request, not streaming agent communication (`frontend/src/components/AgentDebateViewer.jsx`, component `AgentDebateViewer`).

## 3. Current Implementation Status

| Area | Status | Implementation evidence |
|---|---|---|
| Product concept and sample policies | Complete for a demo | `README.md`, `ARCHITECTURE.md`, `data/product_docs.json` |
| React shell and chat UI | Partially implemented | `frontend/src/App.jsx`; `frontend/src/components/ChatInterface.jsx` |
| Council visualization | Mocked presentation over real response data | `AgentDebateViewer.runSimulation` waits 800 ms between already-received agent outputs; there is no stream |
| Gateway routes | Partially implemented | `api/main.py`, `api/routes/chat.py`, `api/routes/health.py` |
| SAGE service | Broken | `agents/sage/main.py` fails Python parsing at its JSON prompt literal |
| GUARDIAN service | Broken and logically unsafe | `agents/guardian/main.py` fails parsing; when corrected, parsed model JSON can override regex flags |
| EMPATH service | Partially implemented | `agents/empath/main.py`, `EmotionAnalyzer.analyze`; deterministic emotion categories do not use the model's label to choose emotion |
| ORACLE service | Partially implemented | `agents/oracle/main.py`, `FactChecker`; receives model-provided `sources`, not the retrieved Chroma documents |
| Consensus | Hard-coded/mischaracterized | `api/services/orchestrator.py`, `consensus/pbft_consensus.py`; simple threshold over three duplicated SAGE answers plus ORACLE |
| Redis message bus | Disconnected/dead code | `consensus/message_bus.py` is never imported or instantiated by the runtime |
| Chroma RAG | Partially implemented, runtime unverified | `agents/sage/rag_engine.py`, `api/seed_docs.py`, `docker-compose.yml` |
| Blockchain write path | Partially implemented | `api/services/blockchain_logger.py`, `blockchain/contracts/ConsensusLedger.sol`; only approved decisions are attempted |
| Smart-contract authorization | Broken for trustworthy audit | `ConsensusLedger.logConsensus` is public and has no caller restriction |
| Authentication/RBAC | Not implemented | No auth dependency, middleware, user model, password, token, or protected route exists |
| Human escalation | Planned only | API returns `escalate: true`; there is no queue, webhook, ticket, or notification integration |
| Docker Compose | Defined but application startup is blocked | `docker-compose.yml`; configuration parses, but SAGE/GUARDIAN syntax failures prevent the intended stack |
| Render deployment | Disconnected/incomplete | `render.yaml` defines only gateway and Redis |
| Vercel frontend | Configured, not verified deployed | `frontend/vercel.json`; no deployment URL is checked in |
| Automated tests | Partial | `tests/`; only consensus branches and several regex rules have isolated coverage |
| CI | Broken as checked in | `.github/workflows/ci.yml` starts no gateway for integration tests and lint encounters syntax errors |

## 4. Technology Stack

| Layer | Technology | Version/configuration evidence | Actual use |
|---|---|---|---|
| Languages | Python, JavaScript/JSX, CSS, Solidity, YAML/JSON | Source extensions throughout repository | Python services; React client; Solidity audit contract |
| Gateway/agents | FastAPI | `fastapi==0.111.0` in each Python service requirements file | HTTP APIs in `api/main.py` and each `agents/*/main.py` |
| ASGI server | Uvicorn | `uvicorn[standard]==0.30.0`; Docker `CMD` entries | One process per service, port 5000 internally or 8000 for gateway |
| Validation | Pydantic 2 | `pydantic==2.7.0` | Request body models only; AI outputs are not schema-validated |
| External LLM | Groq Python SDK | `groq==0.9.0` in SAGE/GUARDIAN/ORACLE requirements | Hard-coded model `llama3-70b-8192`, temperature `0.1` |
| Vector store | ChromaDB server + thin client | `chromadb/chroma:latest` in `docker-compose.yml`; `chromadb-client==0.4.25` in `agents/sage/requirements.txt` | One `product_docs` collection |
| Embeddings | Sentence Transformers | `sentence-transformers==2.7.0`; model `all-MiniLM-L6-v2` | ORACLE comparisons and gateway vote tally |
| Sentiment | Hugging Face Transformers + PyTorch | `transformers==4.41.0`, `torch==2.3.0`; DistilBERT model in `agents/empath/emotion_model.py` | Sentiment label/score, plus keyword-based emotion logic |
| HTTP clients | Requests | `requests==2.31.0` in gateway/SAGE requirements | Gateway-to-agent calls, health checks, Chroma seed calls |
| Message bus/cache | Redis 7 | `redis:7-alpine`, `redis==5.0.0` | Container and unused `RedisMessageBus`; not in active request flow and not used as a cache |
| Blockchain client | Web3.py | `web3==6.15.0` | Signs and sends `logConsensus` transactions |
| Smart contracts | Solidity + Hardhat toolbox | Solidity `^0.8.19`; Hardhat `^2.20.0`; toolbox `^4.0.0` | One `ConsensusLedger` contract and deployment scripts |
| Frontend | React 18 + Vite 5 | `frontend/package.json` | Local component state, no router or external state manager |
| Containers | Docker Compose | `docker-compose.yml`, five Dockerfiles | Redis, Chroma, four agents, gateway |
| Hosting config | Render and Vercel | `render.yaml`, `frontend/vercel.json` | Configuration only; no verified deployment |
| CI | GitHub Actions | `.github/workflows/ci.yml` | Pytest and Flake8 jobs, currently structurally broken |
| Tests | Pytest | Tests import `pytest`; CI installs it | Unit-style consensus/scanner tests and environment-dependent HTTP smoke tests |
| Package managers | pip and npm | Five `requirements.txt` files; two `package.json` files | No Python or npm lock files are checked in |

There is no relational/document application database, ORM, migration framework, message-queue worker, scheduler, server-side session store, authentication provider, agent framework, or frontend state-management library.


## 5. Repository Structure (Auto-Updated)

# Codebase Context (Auto-Generated)

## Repository Structure
- **./**
    - `.dockerignore`
    - `.env.example`
    - `.gitignore`
    - `AGENTMESH_BUILD_SPEC.md`
    - `ARCHITECTURE.md`
    - `CODEBASE_CONTEXT.md`
    - `DEMO_SCRIPT.md`
    - `DEPLOY.md`
    - `HACKATHON_SUBMISSION.md`
    - `IMPLEMENTATION_REPORT.md`
    - `README.md`
    - `alembic.ini`
    - `docker-compose.yml`
    - `generate_context.py`
    - `pytest.ini`
    - `render.yaml`
    - `requirements-dev.txt`
    - **agents/**
        - `__init__.py`
        - **empath/**
            - `Dockerfile`
            - `__init__.py`
            - `emotion_model.py`
            - `main.py`
            - `requirements.txt`
            - `service.py`
        - **guardian/**
            - `Dockerfile`
            - `__init__.py`
            - `main.py`
            - `requirements.txt`
            - `security_scanner.py`
            - `service.py`
        - **oracle/**
            - `Dockerfile`
            - `__init__.py`
            - `fact_checker.py`
            - `main.py`
            - `requirements.txt`
            - `service.py`
        - **sage/**
            - `Dockerfile`
            - `__init__.py`
            - `main.py`
            - `rag_engine.py`
            - `requirements.txt`
            - `service.py`
    - **api/**
        - `Dockerfile`
        - `__init__.py`
        - `auth.py`
        - `bootstrap_platform_admin.py`
        - `config.py`
        - `errors.py`
        - `export_openapi.py`
        - `main.py`
        - `requirements.txt`
        - `saas_schemas.py`
        - `schemas.py`
        - `seed_docs.py`
        - `tenancy.py`
        - `worker.py`
        - **db/**
            - `__init__.py`
            - `base.py`
            - `models.py`
        - **middleware/**
            - `__init__.py`
            - `rate_limit.py`
        - **routes/**
            - `__init__.py`
            - `api_keys.py`
            - `billing.py`
            - `chat.py`
            - `decisions.py`
            - `documents.py`
            - `escalations.py`
            - `health.py`
            - `platform.py`
            - `reviews.py`
            - `tenants.py`
            - `usage.py`
            - `webhooks.py`
        - **services/**
            - `__init__.py`
            - `api_keys.py`
            - `audit.py`
            - `billing.py`
            - `blockchain_logger.py`
            - `decisions.py`
            - `dlp.py`
            - `email.py`
            - `knowledge.py`
            - `malware.py`
            - `object_storage.py`
            - `orchestrator.py`
            - `rate_limiter.py`
            - `retention.py`
            - `reviews.py`
            - `storage.py`
            - `tenant_persistence.py`
            - `tenants.py`
            - `tone_adapter.py`
            - `usage.py`
            - `webhooks.py`
    - **blockchain/**
        - `hardhat.config.js`
        - `package-lock.json`
        - `package.json`
        - **artifacts/**
            - **build-info/**
                - `2afaafece90cf43ed5d141d4435dbaa7.json`
            - **contracts/**
                - **DecisionLedger.sol/**
                    - `DecisionLedger.dbg.json`
                    - `DecisionLedger.json`
        - **cache/**
            - `solidity-files-cache.json`
        - **contracts/**
            - `DecisionLedger.sol`
        - **scripts/**
            - `deploy.js`
            - `start-local.js`
        - **test/**
            - `DecisionLedger.js`
    - **consensus/**
        - `__init__.py`
        - `risk_engine.py`
    - **data/**
        - `product_docs.json`
    - **docs/**
        - `openapi.json`
        - **screenshots/**
    - **evaluation/**
        - `cases.json`
        - `report.json`
        - `run_evaluation.py`
    - **frontend/**
        - `index.html`
        - `package-lock.json`
        - `package.json`
        - `playwright.config.ts`
        - `tsconfig.json`
        - `vercel.json`
        - `vite.config.js`
        - `vitest.config.ts`
        - **dist/**
            - `index.html`
            - **assets/**
                - `index-CGtNpAmE.js`
                - `index-RNZxc2m0.css`
                - `vendor-forms-CrutX5vr.js`
                - `vendor-icons-BBriRvd5.js`
                - `vendor-query-D4VyGfOF.js`
                - `vendor-react-FnR1TxsD.js`
                - `vendor-router-BK_XU_Zh.js`
                - `vendor-supabase-Bmi-Q25R.js`
            - **fonts/**
                - `fraunces-latin.woff2`
                - `inter-latin.woff2`
                - `jetbrains-mono-latin.woff2`
        - **e2e/**
            - `saas-journey.spec.ts`
            - **fixtures/**
                - `returns.md`
        - **public/**
            - **fonts/**
                - `fraunces-latin.woff2`
                - `inter-latin.woff2`
                - `jetbrains-mono-latin.woff2`
        - **src/**
            - `App.tsx`
            - `api.js`
            - `decision.js`
            - `index.css`
            - `main.tsx`
            - **auth/**
                - `AuthPages.test.tsx`
                - `AuthPages.tsx`
                - `AuthProvider.tsx`
            - **components/**
                - `AgentDebateViewer.jsx`
                - `AppShell.jsx`
                - `BlockchainProof.jsx`
                - `ChatInterface.jsx`
                - `HumanReviewQueue.jsx`
                - `SaaSShell.test.tsx`
                - `SaaSShell.tsx`
                - `SystemStatus.jsx`
                - `ui.jsx`
            - **generated/**
                - `api.ts`
            - **lib/**
                - `saas-api.ts`
                - `supabase.ts`
            - **pages/**
                - `AcceptInvitePage.tsx`
                - `OnboardingPage.test.tsx`
                - `OnboardingPage.tsx`
                - `SaaSPages.test.tsx`
                - `SaaSPages.tsx`
            - **test/**
                - `setup.ts`
        - **test-results/**
    - **shared/**
        - `__init__.py`
        - `schemas.py`
    - **state/**
        - `agentmesh-saas.db`
        - **documents/**
            - **organizations/**
                - **1ee98483-e9e5-41ca-8707-eebfd4a7445c/**
                    - **workspaces/**
                        - **2ca6b969-c383-49a7-9b09-a205d65eab86/**
                            - **documents/**
                                - **25e4f069-8295-4079-8a0b-5d110a3387f7/**
                                    - **v1/**
                                        - `4a7159d59f8544d931d94bad501c5fcd1985151a5d214ede93e0806186f881fb.md`
    - **tests/**
        - `conftest.py`
        - `test_api_integration.py`
        - `test_citation_provenance.py`
        - `test_claim_verification.py`
        - `test_evaluation_dataset.py`
        - `test_evaluation_runner.py`
        - `test_full_stack_optional.py`
        - `test_guardian.py`
        - `test_local_workflows.py`
        - `test_postgres_rls.py`
        - `test_risk_engine.py`
        - `test_saas_tenancy.py`
        - `test_security_rules.py`
        - `test_storage.py`
        - `test_tone_adapter.py`
        - `test_typed_outputs.py`

## File Details

### .\.dockerignore

### .\.env.example

### .\.gitignore

### .\AGENTMESH_BUILD_SPEC.md
- *Markdown documentation file.*

### .\ARCHITECTURE.md
- *Markdown documentation file.*

### .\CODEBASE_CONTEXT.md
- *Markdown documentation file.*

### .\DEMO_SCRIPT.md
- *Markdown documentation file.*

### .\DEPLOY.md
- *Markdown documentation file.*

### .\HACKATHON_SUBMISSION.md
- *Markdown documentation file.*

### .\IMPLEMENTATION_REPORT.md
- *Markdown documentation file.*

### .\README.md
- *Markdown documentation file.*

### .\alembic.ini

### .\docker-compose.yml

### .\generate_context.py
- **Functions**: analyze_python_file, analyze_js_ts_file, generate_context

### .\pytest.ini

### .\render.yaml

### .\requirements-dev.txt

### .\agents\__init__.py

### .\agents\empath\Dockerfile

### .\agents\empath\__init__.py

### .\agents\empath\emotion_model.py
- **Classes**: EmotionAnalyzer

### .\agents\empath\main.py
- **Functions**: analyze, health, readiness

### .\agents\empath\requirements.txt

### .\agents\empath\service.py
- **Classes**: EmpathService

### .\agents\guardian\Dockerfile

### .\agents\guardian\__init__.py

### .\agents\guardian\main.py
- **Functions**: analyze, health, readiness

### .\agents\guardian\requirements.txt

### .\agents\guardian\security_scanner.py
- **Functions**: normalize_security_text, _scan, _contains_credential_request, _contains_unsafe_transfer_request, scan_query, scan_answer, severity_for

### .\agents\guardian\service.py
- **Classes**: _SemanticFinding, GuardianService

### .\agents\oracle\Dockerfile

### .\agents\oracle\__init__.py

### .\agents\oracle\fact_checker.py
- **Classes**: FactChecker
- **Functions**: _tokens, _normalized, _material_markers, _sentences

### .\agents\oracle\main.py
- **Functions**: analyze, health, readiness

### .\agents\oracle\requirements.txt

### .\agents\oracle\service.py
- **Classes**: OracleService

### .\agents\sage\Dockerfile

### .\agents\sage\__init__.py

### .\agents\sage\main.py
- **Functions**: analyze, health, readiness

### .\agents\sage\rag_engine.py
- **Classes**: RAGEngine
- **Functions**: _tokens, _has_domain_signal

### .\agents\sage\requirements.txt

### .\agents\sage\service.py
- **Classes**: _ModelDraft, SageService

### .\api\Dockerfile

### .\api\__init__.py

### .\api\auth.py
- **Classes**: Principal, SupabaseTokenVerifier
- **Functions**: _verifier, _bearer_value, get_principal, _rate_limit_principal, sync_user_profile, require_verified_principal, require_platform_admin

### .\api\bootstrap_platform_admin.py
- **Functions**: main

### .\api\config.py
- **Classes**: Settings
- **Functions**: _boolean, _integer, get_settings, reset_settings_cache

### .\api\errors.py
- **Classes**: APIError
- **Functions**: request_id, error_payload, api_error_handler, validation_error_handler

### .\api\export_openapi.py
- **Functions**: main

### .\api\main.py
- **Functions**: _cors_origins, create_app

### .\api\requirements.txt

### .\api\saas_schemas.py
- **Classes**: SaaSModel, OrganizationCreate, OrganizationView, WorkspaceCreate, WorkspaceView, OnboardingResult, MemberView, MemberUpdate, OwnershipTransfer, InvitationCreate, InvitationView, ProfileDraft, ProfileView, DocumentView, KnowledgeReleaseView, DocumentPreviewChunk, DocumentPreview, APIKeyCreate, APIKeyView, APIKeyCreated, PublicDecisionRequest, DecisionTrace, PublicDecisionResponse, DecisionListItem, UsageSummary, SpendCapUpdate, CheckoutResult, BillingPortalResult, ReviewClaim, TenantEscalationView, WebhookCreate, WebhookView, WebhookCreated, WebhookDeliveryView, PlatformOrganizationView

### .\api\schemas.py
- **Classes**: APIModel, ChatRequest, ChatResponse, EscalationRecord, EscalationUpdate, EscalationAction

### .\api\seed_docs.py
- **Functions**: seed

### .\api\tenancy.py
- **Classes**: TenantContext
- **Functions**: get_db_session, set_tenant_database_context, set_platform_database_context, organization_context, workspace_context, principal_dependency

### .\api\worker.py
- **Functions**: process_document, enqueue_document, report_usage_to_stripe, reconcile_usage_with_stripe_outbox, deliver_webhooks, deliver_email, enforce_retention, delete_stored_documents

### .\api\db\__init__.py

### .\api\db\base.py
- **Classes**: Base, Database

### .\api\db\models.py
- **Classes**: TimestampMixin, UserProfile, Organization, Membership, Invitation, PlatformRole, Workspace, IndustryTemplate, WorkspaceProfileVersion, Document, DocumentVersion, DocumentChunk, KnowledgeRelease, APIKey, SaaSDecision, DecisionSession, DecisionCitation, AgentFindingRecord, TenantEscalation, ReviewAction, UsageEvent, UsageReservation, BillingAccount, BillingOutbox, StripeEvent, IdempotencyRecord, WebhookEndpoint, WebhookDelivery, EmailOutbox, AuditEvent, BackgroundJob, AbuseSignal
- **Functions**: new_id, utc_now

### .\api\middleware\__init__.py

### .\api\middleware\rate_limit.py
- **Classes**: InMemoryRateLimitMiddleware

### .\api\routes\__init__.py

### .\api\routes\api_keys.py
- **Functions**: api_keys, create_api_key, revoke_api_key

### .\api\routes\billing.py
- **Functions**: checkout, portal, stripe_webhook

### .\api\routes\chat.py
- **Functions**: chat

### .\api\routes\decisions.py
- **Functions**: create_decision, get_public_decision, list_dashboard_decisions, get_dashboard_decision

### .\api\routes\documents.py
- **Functions**: documents, upload_document, upload_document_version, preview_document, archive_document, knowledge_releases, publish_knowledge_release, activate_knowledge_release

### .\api\routes\escalations.py
- **Functions**: require_review_key, _not_found, list_escalations, get_escalation, update_escalation, approve_escalation, reject_escalation, resolve_escalation, _apply_action

### .\api\routes\health.py
- **Functions**: legacy_health, liveness, readiness

### .\api\routes\platform.py
- **Functions**: _authorize, organizations, platform_metrics, jobs, templates, rule_packs, abuse_signals, billing_reconciliation, service_health

### .\api\routes\reviews.py
- **Functions**: review_queue, review_detail, claim_review, _transition_route

### .\api\routes\tenants.py
- **Functions**: organizations, create_organization, accept_invitation, workspaces, create_workspace, members, update_member, transfer_ownership, delete_organization, invite_member, profiles, create_profile, publish_profile

### .\api\routes\usage.py
- **Functions**: organization_usage, set_spend_cap

### .\api\routes\webhooks.py
- **Functions**: list_webhooks, create_webhook, disable_webhook, webhook_deliveries

### .\api\services\__init__.py

### .\api\services\api_keys.py
- **Classes**: APIKeyPrincipal
- **Functions**: _digest, create_key, list_keys, revoke_key, authenticate_key

### .\api\services\audit.py
- **Functions**: record_audit

### .\api\services\billing.py
- **Functions**: _configure, create_checkout, create_portal, process_stripe_webhook, report_meter_events, reconcile_meter_outbox

### .\api\services\blockchain_logger.py
- **Classes**: BlockchainLogger
- **Functions**: _enabled

### .\api\services\decisions.py
- **Classes**: RetrievedEvidenceEngine
- **Functions**: _request_digest, _profile, _stored_response, create_decision, decision_response

### .\api\services\dlp.py
- **Functions**: _luhn_valid, reject_sensitive_input

### .\api\services\email.py
- **Functions**: queue_email, queue_review_notifications, deliver_pending

### .\api\services\knowledge.py
- **Classes**: ExtractedPage
- **Functions**: _validate_file, create_document, create_document_version, _extract, _chunk_pages, embedding, process_document_version, _document_view, list_documents, preview_document, publish_release, list_releases, archive_document, activate_release, retrieve_sources

### .\api\services\malware.py
- **Functions**: scan_document

### .\api\services\object_storage.py
- **Classes**: ObjectStorage, LocalObjectStorage, S3ObjectStorage
- **Functions**: create_object_storage

### .\api\services\orchestrator.py
- **Classes**: _InvalidAgentOutputError, AgentOrchestrator
- **Functions**: _validated_output

### .\api\services\rate_limiter.py
- **Classes**: DistributedRateLimiter

### .\api\services\retention.py
- **Functions**: redact_expired_content

### .\api\services\reviews.py
- **Functions**: list_escalations, get_escalation, _check_version, _record_transition, claim_escalation, transition_escalation

### .\api\services\storage.py
- **Classes**: SQLiteRepository
- **Functions**: _utc_now

### .\api\services\tenant_persistence.py
- **Classes**: CreatedTenantTicket, TenantDecisionPersistence

### .\api\services\tenants.py
- **Functions**: slugify, seed_industry_templates, _organization_view, _workspace_view, create_organization, list_organizations, _create_workspace_record, create_workspace, list_workspaces, create_invitation, accept_invitation, list_members, update_member, transfer_ownership, delete_organization, create_profile_draft, publish_profile, list_profiles

### .\api\services\tone_adapter.py
- **Classes**: ToneAdapter

### .\api\services\usage.py
- **Functions**: period_key, _lock_organization, usage_count, reserve_usage, finalize_usage, release_usage, summary, update_spend_cap

### .\api\services\webhooks.py
- **Functions**: _encryption_key, _encrypt, _decrypt, create_endpoint, list_endpoints, disable_endpoint, list_deliveries, queue_event, deliver_pending

### .\blockchain\hardhat.config.js
- **Snippets/Imports**:
  - `require("@nomicfoundation/hardhat-toolbox");`
  - `module.exports = {`
  - `solidity: "0.8.19",`
  - `networks: {`
  - `amoy: {`

### .\blockchain\package-lock.json

### .\blockchain\package.json

### .\blockchain\artifacts\build-info\2afaafece90cf43ed5d141d4435dbaa7.json

### .\blockchain\artifacts\contracts\DecisionLedger.sol\DecisionLedger.dbg.json

### .\blockchain\artifacts\contracts\DecisionLedger.sol\DecisionLedger.json

### .\blockchain\cache\solidity-files-cache.json

### .\blockchain\contracts\DecisionLedger.sol

### .\blockchain\scripts\deploy.js
- **Snippets/Imports**:
  - `const hre = require("hardhat");`
  - `async function main() {`
  - `const DecisionLedger = await hre.ethers.getContractFactory("DecisionLedger");`
  - `const ledger = await DecisionLedger.deploy();`
  - `await ledger.waitForDeployment();`

### .\blockchain\scripts\start-local.js
- **Snippets/Imports**:
  - `const hre = require("hardhat");`
  - `async function main() {`
  - `const [deployer] = await hre.ethers.getSigners();`
  - `console.log("Deploying with account:", deployer.address);`
  - `const DecisionLedger = await hre.ethers.getContractFactory("DecisionLedger");`

### .\blockchain\test\DecisionLedger.js
- **Snippets/Imports**:
  - `const { expect } = require("chai");`
  - `const { ethers } = require("hardhat");`
  - `describe("DecisionLedger", function () {`
  - `async function deployLedger() {`
  - `const [owner, other] = await ethers.getSigners();`

### .\consensus\__init__.py

### .\consensus\risk_engine.py
- **Classes**: RiskAwareDecisionEngine

### .\data\product_docs.json

### .\docs\openapi.json

### .\evaluation\cases.json

### .\evaluation\report.json

### .\evaluation\run_evaluation.py
- **Functions**: _ratio, _report_path, _validate_dataset, _evaluate_case, _failure_policy_checks, run, _parse_args, main

### .\frontend\index.html

### .\frontend\package-lock.json

### .\frontend\package.json

### .\frontend\playwright.config.ts
- **Snippets/Imports**:
  - `import { defineConfig, devices } from '@playwright/test'`
  - `export default defineConfig({`
  - `testDir: './e2e',`
  - `fullyParallel: false,`
  - `retries: process.env.CI ? 2 : 0,`

### .\frontend\tsconfig.json

### .\frontend\vercel.json

### .\frontend\vite.config.js
- **Snippets/Imports**:
  - `import { defineConfig } from 'vite'`
  - `import react from '@vitejs/plugin-react'`
  - `export default defineConfig({`
  - `plugins: [react()],`
  - `build: {`

### .\frontend\vitest.config.ts
- **Snippets/Imports**:
  - `import { defineConfig } from 'vitest/config'`
  - `import react from '@vitejs/plugin-react'`
  - `export default defineConfig({`
  - `plugins: [react()],`
  - `test: {`

### .\frontend\dist\index.html

### .\frontend\dist\assets\index-CGtNpAmE.js
- **Snippets/Imports**:
  - `var ye=Object.defineProperty;var we=(s,n,r)=>n in s?ye(s,n,{enumerable:!0,configurable:!0,writable:!`
  - `-H "Authorization: Bearer $AGENTMESH_API_KEY" \\`
  - `-H "Idempotency-Key: request-001" \\`
  - `-H "Content-Type: application/json" \\`
  - `-d '{"input":"What is our return policy?"}'`})})]})]})}function ws(){var o,d;const s=$(),[n,r]=g.use`

### .\frontend\dist\assets\index-RNZxc2m0.css

### .\frontend\dist\assets\vendor-forms-CrutX5vr.js
- **Snippets/Imports**:
  - `import{R as Q}from"./vendor-query-D4VyGfOF.js";var Ue=e=>e.type==="checkbox",me=e=>e instanceof Date`
  - ``).filter(s=>s),o=Math.min(...n.map(s=>s.length-s.trimStart().length)),i=n.map(s=>s.slice(o)).map(s=`
  - ``))}}const Ho={major:4,minor:4,patch:3},q=d("$ZodType",(e,t)=>{var o;var r;e??(e={}),e._zod.def=t,e.`
  - `if (${R}.issues.length) {`
  - `if (${J} in input) {`

### .\frontend\dist\assets\vendor-icons-BBriRvd5.js
- **Snippets/Imports**:
  - `import{r as s}from"./vendor-query-D4VyGfOF.js";/**`
  - `* @license lucide-react v1.24.0 - ISC`
  - `*`
  - `* This source code is licensed under the ISC license.`
  - `* See the LICENSE file in the root directory of this source tree.`

### .\frontend\dist\assets\vendor-query-D4VyGfOF.js
- **Snippets/Imports**:
  - `var je=e=>{throw TypeError(e)};var ue=(e,t,s)=>t.has(e)||je("Cannot "+s);var i=(e,t,s)=>(ue(e,t,"rea`
  - `* @license React`
  - `* react.production.min.js`
  - `*`
  - `* Copyright (c) Facebook, Inc. and its affiliates.`

### .\frontend\dist\assets\vendor-react-FnR1TxsD.js
- **Snippets/Imports**:
  - `import"./vendor-router-BK_XU_Zh.js";import"./vendor-query-D4VyGfOF.js";`

### .\frontend\dist\assets\vendor-router-BK_XU_Zh.js
- **Snippets/Imports**:
  - `import{r as v}from"./vendor-query-D4VyGfOF.js";var va={exports:{}},ge={},ya={exports:{}},ga={};/**`
  - `* @license React`
  - `* scheduler.production.min.js`
  - `*`
  - `* Copyright (c) Facebook, Inc. and its affiliates.`

### .\frontend\dist\assets\vendor-supabase-Bmi-Q25R.js
- **Snippets/Imports**:
  - `function Fe(t,e){var r={};for(var s in t)Object.prototype.hasOwnProperty.call(t,s)&&e.indexOf(s)<0&&`
  - `Caused by: ${(g=u==null?void 0:u.name)!==null&&g!==void 0?g:"Error"}: ${v}`,_&&(l+=` (${_})`),u!=nul`
  - `${u.stack}`)}else{var m;l=(m=a==null?void 0:a.stack)!==null&&m!==void 0?m:""}const b=this.url.toStri`
  - `Suggested solution: ${e.workaround}`),new Error(r)}static isWebSocketSupported(){try{return this.det`
  - ``),()=>this.onerror("timeout"),n=>{!n||n.status!==200?(this.awaitingBatchAck=!1,this.onerror(n&&n.st`

### .\frontend\dist\fonts\fraunces-latin.woff2

### .\frontend\dist\fonts\inter-latin.woff2

### .\frontend\dist\fonts\jetbrains-mono-latin.woff2

### .\frontend\e2e\saas-journey.spec.ts
- **Snippets/Imports**:
  - `import path from 'node:path'`
  - `import { expect, test } from '@playwright/test'`
  - `test('onboarding to published knowledge, decision trace, and usage', async ({ page }) => {`
  - `await page.goto('/')`
  - `await expect(page.getByRole('heading', { name: 'Configure your first AgentMesh workspace.' })).toBeV`

### .\frontend\e2e\fixtures\returns.md
- *Markdown documentation file.*

### .\frontend\public\fonts\fraunces-latin.woff2

### .\frontend\public\fonts\inter-latin.woff2

### .\frontend\public\fonts\jetbrains-mono-latin.woff2

### .\frontend\src\App.tsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import { useQuery } from '@tanstack/react-query'`
  - `import { Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'`
  - `import { AuthPage, ForgotPasswordPage, VerifyPage } from './auth/AuthPages'`
  - `import { useAuth } from './auth/AuthProvider'`

### .\frontend\src\api.js
- **Snippets/Imports**:
  - `const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim()`
  - `export const API_BASE_URL = (configuredBaseUrl || '/api/v1').replace(/\/$/, '')`
  - `const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS)`
  - `export const DEFAULT_TIMEOUT_MS = Number.isFinite(configuredTimeout) && configuredTimeout > 0`
  - `? configuredTimeout`

### .\frontend\src\decision.js
- **Snippets/Imports**:
  - `export const AGENT_DEFINITIONS = [`
  - `{ key: 'sage', name: 'SAGE', role: 'Policy grounding' },`
  - `{ key: 'guardian', name: 'GUARDIAN', role: 'Security review' },`
  - `{ key: 'empath', name: 'EMPATH', role: 'Customer context' },`
  - `{ key: 'oracle', name: 'ORACLE', role: 'Evidence verification' },`

### .\frontend\src\index.css

### .\frontend\src\main.tsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import ReactDOM from 'react-dom/client'`
  - `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'`
  - `import { BrowserRouter } from 'react-router-dom'`
  - `import App from './App'`

### .\frontend\src\auth\AuthPages.test.tsx
- **Snippets/Imports**:
  - `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'`
  - `import { render, screen } from '@testing-library/react'`
  - `import userEvent from '@testing-library/user-event'`
  - `import { MemoryRouter, Route, Routes } from 'react-router-dom'`
  - `import { describe, expect, it } from 'vitest'`

### .\frontend\src\auth\AuthPages.tsx
- **Snippets/Imports**:
  - `import React, { useState } from 'react'`
  - `import { zodResolver } from '@hookform/resolvers/zod'`
  - `import { useForm } from 'react-hook-form'`
  - `import { Link, Navigate, useNavigate } from 'react-router-dom'`
  - `import { z } from 'zod'`

### .\frontend\src\auth\AuthProvider.tsx
- **Snippets/Imports**:
  - `import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'`
  - `import type { Session, User } from '@supabase/supabase-js'`
  - `import { authConfigured, supabase } from '../lib/supabase'`
  - `import { setDevelopmentIdentity, setTokenProvider } from '../lib/saas-api'`
  - `interface AuthContextValue {`

### .\frontend\src\components\AgentDebateViewer.jsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import { BookOpenText, FileCheck2, HeartPulse, ShieldCheck } from 'lucide-react'`
  - `import BlockchainProof from './BlockchainProof'`
  - `import {`
  - `AGENT_DEFINITIONS,`

### .\frontend\src\components\AppShell.jsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import {`
  - `Activity,`
  - `ChevronDown,`
  - `GitBranch,`

### .\frontend\src\components\BlockchainProof.jsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import { ExternalLink } from 'lucide-react'`
  - `import { humanize } from '../decision'`
  - `import { SectionHeader, StatusIndicator } from './ui'`
  - `export default function BlockchainProof({ audit }) {`

### .\frontend\src\components\ChatInterface.jsx
- **Snippets/Imports**:
  - `import React, { useCallback, useEffect, useRef, useState } from 'react'`
  - `import { ArrowRight, ArrowUpRight, BookMarked, SendHorizontal, ShieldCheck, Square } from 'lucide-re`
  - `import { apiRequest, describeApiError } from '../api'`
  - `import { formatConfidence, humanize, normalizeDecision } from '../decision'`
  - `import { MeshMark } from './AppShell'`

### .\frontend\src\components\HumanReviewQueue.jsx
- **Snippets/Imports**:
  - `import React, { useEffect, useMemo, useRef, useState } from 'react'`
  - `import {`
  - `Check,`
  - `ChevronRight,`
  - `RefreshCw,`

### .\frontend\src\components\SaaSShell.test.tsx
- **Snippets/Imports**:
  - `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'`
  - `import { cleanup, render, screen } from '@testing-library/react'`
  - `import { MemoryRouter, Route, Routes } from 'react-router-dom'`
  - `import { afterEach, describe, expect, it, vi } from 'vitest'`
  - `import { AuthProvider } from '../auth/AuthProvider'`

### .\frontend\src\components\SaaSShell.tsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import { useQuery } from '@tanstack/react-query'`
  - `import {`
  - `Activity,`
  - `BookOpen,`

### .\frontend\src\components\SystemStatus.jsx
- **Snippets/Imports**:
  - `import React from 'react'`
  - `import { Database, FileSearch, Link2, RefreshCw, Server, ShieldCheck, Users } from 'lucide-react'`
  - `import { ErrorState, LoadingState, SectionHeader, StatusIndicator } from './ui'`
  - `const DEPENDENCY_ROWS = [`
  - `{ key: 'sage', label: 'Policy retrieval', description: 'Grounding and approved policy corpus', icon:`

### .\frontend\src\components\ui.jsx
- **Snippets/Imports**:
  - `import React, { useEffect, useRef, useState } from 'react'`
  - `import {`
  - `AlertTriangle,`
  - `Check,`
  - `CheckCircle2,`

### .\frontend\src\generated\api.ts
- **Snippets/Imports**:
  - `/**`
  - `* This file was auto-generated by openapi-typescript.`
  - `* Do not make direct changes to the file.`
  - `*/`
  - `export interface paths {`

### .\frontend\src\lib\saas-api.ts
- **Snippets/Imports**:
  - `const configuredBaseUrl = import.meta.env.VITE_API_URL?.trim()`
  - `export const API_BASE_URL = (configuredBaseUrl || '/api/v1').replace(/\/$/, '')`
  - `type TokenProvider = () => Promise<string | null>`
  - `let tokenProvider: TokenProvider = async () => null`
  - `let developmentIdentity = {`

### .\frontend\src\lib\supabase.ts
- **Snippets/Imports**:
  - `import { createClient, type SupabaseClient } from '@supabase/supabase-js'`
  - `const url = import.meta.env.VITE_SUPABASE_URL?.trim()`
  - `const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim()`
  - `export const authConfigured = Boolean(url && publishableKey)`
  - `export const supabase: SupabaseClient | null = authConfigured`

### .\frontend\src\pages\AcceptInvitePage.tsx
- **Snippets/Imports**:
  - `import { useMutation } from '@tanstack/react-query'`
  - `import { ArrowRight, Users } from 'lucide-react'`
  - `import { useNavigate, useSearchParams } from 'react-router-dom'`
  - `import { saasRequest, type Organization, type Workspace } from '../lib/saas-api'`
  - `export default function AcceptInvitePage() {`

### .\frontend\src\pages\OnboardingPage.test.tsx
- **Snippets/Imports**:
  - `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'`
  - `import { render, screen, waitFor } from '@testing-library/react'`
  - `import userEvent from '@testing-library/user-event'`
  - `import { MemoryRouter } from 'react-router-dom'`
  - `import { afterEach, describe, expect, it, vi } from 'vitest'`

### .\frontend\src\pages\OnboardingPage.tsx
- **Snippets/Imports**:
  - `import React, { useState } from 'react'`
  - `import { zodResolver } from '@hookform/resolvers/zod'`
  - `import { useForm } from 'react-hook-form'`
  - `import { useQueryClient } from '@tanstack/react-query'`
  - `import { ArrowRight, Check, Copy, KeyRound } from 'lucide-react'`

### .\frontend\src\pages\SaaSPages.test.tsx
- **Snippets/Imports**:
  - `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'`
  - `import { cleanup, render, screen } from '@testing-library/react'`
  - `import React from 'react'`
  - `import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'`
  - `import { afterEach, describe, expect, it, vi } from 'vitest'`

### .\frontend\src\pages\SaaSPages.tsx
- **Snippets/Imports**:
  - `import React, { useMemo, useState } from 'react'`
  - `import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'`
  - `import {`
  - `AlertTriangle,`
  - `ArrowRight,`

### .\frontend\src\test\setup.ts
- **Snippets/Imports**:
  - `import '@testing-library/jest-dom/vitest'`
  - `Object.defineProperty(window.navigator, 'clipboard', {`
  - `configurable: true,`
  - `value: { writeText: async () => undefined },`
  - `})`

### .\shared\__init__.py

### .\shared\schemas.py
- **Classes**: StrictModel, AgentState, DecisionState, GuardianStatus, GuardianAction, OracleRecommendation, EscalationPriority, EscalationStatus, AuditStatus, SourceRecord, SageOutput, GuardianOutput, EmpathOutput, ClaimVerification, OracleOutput, AgentFinding, DecisionResult, AuditOutcome, AgentRequest, SageResponse, GuardianRequest, GuardianResponse, EmpathResponse, OracleRequest, OracleResponse

### .\state\agentmesh-saas.db

### .\state\documents\organizations\1ee98483-e9e5-41ca-8707-eebfd4a7445c\workspaces\2ca6b969-c383-49a7-9b09-a205d65eab86\documents\25e4f069-8295-4079-8a0b-5d110a3387f7\v1\4a7159d59f8544d931d94bad501c5fcd1985151a5d214ede93e0806186f881fb.md
- *Markdown documentation file.*

### .\tests\conftest.py

### .\tests\test_api_integration.py
- **Classes**: FakeOrchestrator, DisabledBlockchain
- **Functions**: _client, test_chat_api_uses_in_process_mock_without_docker_or_network, test_chat_api_reuses_supplied_session_and_rejects_invalid_input, test_health_api_reflects_mocked_readiness, test_review_queue_crud_endpoints_use_temporary_sqlite, test_review_queue_reject_action_and_missing_ticket, test_actual_local_pipeline_creates_escalation_without_external_services

### .\tests\test_citation_provenance.py
- **Functions**: _policies, test_retrieval_returns_application_controlled_source_records, test_sage_citations_are_structured_retrieval_results, test_model_text_cannot_replace_structured_citation_provenance, test_unsupported_query_has_no_fabricated_citations, test_generic_temporal_overlap_does_not_create_irrelevant_policy_evidence, test_generic_account_words_do_not_select_premium_policy, test_missing_policy_file_is_reported_as_dependency_failure

### .\tests\test_claim_verification.py
- **Functions**: _source, test_exact_policy_claim_is_supported_with_source_id, test_material_claim_missing_from_evidence_is_not_approved, test_numeric_contradiction_is_rejected_even_with_similar_words, test_claims_are_verified_individually, test_claim_without_retrieved_evidence_requests_clarification, test_empty_draft_is_not_treated_as_verified, test_material_qualifier_or_polarity_changes_are_rejected, test_one_word_material_claim_is_not_dropped

### .\tests\test_evaluation_dataset.py
- **Functions**: _dataset, test_dataset_meets_required_category_minimums, test_dataset_ids_are_unique_and_labels_are_complete, test_all_expected_document_ids_exist_in_approved_policy_corpus, test_category_labels_are_consistent

### .\tests\test_evaluation_runner.py
- **Functions**: test_evaluation_runner_uses_all_cases_and_reports_real_denominators, test_evaluation_runner_has_no_component_errors, test_report_is_json_serializable

### .\tests\test_full_stack_optional.py
- **Functions**: _request, test_complete_started_stack_health_and_chat

### .\tests\test_guardian.py
- **Functions**: test_credential_request_detected, test_phishing_urgency_detected, test_pii_request_detected, test_safe_query, test_unauthorized_refund_promise

### .\tests\test_local_workflows.py
- **Classes**: DisabledBlockchain, CapturingBlockchain
- **Functions**: test_standalone_agent_apps_are_live_and_ready, local_client, test_grounded_refund_workflow_is_approved_with_controlled_citation, test_credential_risk_is_deterministically_blocked_and_persisted, test_urgent_hospital_workflow_adapts_tone_and_escalates, test_prompt_injection_is_blocked_without_exposing_a_prompt, test_blocked_request_does_not_expose_unapproved_sage_draft, test_session_id_is_reused_without_overwriting_sqlite_decisions, test_identical_session_retries_have_unique_optional_audit_records

### .\tests\test_postgres_rls.py
- **Functions**: test_postgres_rls_hides_and_rejects_cross_tenant_rows, test_postgres_usage_reservations_enforce_quota_under_concurrency

### .\tests\test_risk_engine.py
- **Functions**: _source, _sage, _guardian, _empath, _oracle, _states, _decide, test_approved_state_for_safe_grounded_neutral_answer, test_approved_with_rewrite_state_for_frustrated_customer, test_needs_clarification_state_for_unsupported_material_claim, test_oracle_with_no_verified_claims_cannot_approve, test_needs_clarification_state_for_insufficient_retrieval, test_blocked_state_has_precedence_over_oracle_failure, test_escalated_state_for_security_warning, test_escalated_state_for_urgent_high_risk_customer, test_system_unavailable_state_when_sage_is_unavailable, test_guardian_unavailable_fails_closed, test_oracle_unavailable_never_claims_verified_approval, test_empath_unavailable_degrades_to_neutral_without_blocking, test_precedence_is_independent_of_synthetic_agent_vote_counts

### .\tests\test_saas_tenancy.py
- **Functions**: _settings, _client, _headers, _onboard, _create_key, _upload_and_publish, test_onboarding_creates_isolated_organization_workspace_and_profile, test_workspace_document_release_and_tenant_decision_api, test_free_quota_is_atomic_and_requires_billing_for_overage, test_api_key_revoke_is_immediate_and_secret_is_never_listed, test_document_versions_preview_archive_and_release_rollback, test_invited_viewer_is_read_only_and_cannot_open_review_queue, test_role_permission_matrix_covers_every_customer_role, test_reviewer_claim_optimistic_lock_and_terminal_transition, test_owner_spend_cap_blocks_paid_overage_before_processing, test_dlp_rejection_is_not_billed, test_retention_redacts_raw_and_normalized_decision_content

### .\tests\test_security_rules.py
- **Functions**: test_deterministic_query_rules, test_deterministic_answer_rules, test_safe_policy_question_has_no_security_violation, test_benign_person_to_person_transfer_question_is_not_critical, test_unverified_support_transfer_instruction_remains_critical, test_severity_precedence_is_critical_over_warning, test_semantic_safe_result_cannot_override_deterministic_critical, test_semantic_failure_cannot_remove_deterministic_critical, test_semantic_finding_can_add_but_not_duplicate_violations

### .\tests\test_storage.py
- **Functions**: _create, test_sqlite_escalation_create_and_retrieve, test_sqlite_escalation_list_and_status_filter, test_sqlite_escalation_update_edit_and_resolve, test_missing_escalation_raises_key_error, test_repository_health_checks_a_real_sqlite_write, test_decision_audit_can_reference_escalation, test_optional_audit_outcome_updates_existing_local_decision

### .\tests\test_tone_adapter.py
- **Functions**: test_emotion_analysis_selects_response_strategy, test_tone_adaptation_preserves_verified_body_byte_for_byte, test_neutral_tone_does_not_modify_answer, test_missing_empath_output_uses_neutral_fallback, test_preserves_facts_rejects_rewritten_or_removed_body, test_adapter_only_uses_declared_presentation_prefix

### .\tests\test_typed_outputs.py
- **Functions**: source_record, test_source_record_accepts_complete_structured_provenance, test_source_record_rejects_invalid_or_extra_fields, test_sage_output_rejects_out_of_range_confidence, test_guardian_output_rejects_unknown_status_and_extra_fields, test_empath_output_rejects_invalid_urgency, test_oracle_claim_requires_claim_level_reason_and_source_ids, test_oracle_output_validates_nested_claims, test_agent_state_is_a_closed_enum, test_async_component_non_model_output_is_reported_as_invalid, test_sync_component_non_model_output_is_reported_as_invalid
