# JobMatch AI (Jobby)

Jobby compara tu CV con una oferta laboral y te dice cuánto coincidís (Match Score), qué te
falta y cómo mejorar tu postulación. El plan premium suma kits de preparación para
entrevistas.

Flujo principal: registro, carga del CV, análisis, creación de un puesto, comparación, Match
Score y reporte ATS.

## En producción

| Componente | Dirección | Plataforma |
|---|---|---|
| Web | <https://jobbyweb.vercel.app> | Vercel |
| API | <https://jobmatch-api-9xel.onrender.com> (estado en `/health`) | Render |
| Base de datos, login y archivos | Supabase (PostgreSQL, Auth y Storage) | Supabase |

La API corre en el plan gratuito de Render: si pasa 15 minutos sin uso se duerme y el primer
pedido puede tardar unos 40 segundos. La web la despierta al abrirse. Más detalle en
[docs/operacion/arranque-en-frio.md](docs/operacion/arranque-en-frio.md).

## Estructura del proyecto

- `apps/web`: frontend (Next.js 15).
- `services/api`: API (FastAPI), tareas en segundo plano e integración con Supabase.
- `packages/shared-types`: tipos de TypeScript compartidos.
- `services/api/migrations`: migraciones SQL numeradas de Supabase.
- `tests/load`: pruebas de carga con k6.

## Cómo trabajamos

`main` es la única rama principal y es la que se despliega. El trabajo se hace en ramas cortas
(`feat/`, `fix/`, `docs/`, `test/`, `ci/`, `chore/`) que se integran con pull requests. Detalle
en [docs/00-flujo-de-ramas.md](docs/00-flujo-de-ramas.md) y [docs/00-vision.md](docs/00-vision.md).

## Documentación

- [docs/00-vision.md](docs/00-vision.md): arquitectura objetivo, modelo de acceso y pendientes.
- [DECISIONS.md](DECISIONS.md): registro de decisiones técnicas (solo se agregan entradas).
- [docs/operacion/arranque-en-frio.md](docs/operacion/arranque-en-frio.md): arranque en frío de Render y reglas de suspensión de los planes gratuitos.
- [docs/operacion/modo-local-de-tareas.md](docs/operacion/modo-local-de-tareas.md): tareas en segundo plano dentro de la API.
- [docs/tools/README.md](docs/tools/README.md): diagramas con Mermaid y PlantUML, y exportación a PDF.
- [docs/05-pendientes-producto.md](docs/05-pendientes-producto.md): pendientes de producto y frontend.

## Puesta en marcha local

Requisitos: Node.js 22+, pnpm 9+, Python 3.13+, Poetry 1.8+ y Docker Desktop.

1. Levantar la infraestructura local (Redis):

   ```powershell
   docker compose up -d
   ```

2. Crear los archivos de entorno a partir de `.env.example` y completarlos. Nunca subas
   claves reales al repositorio.

3. Instalar las dependencias:

   ```powershell
   pnpm install
   cd services/api
   poetry install
   poetry run playwright install chromium
   ```

4. Levantar la API y la web (cada una en su terminal):

   ```powershell
   cd services/api
   poetry run uvicorn app.main:app --reload
   ```

   ```powershell
   cd apps/web
   pnpm dev
   ```

La web queda en `http://localhost:3000` y la API en `http://localhost:8000`.

## Migraciones de Supabase

Aplicá las migraciones de `services/api/migrations` en orden, desde el editor SQL o la CLI de
Supabase. **No edites una migración ya aplicada**: para cambiar el esquema, creá una nueva.

Configuración necesaria en Supabase:

- Activar las extensiones `pgcrypto` y `vector`.
- Crear el bucket privado `cv-documents` en Storage.
- Configurar los proveedores de Auth y permitir la URL de redirección
  `<dominio de la web>/api/auth/callback`.
- Aplicar las políticas RLS de las migraciones antes de probar flujos con sesión iniciada.

## Controles antes de un pull request

Web (desde `apps/web`):

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

API (desde `services/api`):

