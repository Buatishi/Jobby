# DECISIONS.md — JobMatch AI

Registro de decisiones técnicas del TP Integrador. Fuente única de verdad para Codex y
para el documento de decisiones técnicas de la consigna (sección 4.7).

Reglas de uso:
- Una decisión acá es **aprobada**: no se reabre, no se reinterpreta, no se propone
  alternativa salvo que el usuario la reabra explícitamente en este archivo.
- Antes de que una decisión esté acá, es solo una opción investigada — no se implementa.
- Cada entrada nueva se agrega al final, no se reordena ni se edita retroactivamente
  (si una decisión cambia, se agrega una entrada nueva que reemplaza a la anterior y se
  aclara el motivo del cambio).

Estado de las 7 decisiones pendientes originales:

| # | Decisión | Estado |
|---|---|---|
| 1 | Entidad para CRUD completo | ✅ Cerrada |
| 2 | Dónde persistir el rol admin | ⏳ Pendiente |
| 3 | Cómo medir el 65% de cobertura | ✅ Cerrada |
| 4 | Entorno aislado para tests de integración | ✅ Cerrada |
| 5 | Bucket real de producción (`cv-docs` vs `cv-documents`) | ✅ Cerrada |
| 6 | Cómo conectar el gate de CI con Vercel/Render | ⏳ Pendiente |
| 7 | Si la infraestructura actual aguanta Celery | ⏳ Pendiente |

---

## Decisión 1 — Entidad para el CRUD completo obligatorio

**Estado:** Aprobada.

**Elegida:** `job_descriptions` (endpoints en `services/api/app/api/v1/jobs.py`).

**Alternativas evaluadas:** `interview_kits` (descartada: depende de plan premium, perfil
100% y Claude — más frágil para la demo), `uploaded_documents` (descartada: DELETE no
limpia el archivo de Storage, deuda técnica previa), `master_profiles` y `job_matches`
(descartadas: violan el diseño del dominio — perfil único por usuario, match es un
resultado calculado, no algo que el usuario cree manualmente).

**Fundamento:** forma parte del flujo core gratuito, ya tiene creación y listado
funcionando, requiere solo dos endpoints nuevos, y ya cuenta con una regla de negocio
negativa real y probada (perfil <60% → 403).

**Reglas de implementación definidas:**

1. **Creación**: `POST /jobs/analyze` (202, asíncrono vía Celery) ya cumple el requisito.
   No se modifica.
2. **Edición** (`PATCH /jobs/{job_id}`): solo metadata editable — `job_title`,
   `company_name`, `required_seniority`, `required_modality`, `salary_min`, `salary_max`,
   `currency`. NO se edita `raw_text` ni `source_url` (dispararían re-análisis por IA,
   fuera de alcance). El PATCH no recalcula MatchScore ni embeddings.
3. **Eliminación** (`DELETE /jobs/{job_id}`): si existen `job_matches` o `interview_kits`
   derivados de ese job, responder `409 JOB_HAS_DEPENDENT_RESULTS` y no borrar. Si no
   existen, hard-delete de la fila. No se implementa soft-delete ni columna `deleted_at`.

**Prestación resignada:** no se puede editar el contenido original del job ni recalcular
el match desde el PATCH; si se necesita reanalizar, el usuario debe crear un job nuevo.

---

## Decisión 2 — Dónde persistir el rol admin

**Estado:** Pendiente.

Opciones en evaluación: columna en tabla `users` (igual que `tier`) vs. claim en
`app_metadata` del JWT de Supabase Auth. Falta investigación de Codex sobre costo de
cada una en `dependencies.py` / `auth.py`, y confirmación del usuario.

---

## Decisión 3 — Cómo medir el umbral de cobertura del 65%

**Estado:** Aprobada.

**Elegida:** el 65% eliminatorio aplica **solo al backend** (`services/api`), tal como
exige la consigna — no es un número combinado con el frontend.

**Alternativas evaluadas:** (a) umbrales separados por ecosistema, cada uno con su
herramienta nativa — elegida; (b) cobertura combinada en un solo número vía herramienta
externa (ej. Codecov) — descartada por agregar dependencia/costo externo y ser más difícil
de defender oralmente.

**Fundamento:** sin herramientas nuevas, sin costo, fácil de explicar en la defensa
("medimos cada ecosistema con su herramienta nativa").

