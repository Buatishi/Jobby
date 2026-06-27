# Frontend - Next.js 15

## Stack

- Next.js 15 App Router with strict TypeScript.
- Tailwind CSS 3 for styling.
- shadcn/ui for base UI components.
- Supabase Auth for authentication, using the browser client in `lib/supabase/client.ts`.
- API calls must use the JWT-aware wrapper in `lib/api/client.ts`; never call `fetch` directly from app code.

## Route Structure

- `app/(public)/` contains unauthenticated pages such as landing and pricing.
- `app/(auth)/` contains login and registration flows.
- `app/(app)/` contains authenticated product routes such as dashboard, profile, jobs, ATS, and interview kits.

Keep route-specific components close to their route when they are not shared. Promote reusable UI only when it is used across multiple routes.

## Component Conventions

Use Server Components by default. Add `"use client"` only when a component needs browser-only APIs, React state, effects, event handlers, or client-side auth behavior.

Use shadcn/ui for all base components. Do not add another UI component library. Semantic score colors must come from `lib/utils/score-colors.ts`; do not hardcode hex colors for match, warning, success, or failure states.

## Commands

Run these from `apps/web/`:

- `pnpm dev` starts the local development server.
- `pnpm build` creates a production build.
- `pnpm typecheck` runs TypeScript validation.
- `pnpm lint` runs the frontend lint rules.

Before opening a PR that touches frontend code, run `pnpm typecheck && pnpm lint`.

## Agent Notes

Follow the root `AGENTS.md` for repository-wide rules. Keep code identifiers and UI implementation in English. Use Spanish comments only when they clarify intent or a non-obvious edge case.
