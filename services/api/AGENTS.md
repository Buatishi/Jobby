# Backend - FastAPI

## Stack

- FastAPI 0.115+ on Python 3.13+.
- Pydantic v2 for request and response schemas.
- Celery 5 with Redis 7 for background work.
- Supabase with PostgreSQL 17, pgvector, and Auth.
- PyJWT for JWT validation. Do not use `python-jose`.

## Project Structure

- `app/api/v1/` contains routers grouped by domain.
- `app/services/` contains business logic such as AI Gateway, MatchEngine, and CVParser.
- `app/tasks/` contains Celery task definitions.
- `app/models/` contains Pydantic request and response schemas.

Keep routers thin: validate input, call service-layer code, and return typed responses. Put reusable business rules in `app/services/`, not directly in route handlers.

## Error Schema

All endpoints must return errors using the standard shape:

```json
{"error": "mensaje legible", "code": "MACHINE_CODE", "details": {}}
```

Use a human-readable Spanish `error`, a stable uppercase machine `code`, and a structured `details` object for field errors or debugging context that is safe to expose.

## Commands

Run these from `services/api/`:

- `poetry run uvicorn app.main:app --reload` starts the local development server.
- `poetry run pytest` runs backend tests.
- `poetry run mypy app/` runs static type checks.
- `poetry run ruff check app/` runs lint checks.

Before opening a backend PR, run `poetry run mypy app/ && poetry run pytest`.

## Agent Notes

Follow the root `AGENTS.md` for repository-wide rules. All backend functions should be async unless there is an explicit, documented reason. Do not perform blocking I/O on the event loop, and do not modify `services/api/migrations/` without explicit instruction.