**Mecanismo de implementación:**
- `pytest --cov=app --cov-fail-under=65` como paso del job `backend` en `ci.yml`.
- El push a GitHub **siempre se sube** — lo que se bloquea es el deploy, no el push.
- Un job `deploy` depende (`needs:`) de que el job `backend` (tests + cobertura) termine
  en verde. Si falla, el deploy no se dispara.
- El frontend no lleva umbral eliminatorio (la consigna lo deja opcional/sumador en la
  rúbrica), pero el grupo puede medirlo igual con `vitest --coverage` sin que sea gate.

**Aclaración importante:** el usuario mencionó inicialmente "sobre todo el código" y
luego confirmó que el requisito eliminatorio real es solo backend. Se deja registrado por
si en la defensa se pregunta por qué el frontend no tiene gate: es así porque la consigna
(sección 3.7.3) lo dice explícitamente.

---

## Decisión 4 — Entorno aislado para los tests de integración

**Estado:** Aprobada.

**Diagnóstico previo confirmado:** los tests actuales (`conftest.py` + `FakeSupabase` en
`tests/fakes.py`) usan una simulación en memoria, no PostgreSQL real. No cumplen por sí
solos la definición de "integración con base real" que exige la consigna. Sirven como
tests rápidos de componente, pero no reemplazan el requisito.

**Elegida:** segundo proyecto Supabase (plan Free), dedicado exclusivamente a testing,
separado del proyecto productivo `Jobby`.

**Alternativas evaluadas:** (a) schema separado dentro del proyecto productivo —
descartada: no separa de verdad (mismo Auth/Storage productivos, riesgo de tocar datos
reales con `service_role`); (b) PostgreSQL efímero en GitHub Actions — descartada como
única solución: el backend habla HTTP/PostgREST contra Supabase, no SQL directo, así que
un Postgres genérico no reproduce Auth/Storage/PostgREST reales.

**Fundamento:** máxima fidelidad (Auth, Storage, RLS, pgvector reales), costo USD 0
(quedaba 1 slot Free libre en la cuenta, confirmado en el dashboard), y el cliente actual
puede seguir usando la misma interfaz sin cambios de código en `database.py`.

**Condiciones de implementación:**
- Variables mínimas obligatorias en CI: `TEST_SUPABASE_URL`, `TEST_SUPABASE_SERVICE_ROLE_KEY`.
- La suite debe fallar de forma cerrada si estas variables faltan; nunca debe reutilizar
  automáticamente las variables productivas `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`.
- Las 22 migraciones son reutilizables sin cambios sobre el proyecto nuevo vacío,
  aplicadas una sola vez y en orden numérico (verificado: sin `INSERT...SELECT` desde
  datos productivos, sin seeds con información personal).
- Riesgo operativo a vigilar: Supabase pausa proyectos Free tras una semana de
  inactividad — reactivar el proyecto de pruebas antes de la Semana 10-11 si no se usó
  seguido.

**Prestación resignada:** dependencia de una segunda cuenta/proyecto externo a mantener
activo; algo más lento que un mock en memoria para correr la suite localmente.

---

## Decisión 5 — Bucket real de producción

**Estado:** Aprobada.

**Diagnóstico confirmado (código + verificación manual en el dashboard de Supabase):**
existen físicamente **los dos buckets** en producción, pero no son equivalentes:

| Bucket | Políticas | Límite | Tipos permitidos |
|---|---|---|---|
| `cv-documents` | 4 (coincide con las políticas SELECT/INSERT/UPDATE/DELETE de la migración 017) | Unset (50 MB) | Any |
| `cv-docs` | 0 | 10 MB | solo `application/pdf` |

`cv-documents` es el bucket real y correcto: coincide con la migración, con el frontend
(`wizard/step-2/page.tsx`) y con el parsing (`tasks/parsing.py`). `cv-docs` es un bucket
huérfano sin políticas, usado únicamente por `account_deletion.py`.

**Hallazgo de seguridad/privacidad derivado (no es solo un tema de nomenclatura):**
`account_deletion.py` usa la `SERVICE_ROLE_KEY`, que evita las políticas de Storage igual
que evita RLS. Esto significa que, en el estado actual, al borrar una cuenta el sistema
intenta eliminar archivos del bucket vacío `cv-docs`, mientras los CV reales del usuario
permanecen sin borrar en `cv-documents`. Es un bug de privacidad activo, no solo una
inconsistencia cosmética.

**Acción definida:**
1. Corregir `account_deletion.py`: `DOCUMENTS_BUCKET = "cv-documents"`.
2. Corregir `README.md` (referencia a `cv-docs` en la sección de instalación).
3. Eliminar manualmente el bucket huérfano `cv-docs` desde el dashboard de Supabase, una
   vez que el código ya no lo referencie.

