# Azure student staging

The low-cost staging topology uses:

- Azure Static Web Apps Free for `frontend/dist`;
- Azure Container Apps Consumption for the API, with `minReplicas: 0` and `maxReplicas: 1`;
- public GitHub Container Registry for the API image;
- no Azure Container Registry and no Log Analytics workspace.

The current student staging deployment is intentionally a demo topology. With `APP_ENV=development`, eager tasks, local object storage, and SQLite, data is ephemeral and can disappear whenever the Container App scales down or receives a new revision. Do not treat it as production.

Production requires external PostgreSQL with a restricted non-superuser application role, durable private object storage, managed Redis with `noeviction`, separate worker/scheduler processes, malware scanning, complete Razorpay settings, and backups. These services are deliberately excluded from the student deployment until their recurring cost is approved.

The committed container image is published by `.github/workflows/publish-container.yml` as `ghcr.io/drdev-coder/agentmesh-api:staging`. GitHub Container Registry packages are private on first publication; make this package public before creating the Container App so Azure can pull it anonymously.

Local secret-bearing deployment manifests must be named `*.generated.yaml` or `*.generated.json`; these names are ignored by Git.
