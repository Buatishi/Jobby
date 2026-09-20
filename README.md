# JobMatch AI

JobMatch AI is a monorepo for matching candidates against job descriptions, improving ATS coverage, and generating premium interview preparation kits.

## Project Structure

- `apps/web` - Next.js 15 App Router frontend.
- `services/api` - FastAPI backend, Celery workers, Supabase integration.
- `packages/shared-types` - shared TypeScript contracts.
- `services/api/migrations` - numbered Supabase SQL migrations.
- `tests/load` - k6 load tests for backend workflows.

## Branching

`main` is the single trunk and the production branch. Work happens in short-lived topic
branches (`feat/`, `fix/`, `docs/`, `test/`, `ci/`, `chore/`) merged through pull requests.
See [docs/00-flujo-de-ramas.md](docs/00-flujo-de-ramas.md) and
[docs/00-vision.md](docs/00-vision.md).

## Local Setup

Prerequisites:

- Node.js 22+
- pnpm 9+
- Python 3.13+
- Poetry 1.8+
- Docker Desktop

Start local infrastructure:

```powershell
docker compose up -d
```

Create env files from `.env.example`, then install dependencies:

```powershell
pnpm install
cd services/api
poetry install
poetry run playwright install chromium
```

Run the app:

```powershell
cd services/api
poetry run uvicorn app.main:app --reload
```

```powershell
cd apps/web
pnpm dev
```

Frontend runs at `http://localhost:3000`; backend runs at `http://localhost:8000`.

## Supabase Migrations

Apply migrations in order from `services/api/migrations` using the Supabase SQL editor or CLI. Do not edit an already-applied migration; create a new numbered migration instead.

Required Supabase setup:

- Enable PostgreSQL extensions used by the migrations, including `pgcrypto` and `vector`.
- Create the `cv-docs` Storage bucket.
- Configure Auth providers and callback URLs for the frontend domain.
- Apply RLS policies from the migration set before testing authenticated flows.

## Checks

Run before each PR:

```powershell
cd apps/web
pnpm typecheck
pnpm lint
pnpm build
```

```powershell
cd services/api
poetry run ruff check app tests
poetry run mypy app/
poetry run pytest --basetemp=.pytest-tmp
```

```powershell
cd packages/shared-types
pnpm build
```

E2E tests:

```powershell
cd apps/web
pnpm exec playwright test
```

Load tests:

```powershell
k6 run -e API_URL=http://localhost:8000 -e AUTH_TOKEN=<jwt> tests/load/jobmatch.k6.js
```

## Deploy

Frontend deploys to Vercel from `apps/web`. Configure Supabase public keys, backend URL, Lemon Squeezy public app URL, and Sentry DSN in Vercel environment variables.

Backend deploys are configured for Render with `render.yaml` at the repository root. Railway is not the active backend target in this repo anymore; if you deploy there manually, mirror the same Dockerfile, worker commands, and environment variables from `render.yaml`.

Render creates:

- FastAPI web service from `services/api/Dockerfile` on port `8000`.
- Celery worker for `parsing,analysis`.
- Celery worker for `scraping`; move this off the free plan before real scraping because Playwright needs more memory.

Use Upstash Redis with a TLS URL:

```text
rediss://default:<UPSTASH_REDIS_PASSWORD>@<UPSTASH_REDIS_HOST>:6379
```

### Lemon Squeezy webhook

Create a webhook in the Lemon Squeezy dashboard pointing to:

```text
https://<render-api-domain>/api/v1/webhooks/lemonsqueezy
```

Enable these events: `order_created`, `subscription_created`,
`subscription_updated`, `subscription_cancelled`, `subscription_expired`,
`subscription_payment_success`, and `subscription_payment_failed`. Copy the
signing secret into `LEMONSQUEEZY_WEBHOOK_SECRET`.

## Environment Variables

Backend:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_JWT_SECRET`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEEPSEEK_API_KEY`
- `REDIS_URL`
- `LEMONSQUEEZY_API_KEY`
- `LEMONSQUEEZY_STORE_ID`
- `LEMONSQUEEZY_WEBHOOK_SECRET`
- `LEMONSQUEEZY_PREMIUM_VARIANT_ID`
- `RESEND_API_KEY`
- `SENTRY_DSN`
- `FRONTEND_URL`

Frontend:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_APP_URL`
- `NEXT_PUBLIC_PRICE_MONTHLY`
- `NEXT_PUBLIC_PRICE_YEARLY`
- `NEXT_PUBLIC_SENTRY_DSN`

GitHub preview deploy secrets:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
