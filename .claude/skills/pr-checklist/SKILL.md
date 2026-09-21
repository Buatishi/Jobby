---
name: pr-checklist
description: Verifica un cambio de JobMatch antes de abrir el pull request y arma el resumen Requisito, Impacto, Riesgo y Prueba con resultados reales.
disable-model-invocation: true
---

# Checklist previo al pull request

Ejecutá los pasos en orden y mostrá el resultado real de cada comando. No inventes
resultados: si algo no se pudo correr, decilo.

1. **Alcance.** `git status` y `git diff --stat`. Si el cambio toca `render.yaml`,
   `.github/workflows/`, variables de entorno, webhooks o cobros de LemonSqueezy, o
   migraciones ya aplicadas, frená y avisá antes de seguir (`AGENTS.md`, sección 1).
2. **Frontend** (si cambió `apps/web`): desde `apps/web`, `pnpm typecheck`, `pnpm lint`,
   `pnpm test` y `pnpm build`.
3. **Backend** (si cambió `services/api`): `poetry run mypy app/`, `poetry run ruff check app/`
   y `poetry run pytest`, sin cargar `services/api/.env` (por ejemplo desde una carpeta
   temporal con `PYTHONPATH=services/api`). No correr el E2E vivo.
4. **Pruebas y documentación.** El comportamiento nuevo o modificado tiene test y se
   actualizó solo la documentación directamente afectada (`AGENTS.md`, sección 7).
5. **Resumen** de cuatro líneas para la descripción del PR:
   - **Requisito:** qué se pidió.
   - **Impacto:** qué workspace o módulo toca.
   - **Riesgo:** qué puede romperse (auth, roles, plan free o premium, datos de CV,
     despliegue, cobros).
   - **Prueba:** los comandos corridos y su resultado.
