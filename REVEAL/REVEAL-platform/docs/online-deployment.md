# REVEAL Online Deployment

This repository is ready to be deployed online with the following split:

- `Vercel`: REVEAL frontend and Next.js API routes
- `Railway`: Python `analysis-service`
- `Railway Postgres`: shared database for users, sites, and saved application state

The active code roots are:

- frontend: [`frontend`](../frontend)
- analysis service: [`analysis-service`](../analysis-service)

The legacy `backend` folder is not required for the current Vercel + Railway deployment path.

## Architecture

The intended production flow is:

1. browser -> Vercel frontend
2. frontend server routes -> Railway analysis service
3. frontend -> Railway Postgres via Prisma

This means:

- Vercel needs `DATABASE_URL`, `NEXTAUTH_*`, Azure auth settings, mail settings, and `PYTHON_SERVICE_URL`
- Railway needs the Python service env vars and optional CDS / ERA credentials

## 1. Prepare GitHub

Push the REVEAL code to the GitHub repo and deploy from:

- repo: `8p24TW/dolfines-data-services-products`
- Vercel root directory: `REVEAL/REVEAL-platform/frontend`
- Railway root directory: `REVEAL/REVEAL-platform/analysis-service`

## 2. Create Railway Postgres

Create a Railway Postgres instance first and copy its connection string.

Use that connection string for:

- `DATABASE_URL` in Vercel

Then apply the schema from the frontend directory:

```powershell
cd REVEAL\REVEAL-platform\frontend
npx prisma migrate deploy
```

If you are not using tracked migrations yet for a given change set, use:

```powershell
npx prisma db push
```

## 3. Deploy analysis-service on Railway

The Python service already includes:

- [`Dockerfile`](../analysis-service/Dockerfile)
- [`railway.json`](../analysis-service/railway.json)
- [`analysis-service/.env.example`](../analysis-service/.env.example)

Required Railway env vars:

- `LOG_LEVEL`
- `WEATHER_CACHE_PATH`
- `LONG_TERM_CACHE_DIR`
- `TMP_DIR`
- `PLAYWRIGHT_BROWSERS_PATH`

Optional Railway env vars:

- `CDS_API_URL`
- `CDS_API_KEY`

Recommended values:

- `WEATHER_CACHE_PATH=/app/cache/weather_cache.json`
- `LONG_TERM_CACHE_DIR=/app/cache/long-term`
- `TMP_DIR=/tmp/reveal-analysis`
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`

After deploy, confirm:

- `/health` returns `200`
- the service has a public Railway URL

## 4. Deploy frontend on Vercel

The frontend now includes:

- [`frontend/vercel.json`](../frontend/vercel.json)
- [`frontend/.env.example`](../frontend/.env.example)

Set the Vercel project root to:

- `REVEAL/REVEAL-platform/frontend`

Required Vercel env vars:

- `DATABASE_URL`
- `PYTHON_SERVICE_URL`
- `NEXTAUTH_URL`
- `NEXTAUTH_SECRET`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

Optional Vercel env vars:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_SECURE`

Important production rules:

- `PYTHON_SERVICE_URL` must be the public Railway URL, not localhost
- `NEXTAUTH_URL` must be the real Vercel domain or custom domain
- `DATABASE_URL` must point to the hosted Postgres instance

REVEAL already throws a clear production error if `PYTHON_SERVICE_URL` still points to localhost.

## 5. Deploy order

Recommended sequence:

1. create Railway Postgres
2. apply Prisma schema
3. deploy `analysis-service` to Railway
4. copy Railway public URL
5. set Vercel env vars
6. deploy `frontend` to Vercel

## 6. Smoke test checklist

Once both services are online, verify:

- login works
- dashboard loads
- sites can be listed and edited
- knowledge base loads
- charting upload works
- performance page loads
- price forecast loads
- retrofit BESS page loads

## 7. Storage assumptions

The current cloud-ready version is safe for:

- temporary request uploads
- generated temporary analysis files
- cached reference data inside the Railway container filesystem

That is acceptable for early iteration with one or two users, but it is not durable storage.

Later, move larger persistent assets to object storage:

- SCADA uploads
- long-term generated files
- report exports

## 8. Notes

- local Docker remains useful for local development
- Docker Compose is not the production hosting method anymore
- the `version` field in [`docker-compose.yml`](../docker-compose.yml) is obsolete and can be removed later
