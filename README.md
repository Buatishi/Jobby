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
- [docs/00-propuesta.md](docs/00-propuesta.md): propuesta de proyecto (semana 1).
- [docs/01-dfd.md](docs/01-dfd.md): diagramas de flujo de datos, niveles 0 y 1.
- [docs/02-casos-de-uso.md](docs/02-casos-de-uso.md): diagrama de casos de uso y narrativas de los tres principales.
- [docs/03-dfd-nivel-2.md](docs/03-dfd-nivel-2.md): DFD nivel 2 de los procesos 2 (CV y perfil) y 4 (compatibilidad).
- [docs/04-modelo-de-datos.md](docs/04-modelo-de-datos.md): modelo entidad-relación verificado contra la base real.
- [docs/06-arquitectura-y-despliegue.md](docs/06-arquitectura-y-despliegue.md): componentes, protocolos y puertos, secretos, recorrido hasta producción y ambiente local.
- [docs/07-decisiones-tecnicas.md](docs/07-decisiones-tecnicas.md): decisiones técnicas de la Etapa 1 y declaración de uso de IA.
- [docs/pdf/](docs/pdf/): la documentación de la Etapa 1 en PDF, generada con `docs/tools/build_pdf.py`.
- [docs/operacion/arranque-en-frio.md](docs/operacion/arranque-en-frio.md): arranque en frío de Render y reglas de suspensión de los planes gratuitos.
- [docs/operacion/modo-local-de-tareas.md](docs/operacion/modo-local-de-tareas.md): tareas en segundo plano dentro de la API.
- [docs/operacion/configuracion-claude-code.md](docs/operacion/configuracion-claude-code.md): controles automáticos de Claude Code (bloqueo de `.env` y migraciones, confirmaciones).
- [docs/tools/README.md](docs/tools/README.md): diagramas con Mermaid y PlantUML, y exportación a PDF.
- [docs/05-pendientes-producto.md](docs/05-pendientes-producto.md): pendientes de producto y frontend.

## Puesta en marcha local

Requisitos: Node.js 22+, pnpm 9+, Python 3.13+, Poetry 2.4+ y Docker Desktop.

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
- En Authentication → URL Configuration: **Site URL** con el dominio de producción
  (`https://jobbyweb.vercel.app`) y, en **Redirect URLs**, `https://jobbyweb.vercel.app/**` y
  `http://localhost:3000/**`. El comodín hace falta porque la vuelta de Google lleva
  `?next=` y la recuperación de contraseña vuelve a `/reset-password`; si la URL no está
  permitida, Supabase manda a la Site URL (con `localhost:3000`, el login con Google termina
  en una página que no carga).
- Configurar los proveedores de Auth (Google).
- Aplicar las políticas RLS de las migraciones antes de probar flujos con sesión iniciada.

### Rol de administración

Toda cuenta nueva tiene el rol `user`. Para que una cuenta vea las métricas agregadas en
`/admin`, se le asigna el rol `admin` desde el editor SQL de Supabase (no hay pantalla para
eso, a propósito):

```sql
update public.users set role = 'admin' where email = '<correo de la cuenta>';
```

Para quitarlo, volver a `'user'`. Qué puede hacer cada rol está en la tabla `role_permissions`
(Decisión 21); la web muestra la opción después de recargar la página.

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
poetry run pytest --cov=app --cov-fail-under=65 --basetemp=.pytest-tmp
```

Ese único comando corre toda la suite y emite el informe de cobertura. El umbral del 65 %
es el que exige la consigna y el pipeline lo aplica igual: si la cobertura baja, el CI falla
y no se despliega (Decisiones 3 y 6). Las exclusiones del cálculo están declaradas en
`[tool.coverage.run]` de `services/api/pyproject.toml`: solo la configuración y el arranque
del worker.

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
| `NEXT_PUBLIC_PRICE_MONTHLY`, `NEXT_PUBLIC_PRICE_YEARLY` | Precios que se muestran |
| `NEXT_PUBLIC_SENTRY_DSN` | Reporte de errores del servidor de la web (opcional: sin valor, Sentry no se activa) |

Secretos de GitHub para el despliegue que corre después del CI: `RENDER_DEPLOY_HOOK_URL` y
`VERCEL_DEPLOY_HOOK_URL` (ver `docs/06-arquitectura-y-despliegue.md`, sección 4).
