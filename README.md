# AgentMesh

AgentMesh is a multi-tenant B2B SaaS for building evidence-grounded customer-support decision APIs. Each organization can create isolated workspaces, publish approved knowledge and configuration releases, issue test/live API keys, inspect four-agent decision traces, review escalations, and manage usage-based billing.

The existing SAGE → GUARDIAN → ORACLE → EMPATH council and deterministic fail-closed decision precedence remain the runtime core. Mandatory platform safety rules cannot be disabled by workspace configuration.

This MVP is for English-language informational support. It explicitly excludes PHI, patient records, payment-card data, bank credentials, arbitrary executable rules, regulated financial/medical decisions, OCR, SAML, customer BYOK, and embeddable chat widgets. It makes no HIPAA, PCI DSS, financial-regulatory, or medical-compliance claim.

## What is implemented

- Supabase email/password, Google OAuth, recovery, verified-email sessions, JWKS validation, and Turnstile-compatible signup CAPTCHA.
- Organizations, invitations, multiple workspaces, owner/admin/developer/reviewer/viewer RBAC, and MFA-gated platform administrators.
- PostgreSQL/Alembic persistence, tenant-scoped repositories, tenant-prefixed queries, and PostgreSQL row-level-security policies.
- PDF, DOCX, TXT, and Markdown ingestion up to 25 MB; signature validation, obvious malware rejection, hashing/deduplication, deterministic chunks, provenance, and hybrid lexical/vector retrieval.
- Immutable document/profile/knowledge releases, draft behavior for test keys, published-only behavior for live keys, preview, archive, and rollback.
- One-time-reveal `am_test_` and `am_live_` API keys stored only as keyed digests, with scopes, expiry, revocation, and distributed Redis rate limits.
- Idempotent `POST /api/v1/decisions`, exact citations, redacted traces, decision history, escalation lifecycle, optimistic review locking, and edited-answer revalidation.
- Organization-wide usage ledger, 500 completed decisions per UTC month, non-billable platform failures, Razorpay subscription add-on outbox, hosted subscription links/webhooks, INR spend caps, and provider-cost circuit breaker.
- Timestamped HMAC customer webhooks, retry history, Resend-backed transactional email outbox, document deletion jobs, and 30-day raw-content redaction jobs.
- Immutable hash-chained PostgreSQL audit events. The experimental blockchain module is disabled and is not authoritative.
- React/TypeScript SaaS dashboard using the existing Fraunces/Inter/JetBrains typography and cream/black/red visual system.

## Runtime architecture

```text
Vercel: React + Vite + TypeScript
             |
Azure Container Apps: FastAPI modular monolith ---- Redis (limits, cache, Celery)
             |                         |
             |                  Celery worker + scheduler
             |
Supabase: PostgreSQL + pgvector, Auth, private object storage, backups
             |
Razorpay: Subscriptions, usage add-ons, hosted authorization, signed webhooks
```

The student staging deployment uses Azure Static Web Apps Free plus Azure Container Apps Consumption scaled to zero. Its initial demo revision uses ephemeral SQLite/local storage and eager tasks to avoid paid Azure database, Redis, registry, and logging resources; see `infra/azure/README.md` for the production gap.

Interactive decisions remain synchronous inside the modular monolith. Celery handles document ingestion, email, outbound webhooks, retention, source deletion, and Razorpay add-on delivery.

## Local start

Docker Compose starts PostgreSQL with pgvector, Redis, MinIO, migrations, the API, a Celery worker, and Celery Beat:

```bash
cp .env.example .env
docker compose up --build
```

Set `RESEND_API_KEY` in the ignored `.env` file. For testing, `RESEND_FROM=AgentMesh <onboarding@resend.dev>` can send only to the email address associated with the Resend account; use an address on a verified domain for other recipients.

Then run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Local development auth uses `X-Dev-User`; production refuses to start unless Supabase, PostgreSQL, private object storage, Razorpay, Resend, HTTPS CORS, and cost controls are configured.

For a host-native backend, start PostgreSQL and Redis, copy `.env.example`, run `alembic upgrade head`, then:

```bash
python -m pip install -r requirements-dev.txt
python -m uvicorn api.main:app --env-file .env --port 8000
```

## Public decision API

```http
POST /api/v1/decisions
Authorization: Bearer am_live_<public-id>.<secret>
Idempotency-Key: unique-client-request-id
Content-Type: application/json
```

```json
{
  "input": "What is the return policy?",
  "session_id": "optional-session",
  "end_user_id": "optional-opaque-reference",
  "metadata": {}
}
```

The API key selects the organization, workspace, and test/live environment. Callers never submit tenant IDs. Reusing the same idempotency key with the same body returns the original response without another usage unit; reusing it with another body returns `409`.

The generated contract is [docs/openapi.json](docs/openapi.json), with generated TypeScript declarations in [frontend/src/generated/api.ts](frontend/src/generated/api.ts). `/api/v1/chat` remains only as a temporary local compatibility route.

## Roles

| Role | Primary permissions |
| --- | --- |
| `owner` | Billing, spend cap, ownership, deletion, and all customer actions |
| `admin` | Team, workspaces, documents, profiles, reviews, keys, webhooks |
| `developer` | Keys, webhooks, playground, traces, read-only config/knowledge |
| `reviewer` | Decision/evidence access and escalation actions |
| `viewer` | Read-only dashboards and decision records |

Platform roles are not grantable through a public endpoint. Bootstrap an existing verified identity with:

```bash
python -m api.bootstrap_platform_admin --user-id <supabase-user-id> --granted-by <operator-id>
```

Access to `/platform/*` additionally requires a Supabase `aal2` MFA session. The platform console exposes operational/commercial metadata, not tenant prompts or documents.

## Verification

```bash
python -m compileall agents api consensus shared evaluation
python -m ruff check agents api consensus shared evaluation tests
python -m pytest -q
python evaluation/run_evaluation.py --no-write
python -m api.export_openapi

cd frontend
npm run generate:api
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

CI also applies migrations to PostgreSQL, proves RLS with a restricted database role, verifies generated OpenAPI artifacts, runs the browser journey, tests the optional experimental contract, and validates Docker Compose.

See [DEPLOY.md](DEPLOY.md) for production environment setup, migrations, smoke tests, backup/restore gates, and rollback.
