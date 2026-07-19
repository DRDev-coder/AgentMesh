# Azure student staging

The low-cost staging topology uses:

- Azure Container Apps Consumption for the frontend and API, each with `minReplicas: 0` and `maxReplicas: 1`;
- public GitHub Container Registry for both images;
- the existing Supabase PostgreSQL database through its free IPv4 session pooler and a restricted `agentmesh_app` role;
- API-replica sidecars for Redis, one Celery worker, and Celery Beat;
- Azure Blob Storage shared by the API and ingestion worker;
- no Azure Container Registry and no Log Analytics workspace.

The deployed staging URLs are:

- frontend: `https://agentmesh-web.livelysmoke-efb633a4.centralindia.azurecontainerapps.io`;
- API: `https://agentmesh-api.livelysmoke-efb633a4.centralindia.azurecontainerapps.io`.

The current student deployment is intentionally a staging topology. Tenant records are durable in Supabase PostgreSQL and uploaded source files must use Azure Blob Storage (`OBJECT_STORAGE_BACKEND=azure_blob`) so both API and worker can read them. The legacy SQLite compatibility database, Redis state, and queued Celery messages remain replica-local and can disappear after scale-down or revision replacement. Celery Beat also runs only while the HTTP-scaled API replica is active. Razorpay demo mode may be enabled here to show an explicitly labelled, no-charge success flow without contacting Razorpay; production startup rejects that flag. Do not treat this as production.

Set either `AZURE_STORAGE_CONNECTION_STRING` or an HTTPS `AZURE_STORAGE_ACCOUNT_URL`, plus `AZURE_STORAGE_CONTAINER`. Managed identity is preferred with the account URL. As a temporary demo-only fallback, `TASKS_EAGER=true` may be paired with local storage so extraction runs inside the API request. Startup now rejects asynchronous staging with local storage because separate containers do not share their local filesystems.

Use the Supabase session pooler on port `5432` for Azure Container Apps. Supabase's direct database hostname is IPv6-only for this project, while the shared session pooler is IPv4-compatible. Migrations should continue to use the direct owner connection from a trusted IPv6-capable environment; the Azure runtime uses only the restricted application role.

Production still requires durable private object storage, managed Redis with `noeviction`, independently scaled worker/scheduler processes, malware scanning, complete Razorpay settings, and tested backups. These services are deliberately excluded from the student deployment until their recurring cost is approved.

The committed images are published by `.github/workflows/publish-container.yml` as `ghcr.io/drdev-coder/agentmesh-api:staging` and `ghcr.io/drdev-coder/agentmesh-web:staging`. The frontend image receives its public API, Supabase, and Turnstile settings at container startup through `runtime-config.js`.

Azure Static Web Apps cannot be used by this student subscription: its allowed-location policy and the service's available regions have no overlap. Hosting both images on scale-to-zero Container Apps is the no-fixed-cost fallback.

Local secret-bearing deployment manifests must be named `*.generated.yaml` or `*.generated.json`; these names are ignored by Git and should be deleted after applying them. Container App secret values must never be committed.
