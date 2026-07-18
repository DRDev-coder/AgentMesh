# AgentMesh deployment runbook

The supported production topology is a static frontend, the FastAPI API with separate Celery worker/scheduler, Supabase for Auth/PostgreSQL/pgvector/private object storage/backups, managed Redis, and Razorpay Subscriptions. Development, staging, and production must use separate projects and secrets.

## Student Azure staging

The budget deployment uses Azure Static Web Apps Free, a public GHCR image, and Azure Container Apps Consumption with zero minimum replicas, one maximum replica, and no Log Analytics workspace. This keeps low-traffic Azure usage inside the platform free allowances and avoids the recurring Azure Container Registry charge.

The first demo revision may use `APP_ENV=development`, eager tasks, SQLite, and local object storage so the UI/API can be reviewed before paid infrastructure is approved. That revision is ephemeral: scale-down or redeployment can erase application data and documents. It is not a production topology.

Before changing the Azure revision to `APP_ENV=production`, add a restricted non-superuser PostgreSQL application role, durable private object storage, managed Redis with `noeviction`, separate worker/scheduler deployment, malware scanning, backups, complete Razorpay settings, exact HTTPS origins, and all cost-control values.

## 1. Pre-deployment gates

Do not launch unless CI passes compilation, Ruff, all backend tests, the PostgreSQL RLS test, deterministic evaluation, OpenAPI generation, TypeScript checks, component tests, the Vite build, the Playwright journey, and Compose validation.

The launch gate additionally requires staging proof of:

- cross-organization and cross-workspace `404` isolation;
- immediate API-key revocation;
- live-key access to published releases only;
- reviewer locking and edited-answer revalidation;
- the 500/501 quota boundary under concurrency;
- duplicate and out-of-order Razorpay webhooks;
- billing add-on outbox reconciliation;
- content redaction and document source deletion;
- provider failure producing non-billable `SYSTEM_UNAVAILABLE`;
- database backup restoration into a clean staging environment.

## 2. Supabase

Create separate projects for development, staging, and production.

1. Enable verified email/password and Google OAuth.
2. Configure the exact frontend callback URLs and password-recovery URL.
3. Enable CAPTCHA enforcement and use the matching Turnstile site key as `VITE_TURNSTILE_SITE_KEY`.
4. Enable MFA; platform administrators must enroll and present `aal2`.
5. Enable `pgvector` and confirm point-in-time backups for the selected plan.
6. Create a private object-storage bucket. Do not expose source objects publicly.
7. Use the PostgreSQL connection string as `DATABASE_URL` and the storage S3-compatible values as `S3_*`.

Run migrations with a role that owns the application schema:

```bash
alembic upgrade head
```

The runtime role needs CRUD privileges but should not be a PostgreSQL superuser, because superusers bypass RLS. The migration enables and forces tenant RLS policies. Keep connection pooling in transaction mode so transaction-local tenant settings cannot leak between requests.

## 3. Razorpay

Before setting `APP_ENV=production`:

1. Activate Razorpay Subscriptions for the account and create a recurring INR plan.
2. Store the resulting plan ID as `RAZORPAY_PLAN_ID` and choose the bounded billing-cycle count in `RAZORPAY_SUBSCRIPTION_TOTAL_COUNT`.
3. Generate test/live API credentials and supply `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
4. Register `POST https://<api-origin>/api/v1/webhooks/razorpay` for subscription lifecycle events.
5. Set a dedicated webhook secret as `RAZORPAY_WEBHOOK_SECRET`; it is distinct from the API key secret.
6. Supply `OVERAGE_UNIT_PRICE_PAISE`; completed overage decisions are added to the subscription as INR add-ons.

Use Razorpay test mode in staging. Confirm raw-body HMAC rejection, duplicate `X-Razorpay-Event-Id` handling, authenticated/active/pending/halted/cancelled states, add-on delivery, and daily reconciliation before live mode. Ambiguous add-on timeouts are held for review instead of automatically retried because the provider endpoint has no idempotency key.

## 4. Render API and workers

`render.yaml` declares:

- `agentmesh-api`, with `/readyz` health checks and `alembic upgrade head` as the pre-deploy command;
- `agentmesh-worker`, running Celery jobs;
- `agentmesh-scheduler`, running Celery Beat;
- persistent `agentmesh-redis` with `noeviction` for task durability.

