# Repository Guidelines

## Project Structure & Module Organization

JobMatch AI is a monorepo with three main workspaces:

- `apps/web/` contains the Next.js 15 frontend using strict TypeScript.
- `services/api/` contains the FastAPI backend targeting Python 3.13+.
- `packages/shared-types/` contains shared TypeScript types consumed by other packages.

Keep changes scoped to the relevant workspace. Do not modify `services/api/migrations/` unless explicitly instructed. For SQL schema changes, create a new migration rather than editing one that has already been applied.

## Build, Test, and Development Commands

Run the relevant CI checks before opening a PR:

- `cd apps/web && pnpm typecheck && pnpm lint` checks frontend types and lint rules.
- `cd services/api && poetry run mypy app/ && poetry run pytest` checks backend typing and tests.
- `cd packages/shared-types && pnpm build` builds the shared TypeScript package.

Do not install new dependencies unless the prompt or issue explains why they are needed.

## Coding Style & Naming Conventions

Write code identifiers, APIs, filenames, and commit messages in English. Comments should be in Spanish and should explain intent, edge cases, or non-obvious behavior.

Use strict TypeScript practices in the frontend and shared packages. Do not use `any`; prefer precise types, discriminated unions, generics, or `unknown` with narrowing. Backend code should use async functions throughout and must not run blocking work on the event loop.

## Testing Guidelines

Every PR should include tests for new behavior. Place tests near the relevant workspace conventions, for example backend tests under the FastAPI test suite and frontend tests alongside or near the related feature when the project structure supports it.

Before requesting review, run the workspace checks listed above and fix failures locally.

## Commit & Pull Request Guidelines

Keep commits focused and descriptive, using concise English summaries such as `Add candidate matching endpoint` or `Fix shared job status type`.

Pull requests should include a clear description, linked issue or task when available, test results, and screenshots or recordings for user-facing frontend changes. Call out migrations, environment variable changes, and any skipped checks explicitly.

## Security & Configuration

Never hardcode secrets, tokens, credentials, or private URLs. Use backend environment configuration through `config.py` and frontend values through `.env.local`. Document any new required environment variables in the relevant workspace documentation or PR description.