**Prestación resignada:** ninguna — es una corrección de un bug, no un trade-off.

---

## Decisión adicional — Alcance del rol admin (reafirmada, no reabierta)

**Estado:** Aprobada (reconfirmación).

Se recibió un documento externo de recomendaciones (`recomendaciones.md`) que proponía
ampliar el admin a gestión de usuarios y moderación de puestos. Se evaluó y se **descartó
explícitamente**: el admin se mantiene acotado a solo métricas agregadas, sin acceso al
contenido de CV, tal como estaba definido desde el inicio del proyecto. El resto de ese
documento (login con Google, ya implementado; fórmula de matching no dependiente 100% de
IA, ya implementada; entidad "Postulaciones" y "CV adaptado", no evaluadas para este
trimestre) queda fuera del alcance del TP salvo decisión explícita en contrario.

---

## Decisión 5 — Bucket real de producción

**Estado:** Pendiente.

Inconsistencia detectada: `017_storage_bucket_policies.sql` declara `cv-documents`,
`account_deletion.py` usa `cv-docs`. Pendiente de que Codex liste todas las ocurrencias
en el código y de confirmación del usuario sobre cuál es el nombre real en Supabase.

---

## Decisión 6 — Cómo conectar el gate de CI con Vercel/Render

**Estado:** Pendiente.

Dos caminos en evaluación: (a) desactivar auto-deploy nativo y moverlo a un step de
GitHub Actions con `needs:` sobre el job de tests; (b) dejar auto-deploy nativo pero
agregar un required status check que bloquee el merge a `main`. Pendiente de
investigación de Codex sobre la configuración actual y de decisión del usuario sobre cuál
cumple más literalmente el requisito de la consigna (bloquear el *despliegue*, no solo el
merge).

---

## Decisión 7 — Si la infraestructura actual (Render free) aguanta Celery

**Estado:** Pendiente.

Pendiente de investigación de Codex sobre límites del plan free de Render para workers en
background (especialmente el worker de scraping con Playwright, más pesado) y si
migrar de plan entra en el presupuesto de USD 20/mes.

---

## Decisión 2 — Dónde persistir el rol admin (cierra la pendiente)

**Estado:** Aprobada (2026-09-20).

**Elegida:** columna `role` en la tabla `users` (`'user'` o `'admin'`, por defecto
`'user'`), en una migración nueva (023). Se lee en `get_current_user` y se exige con una
dependencia `require_admin` (403 si no es admin).

**Alternativas evaluadas:** claim `role` en `app_metadata` del JWT de Supabase —
descartada: el rol viajaría dentro del token y no se consultaría como un dato más del
dominio (la consigna 3.4.2 pide roles persistidos), y un cambio de rol no se reflejaría
hasta renovar el token.

**Fundamento:** mismo patrón que `tier`, testeable contra la base de pruebas y sin
depender de la emisión del token. No agrega consultas: se suma `role` al select que ya
existe.

**Alcance del admin:** solo métricas agregadas, sin acceso a CVs ni a datos personales
(decisión previa reafirmada).

---

## Decisión 6 — Cómo conectar el gate de CI con Vercel y Render (cierra la pendiente)

**Estado:** Aprobada (2026-09-20).

**Elegida:** el workflow de CI tiene un job `deploy` con `needs:` sobre los jobs de
backend (tests y cobertura >= 65 %) y de frontend; corre solo en `push` a `main`. El
auto-deploy nativo de Render y de Vercel se apaga y el despliegue lo dispara ese job
mediante deploy hooks guardados como secretos de GitHub.

**Alternativas evaluadas:** dejar el auto-deploy nativo y solo exigir status checks para
mergear — descartada: bloquea el merge pero no el despliegue, que es lo que exige la
consigna 3.6.2.

**Fundamento:** un pipeline que puede fallar y cortar el despliegue.

**Prerrequisito descubierto:** GitHub Actions hoy no arranca. Cada run termina en
`startup_failure` con "The job was not started because recent account payments have
failed or your spending limit needs to be increased". Hay que resolver la facturación de
la cuenta (o pasar el repo a público) antes de implementar el gate.

**Prestación resignada:** los servicios pasan a depender de `main` y de secretos extra.

---

## Decisión 7 — Actualización de evidencia (2026-09-20)

**Estado:** Pendiente, con evidencia nueva.

