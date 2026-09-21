# Jobby Load Tests

These k6 scripts provide repeatable, non-destructive load checks for the
deployed frontend/backend pair.

> Ejecutá estas pruebas solo contra tu propio entorno. No las apuntes a servicios de
> terceros ni a producción sin autorización.

## Requirements

- Install k6: https://k6.io/docs/get-started/installation/
- Set environment variables before running:

```powershell
$env:FRONTEND_URL="https://<tu-frontend>"
$env:API_URL="https://<tu-api>"
$env:AUTH_TOKEN="<supabase-access-token>"
```

`AUTH_TOKEN` is required only for authenticated API scenarios.

## Scenarios

Light navigation and health checks:

```powershell
k6 run tests/load/light.js
```

Authenticated dashboard/profile reads:

```powershell
k6 run tests/load/medium.js
```

Heavy job-analysis smoke test:

```powershell
$env:ENABLE_HEAVY="true"
k6 run tests/load/heavy.js
```

The heavy script intentionally runs with low concurrency by default. Increase
virtual users gradually: 1, 5, 10, 15, 20. Do not run destructive or AI-heavy
tests against production unless you accept provider cost and quota usage.

