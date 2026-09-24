# Flujo de ramas

## 1. Modelo

```
main                       tronco y rama de producción; todo se integra acá por PR
 |- feat/<tema>            nuevas funcionalidades      (feat/admin-role, feat/jobs-crud)
 |- fix/<tema>             correcciones                (fix/tasks-auth, fix/account-deletion-bucket)
 |- docs/<tema>            documentación               (docs/dfd, docs/der, docs/arquitectura)
 |- test/<tema>            tests                       (test/integration-real-db)
 |- ci/<tema>              pipeline y despliegue       (ci/coverage-gate, ci/deploy-gate)
 '- chore/<tema>           mantenimiento
```

Las ramas integradas se borran del remoto: su historial queda en `main` y cada una se puede
restaurar desde su PR. La única que se conserva es `ci/verificacion-del-corte`, evidencia de
una ejecución fallida del pipeline. `feat/jobmatch-phase-1-2`, el historial de la fase 1-2, se
borró el 2026-09-24 con el mismo criterio.

Reglas:

1. `main` es la única rama de producción. Nada se commitea directo a `main`.
2. Cada cambio vive en una rama con prefijo, corta y de un solo propósito.
3. Se integra con un pull request y un merge commit (se conservan los commits de la
   rama).
4. Antes del merge se corren en local: `pytest`, `mypy`, `ruff`, `typecheck`, `lint`,
   `vitest` y `build`. Mientras GitHub Actions no arranque (ver `00-vision.md`, sección
   10), esa es la verificación.
5. Después del merge se verifica producción (salud, 401, CORS y frontend) y, si algo
   falla, se revierte con `git revert -m 1 <merge>`.
6. El historial no se reescribe: nada de `push --force` ni `rebase` sobre ramas
   publicadas.

### Por qué no `main/<algo>`

Git guarda las ramas como archivos: si existe la rama `main`, no puede existir a la vez
`main/docs`, porque `main` tendría que ser archivo y carpeta al mismo tiempo. Por eso las
"subramas" usan prefijos propios (`feat/`, `docs/`, etc.) y se conectan a `main` por PR.

## 2. Historial: etiquetas de hitos

El historial completo (70 commits, del 2026-06-27 al 2026-09-20) está intacto. Para
ordenarlo se agregaron tags anotados sobre commits existentes; un tag solo etiqueta, no
modifica nada.

| Tag | Commit | Fecha | Contenido |
|---|---|---|---|
| `milestone/00-bootstrap` | `81eaecb` | 2026-06-27 | Monorepo, migraciones, base de la API, contratos, landing y auth |
| `milestone/01-cv-parsing-render` | `1714990` | 2026-06-27 | Parseo asíncrono de CV y despliegue en Render |
| `milestone/02-onboarding-job-analysis` | `7339179` | 2026-06-27 | Wizard y análisis de puestos de extremo a extremo |
| `milestone/03-match-ats-interview-kits` | `ebddbee` | 2026-06-28 | Motor de match, ATS, reality gap y kits de entrevista |
| `milestone/04-stripe-billing-rate-limits` | `55f6dc8` | 2026-06-28 | Facturación con Stripe y límites de uso |
| `milestone/05-account-dashboard-tooling` | `502e188` | 2026-06-29 | Cuenta, dashboard, herramientas y tests |
| `milestone/06-visual-identity-recovery` | `131666d` | 2026-07-01 | Identidad visual, recuperación de contraseña y hardening |
| `milestone/07-lemonsqueezy-billing` | `3c5779d` | 2026-07-03 | Reemplazo de Stripe por Lemon Squeezy |
| `milestone/08-i18n-legal-seo` | `dcf188f` | 2026-07-05 | i18n, páginas legales, SEO y seguridad |
| `milestone/09-sessions-frontend-proxy` | `4fa111c` | 2026-07-15 | Sesiones, fallback local y proxy del frontend |
| `milestone/10-cv-upload-ai-providers` | `bb97750` | 2026-07-15 | Subida de CV idempotente y errores de proveedores de IA |
| `milestone/11-prod-hardening` | `79abe9b` | 2026-09-20 | PR #1: ENVIRONMENT, headers, concurrencia y k6 |
| `backup/pre-reorg-2026-09-20` | `79abe9b` | 2026-09-20 | Estado de producción antes de crear `main` |

Ver el detalle de cualquiera con `git show milestone/03-match-ats-interview-kits`.

## 3. Respaldo y vuelta atrás

- Cualquier estado anterior: `git switch --detach backup/pre-reorg-2026-09-20`.
- Respaldo completo (todas las refs e historial) en un bundle fuera del repo, en la PC del
  titular: `Documents\JobMatch-backups\2026-09-20_pre-reorg\jobmatch-all-refs.bundle`.
  Verificar con `git bundle verify`; restaurar con `git clone <bundle> <carpeta>`.
- Los archivos `.env` no se versionan ni están en el bundle a propósito: guardarlos en un
  gestor de contraseñas.
- Frontend en Vercel: reasignar el alias del dominio al deployment anterior.

## 4. Puntos de integración que dependen de la rama

| Servicio | Estado |
|---|---|
| GitHub | `main` es la rama por defecto y exige pull request |
| Render (API) | Los servicios siguen `main` y se despliegan con cada merge |
| Vercel (`jobby-web`) | La rama de producción es `main`; el dominio público se asigna al promover un despliegue |