Los Deployments de GitHub muestran un único servicio de Render (`jobmatch-api`); no se
observan deploys de `jobmatch-worker-*`. Existe además un proyecto de Railway
(`elegant-energy / production`) con 6 deploys entre 2026-06-30 y 2026-07-15. Un
`GET /api/v1/tasks/{id}` con un id inexistente respondió 500 en producción. Hay que
confirmar en los dashboards dónde corre (o si corre) el worker de Celery antes de
declarar la cola como tecnología avanzada (Decisión 9).

---

## Decisión 8 — Datos inválidos responden 400

**Estado:** Aprobada (2026-09-20).

**Elegida:** el handler global de `RequestValidationError` responde 400 con código
`VALIDATION_ERROR`, y se agregan límites (`Field`) a las entradas más expuestas (por
ejemplo `raw_text`).

**Alternativas evaluadas:** mantener 422 (default de FastAPI) y justificarlo — descartada:
la consigna 3.2 y 3.7.2 piden 400.

**Prestación resignada:** se aparta del default de FastAPI; hay que actualizar tests y
cualquier consumidor.

---

## Decisión 9 — Tecnología avanzada declarada: cola de tareas

**Estado:** Aprobada (2026-09-20), condicionada a la Decisión 7.

**Elegida:** cola de tareas (Celery + Redis) como única capacidad declarada. Parsear un
CV y analizar un puesto con IA tarda entre 10 y 60 s y no puede bloquear la petición
HTTP: la API responde 202 con un `task_id`, un consumidor independiente procesa la tarea
y el frontend sigue el estado por SSE.

**Alternativas evaluadas:** declarar además integración con terceros y almacenamiento de
archivos — descartada: la consigna recomienda una sola capacidad, comprendida en
profundidad, y una adicional resuelta de forma deficiente resta.

**Prestación resignada:** depende de que un worker corra de forma sostenida (costo o
plan de Render, o el proyecto de Railway).

---

## Decisión 10 — Diagramas como código con PlantUML

**Estado:** Aprobada (2026-09-20).

**Elegida:** PlantUML: texto versionable en el repo y editable sin asistencia de IA. Los
PDF se generan desde HTML con Microsoft Edge en modo headless.

**Alternativas evaluadas:** draw.io — edición visual, pero el archivo no se revisa como
texto en un diff.

**Herramientas instaladas (2026-09-20, fuentes oficiales, SHA-256 verificado):** Temurin
JRE 21 (Adoptium) y `plantuml.jar` 1.2026.8 (repositorio `plantuml/plantuml`), fuera del
repo, en `C:\Users\juany\tools`.

---

## Decisión 11 — Estrategia de ramas

**Estado:** Aprobada (2026-09-20).

**Elegida:** `main` es el tronco y la rama de producción; el trabajo va en ramas
temáticas con prefijo (`feat/`, `fix/`, `docs/`, `test/`, `ci/`, `chore/`) integradas por
PR. `feat/jobmatch-phase-1-2` queda congelada como historial. Los hitos se etiquetan con
tags `milestone/NN-...` y el estado previo con `backup/pre-reorg-2026-09-20`. No se
reescribe historial. Detalle en `docs/00-flujo-de-ramas.md`.

**Alternativas evaluadas:** renombrar `feat/jobmatch-phase-1-2` a `main` — descartada:
rompe las integraciones (Render, Vercel, Railway) que apuntan al nombre. Subramas con la
forma `main/<algo>` — imposible: Git no admite `main` y `main/<algo>` a la vez.

---

## Decisión 12 — Protección de la rama principal

**Estado:** Aprobada como recomendación; pendiente de ejecución.

**Elegida:** mantener el repo privado y habilitar GitHub Pro (por ejemplo con el Student
Developer Pack, si corresponde) para proteger `main`. Hasta entonces la regla se cumple
por convención (PR obligatorio) y por el gate del job `deploy`.

**Hallazgo:** en el plan Free de un repo privado, GitHub responde 403 ("Upgrade to GitHub
Pro or make this repository public to enable this feature").

**Alternativas evaluadas:** repo público — habilita la protección y los minutos de
Actions, pero expone el código de un producto con usuarios reales.

---

## Aclaración — Decisión 5 duplicada

El archivo contiene dos entradas "Decisión 5". La vigente es la primera (Aprobada); la
segunda (Pendiente) es un residuo anterior y queda sin efecto. Estado del bug:
`account_deletion.py` sigue usando `cv-docs`; la corrección está en el plan.