```powershell
poetry run ruff check app tests
poetry run mypy app/
poetry run pytest --basetemp=.pytest-tmp
```

Tipos compartidos (desde `packages/shared-types`): `pnpm build`.

Pruebas E2E (desde `apps/web`): `pnpm exec playwright test`. El flujo completo solo corre con
`E2E_LIVE=1` y **registra y borra usuarios reales**: no se ejecuta contra producción.

Pruebas de carga:

```powershell
k6 run -e API_URL=http://localhost:8000 -e AUTH_TOKEN=<jwt> tests/load/jobmatch.k6.js
```

## Despliegue

- **Web:** Vercel, desde `apps/web`. En las variables de entorno de Vercel se configuran las
  claves públicas de Supabase, la URL de la API, la URL de la web y el DSN de Sentry.
- **API:** Render, con el archivo `render.yaml` de la raíz. Railway ya no es el destino activo;
  si desplegás ahí a mano, replicá el mismo Dockerfile y las mismas variables.
- **Tareas en segundo plano:** `render.yaml` declara dos workers de Celery, pero Render no
  ofrece workers gratuitos (desde USD 7 por mes). Por eso producción ejecuta las tareas dentro
  de la API con `TASK_EXECUTION_MODE=local` (Decisión 15,
  [docs/operacion/modo-local-de-tareas.md](docs/operacion/modo-local-de-tareas.md)). Los workers
  solo aplican si se crea uno pago.
- **Redis:** Upstash, con una URL TLS:

  ```text
  rediss://default:<UPSTASH_REDIS_PASSWORD>@<UPSTASH_REDIS_HOST>:6379
  ```

### Webhook de Lemon Squeezy

En el panel de Lemon Squeezy creá un webhook que apunte a:

```text
https://<dominio de la API>/api/v1/webhooks/lemonsqueezy
```

Activá los eventos `order_created`, `subscription_created`, `subscription_updated`,
`subscription_cancelled`, `subscription_expired`, `subscription_payment_success` y
`subscription_payment_failed`. Copiá el secreto de firma en `LEMONSQUEEZY_WEBHOOK_SECRET`.

## Variables de entorno

API:

| Variable | Para qué sirve |
|---|---|
| `SUPABASE_URL` | Dirección del proyecto de Supabase |
| `SUPABASE_ANON_KEY` | Clave pública de Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave de servicio (secreta, solo backend) |
| `SUPABASE_JWT_SECRET` | Secreto para validar los tokens de sesión |
| `OPENAI_API_KEY` | Solo para generar embeddings |
| `ANTHROPIC_API_KEY` | Modelos del plan premium |
| `DEEPSEEK_API_KEY` | Proveedor de IA principal |
| `REDIS_URL` | Redis de Upstash (cola y límites de uso) |
| `TASK_EXECUTION_MODE` | `celery` (por defecto) o `local` |
| `LOCAL_TASK_MAX_CONCURRENCY` | Tareas locales simultáneas (2 por defecto) |
| `LEMONSQUEEZY_API_KEY`, `LEMONSQUEEZY_STORE_ID`, `LEMONSQUEEZY_WEBHOOK_SECRET`, `LEMONSQUEEZY_PREMIUM_VARIANT_ID` | Cobros del plan premium |
| `RESEND_API_KEY` | Envío de emails |
| `SENTRY_DSN` | Reporte de errores |
| `FRONTEND_URL` | Dirección de la web (orígenes permitidos por CORS) |

Web:

| Variable | Para qué sirve |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Conexión pública a Supabase |
| `NEXT_PUBLIC_API_URL` | Dirección de la API |
| `NEXT_PUBLIC_APP_URL` | Dirección de la web |
| `NEXT_PUBLIC_PRICE_MONTHLY`, `NEXT_PUBLIC_PRICE_YEARLY` | Precios que se muestran |
| `NEXT_PUBLIC_SENTRY_DSN` | Reporte de errores del navegador |

Secretos de GitHub para los despliegues de vista previa: `VERCEL_TOKEN`, `VERCEL_ORG_ID` y
`VERCEL_PROJECT_ID`.