Supply every `sync: false` value in the `agentmesh-production` environment group. Production startup intentionally fails when PostgreSQL, managed Redis, Supabase Auth, private S3 storage, exact HTTPS CORS, Razorpay, transactional email, external pricing, and provider-cost limits are incomplete.

Important server-only settings:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase PostgreSQL URL using the application role |
| `REDIS_URL` | Managed Redis internal URL |
| `SUPABASE_URL` | JWT issuer/JWKS origin |
| `API_KEY_PEPPER` | 32+ character key-digest pepper |
| `WEBHOOK_ENCRYPTION_KEY` | 32+ character envelope key for webhook secrets |
| `S3_*` | Private Supabase/object-storage S3 interface |
| `RAZORPAY_*` | Subscription authorization, add-ons, and webhook verification |
| `OVERAGE_UNIT_PRICE_PAISE` | Deployment-configured INR usage price |
| `PROVIDER_COST_CAP_CENTS` | Emergency monthly provider-cost ceiling |
| `ESTIMATED_COST_PER_DECISION_MILLICENTS` | Cost estimate used by the circuit breaker |
| `RESEND_API_KEY`, `RESEND_FROM` | Resend transactional email sender |
| `GROQ_API_KEY` | AgentMesh-owned model-provider credential |

Never place these settings in a `VITE_` variable.

After the first verified user signs in, grant the initial platform role from a protected shell:

```bash
python -m api.bootstrap_platform_admin \
  --user-id <supabase-user-id> \
  --granted-by <operator-identity>
```

The command requires a verified application identity and writes an immutable platform audit event.

## 5. Vercel frontend

Configure root directory `frontend`, build command `npm run build`, and output directory `dist`. Supply only public settings:

```dotenv
VITE_API_URL=https://api.example.com/api/v1
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<public-publishable-key>
VITE_TURNSTILE_SITE_KEY=<public-site-key>
```

Add the exact Vercel origin to backend `CORS_ORIGINS`. `frontend/vercel.json` rewrites client-side routes to `index.html`.

## 6. Smoke test

```bash
curl https://api.example.com/healthz
curl https://api.example.com/readyz
```

Then complete this staging journey in a clean browser:

1. Sign up through CAPTCHA, verify email, and complete onboarding.
2. Upload a non-sensitive Markdown policy and wait for `READY_FOR_REVIEW`.
3. Preview extracted chunks and publish a knowledge release.
4. Create a test key and call `POST /api/v1/decisions` with an idempotency key.
5. Confirm the decision, citations, exact release/profile IDs, and one usage unit.
6. Retry the same request and confirm the same decision ID and unchanged usage.
7. Cause an escalation, claim it, test a conflicting edit, and approve a safe cited answer.
8. Confirm signed customer webhook delivery and immutable review/audit history.
9. Authorize a Razorpay test subscription and compare AgentMesh overage usage with created add-ons.
10. Revoke the key and confirm the next call returns `401`.

## 7. Privacy, retention, and deletion

The API never intentionally logs prompts, answers, documents, secrets, payment data, or provider credentials. Raw decision and escalation content is redacted after each organization's retention window (30 days by default); audit and billing metadata remain. Archiving a document removes its chunks from retrieval immediately and queues source-object deletion.

Alerts should cover API error/latency rate, queue depth, failed jobs, failed webhook/email deliveries, provider-cost circuit activation, Razorpay outbox failures/review states, and reconciliation drift. Restore backups regularly into an isolated staging project and record recovery time and data-loss window.

## 8. Rollback

1. Stop new deployments and preserve the current database/object-storage state.
2. Roll the API, worker, scheduler, and frontend back to the same known-good revision.
3. Do not run Alembic downgrade against production unless a separately reviewed restore plan requires it.
4. If the new migration is incompatible, restore the pre-deploy database backup into a new database and point the known-good services to it.
5. Repeat readiness, isolation, key revocation, decision, review, billing, and deletion smoke tests.

The old shared `X-Review-API-Key` and SQLite `/api/v1/chat` path exist only for local compatibility tests and must not be exposed as the production customer or reviewer interface. Blockchain remains disabled and outside the production request path.
