# JobMatch AI

Monorepo for the JobMatch AI frontend, backend, and shared TypeScript contracts.

## Workspaces

- `apps/web` - Next.js 15 frontend.
- `services/api` - FastAPI backend.
- `packages/shared-types` - shared TypeScript API types.

## CI Commands

- Frontend: `cd apps/web && pnpm install && pnpm typecheck && pnpm lint && pnpm build`
- Backend: `cd services/api && poetry install && poetry run mypy app/ && poetry run pytest`
- Shared types: `cd packages/shared-types && pnpm install && pnpm build`

## Local Installation

Prerequisites:

- Node.js 22+
- pnpm 9+
- Python 3.13+

Install everything from the repository root:

```powershell
cd C:\Users\juany\Documents\JobMatch
.\scripts\install-all.ps1
```

Manual alternative:

```powershell
cd C:\Users\juany\Documents\JobMatch
python -m pip install -r requirements.txt
python -m playwright install chromium
pnpm install
```

Start the frontend:

```powershell
pnpm --filter @jobmatch/web dev
```

Open `http://localhost:3000`.

## Deploy on Render

Backend deploys are configured with `render.yaml` at the repository root.

1. Create an Upstash Redis database and copy its TLS URL into `REDIS_URL`.
2. In Render, create a new Blueprint from this repository.
3. Render will create:
   - `jobmatch-api` web service using `services/api/Dockerfile` on port `8000`.
   - `jobmatch-worker-analysis` for Celery queues `parsing,analysis`.
   - `jobmatch-worker-scraping` for the `scraping` queue.
     Por ahora todos los servicios usan el plan Free para validar deploys sin costo; antes de usar scraping en serio, subir este worker a un plan con al menos 512MB RAM porque Playwright corre ahí.
4. Add the required environment variables in Render:
   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
   `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `REDIS_URL`,
   `FRONTEND_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and
   `RESEND_API_KEY`.

Use an Upstash Redis TLS URL format like:

```text
rediss://default:<UPSTASH_REDIS_PASSWORD>@<UPSTASH_REDIS_HOST>:6379
```

## GitHub Secrets

Configure these repository secrets before enabling CI and preview deployments:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_PRICE_MONTHLY`
- `NEXT_PUBLIC_PRICE_YEARLY`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Production deploy is intentionally not configured yet; preview deployments only run on pull requests.
