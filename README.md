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
