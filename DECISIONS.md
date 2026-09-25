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
observan deploys de `jobmatch-worker-*`. Existe además un proyecto de Railway con
6 deploys entre 2026-06-30 y 2026-07-15 y ningún servicio activo. Hay que confirmar dónde corre (o si corre) el worker de Celery antes
de declarar la cola como tecnología avanzada (Decisión 9).

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
PR. `feat/jobmatch-phase-1-2` quedó congelada como historial hasta el 2026-09-24, cuando se
borró junto con las ramas ya integradas (sus commits están en `main`). Los hitos se etiquetan con
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

---

## Actualización — Decisión 5 (2026-09-20)

**Estado:** Corregida.

El borrado de cuenta usa ahora el bucket real `cv-documents`, borra bajo el uid de
Supabase Auth (la carpeta donde el frontend sube los CV) y también las rutas
registradas en `uploaded_documents.storage_path`. Hay tests que fallan si vuelve el
bucket equivocado. Queda pendiente eliminar a mano el bucket huérfano `cv-docs` desde el
dashboard de Supabase.

---

## Decisión 13 — Repositorio público

**Estado:** Aprobada (2026-09-20).

**Elegida:** publicar el repositorio tras un saneamiento previo.

**Alternativas evaluadas:** (a) mantenerlo privado y resolver la facturación de GitHub —
descartada: no habilita la protección de rama y depende de un método de pago;
(b) GitHub Pro con el Student Developer Pack — posible, pero depende de una verificación
externa.

**Fundamento:** habilita Actions sin costo, la protección de `main` y el acceso del
docente sin invitaciones; la consigna no exige un repositorio privado.

**Saneamiento previo (verificado):** sin secretos en el historial ni archivos
`.env` o binarios versionados; guarda anti-SSRF en las URLs que visita el servidor;
`/tasks` exige autenticación y solo devuelve tareas propias; los errores hacia el usuario
no exponen detalles internos; límites de tamaño en las entradas libres; secretos de
producción sin uso eliminados de GitHub Actions; `LICENSE` (todos los derechos
reservados) y `SECURITY.md`.

**Prestaciones resignadas:** el código, los prompts y la fórmula de match quedan
visibles, y el email de autor de los commits existentes queda público (no se reescribe
historial). Los commits nuevos usan el email `noreply` de GitHub.

## Decisión 14 — Arranque en frío de la API: pre-calentamiento por intención de uso

**Estado:** Aprobada (2026-09-21).

**Elegida:** el frontend despierta la API cuando alguien abre la web (un `GET /health`
público y sin credenciales, una vez cada 10 minutos por pestaña), reintenta con espera
creciente los GET que fallan por red o por puerta de enlace (502, 503, 504) y muestra un
aviso si un pedido tarda más de 4 s. Costo: USD 0, sin servicios externos.

**Alternativas evaluadas:** (a) monitor externo cada 5 minutos — descartada como
principal: consume 720 a 744 de las 750 horas gratis del workspace de Render y, si se
agotan, Render suspende todos los servicios gratis; además `/health` no toca la base y no
evita la pausa de Supabase; (b) health check nativo de Render — no evita el sueño
(observado en logs); (c) cron job de Render — mínimo USD 1/mes; (d) GitHub Actions
programado — cuenta bloqueada y se apaga a los 60 días sin actividad; (e) optimizar la
imagen — no separable del tiempo de plataforma; (f) Render Starter (USD 7/mes) — único
arreglo total, queda para evaluar.

**Fundamento:** medición del 2026-09-21: 42,3 s el primer pedido tras inactividad y 0,24 s
el segundo; con el pre-calentamiento, una visita nueva seguida de 45 s dejó la primera
llamada real en 0,245 s. Render documenta que las instancias Free no son para producción y
no menciona los pings; UptimeRobot permite uso comercial pero el costo en horas no lo
justifica.

**Límites:** los POST no se reintentan; no evita reinicios ni deploys; no evita la pausa de
Supabase por inactividad (7 días), que se cubre con una regla operativa. Detalle, validación
y reglas en `docs/operacion/arranque-en-frio.md`.

## Decisión 15 — Tareas en segundo plano: modo local por ahora

**Estado:** Aprobada (2026-09-21). Cierra de forma provisoria la Decisión 7.

**Elegida:** en producción las tareas de parseo de CV, análisis de puestos, match y kits de
entrevista se ejecutan dentro del proceso de la API (`TASK_EXECUTION_MODE=local`), con
concurrencia acotada (`LOCAL_TASK_MAX_CONCURRENCY`, 2 por defecto). El match encadenado tras
un análisis espera su cupo (hasta 300 s) en lugar de fallar. El worker de Celery no se
despliega por ahora.

**Alternativas evaluadas:** (a) Background Worker de Render — mínimo USD 7/mes, no existe
plan gratis, se factura por segundo; (b) Render Starter para la API (USD 7/mes, siempre
despierta) combinado con el modo local; (c) worker embebido en el contenedor de la API —
descartada: comparte los 512 MB y se duerme junto con la API.

**Fundamento:** costo USD 0. Sin worker, las tareas encoladas en Redis nunca se procesaban
y el flujo central no terminaba en producción. El modo local ya existía para el parseo; este
cambio lo extiende a análisis, match y kits sin tocar el código de Celery.

**Límites:** el estado de las tareas vive en la memoria del proceso y se pierde si el
servicio se reinicia o se duerme durante una tarea; una sola instancia; comparte memoria con
la API; un pedido directo con la capacidad llena falla enseguida. El scraping por URL con
Chromium no está instalado en la imagen (pendiente aparte).

**Efecto sobre la tecnología avanzada:** la cola Celery + Redis deja de tener un consumidor
independiente en producción, así que hoy no puede declararse como capacidad avanzada
(sección 5 de `docs/00-vision.md`). La capacidad a declarar se decide cuando se resuelva el
modo de USD 7 (worker o Render Starter).

**Activación:** variable de entorno en Render, con aprobación explícita. Detalle, validación
y reversión en `docs/operacion/modo-local-de-tareas.md`.

## Decisión 16 — Herramientas de documentación y diagramas

**Estado:** Aprobada (2026-09-21).

**Elegida:** Markdown en `docs/` como fuente; Mermaid 12.0.0 (MIT) para DFD, secuencia, ER
y flujos dentro de los `.md`; PlantUML 1.2026.8 (LGPL-3.0) para el UML formal (casos de uso
y despliegue) con el `.puml` y el `.svg` versionados; PDF con `docs/tools/build_pdf.py`
(Markdown, HTML y Edge headless). Las versiones se fijan y verifican por hash en
`docs/tools/tools.lock.json` y se instalan fuera del repositorio, en `~/tools`. La skill
`frontend-design` de Anthropic se instaló a nivel usuario para una pasada visual deliberada.

**Alternativas evaluadas:** (a) solo PlantUML (lo aprobado en la visión) — se mantiene para
UML formal, pero GitHub no lo dibuja; (b) solo Mermaid — su diagrama de casos de uso es
`usecase-beta` desde la 12.0.0, todavía no apto para entregables; (c) D2 (MPL-2.0), draw.io
MCP (Apache-2.0), MkDocs Material (MIT) y tbls (MIT, requiere una base de datos) — no
hacen falta hoy; (d) Graphify — no instalada: hooks en cada búsqueda e instalación de
paquetes sin versión fija.

**Fundamento:** GitHub dibuja Mermaid de forma nativa, así que los diagramas se revisan en
el pull request; PlantUML cubre la notación UML que pide la consigna. La instalación de
Mermaid se rechaza si el hash del paquete de npm no coincide con el fijado, y el `.jar` de
PlantUML coincide con el digest oficial del release. Todo es gratuito y sin credenciales.

**Límites:** la versión de Mermaid de GitHub puede diferir de la 12.0.0 (probar la sintaxis
en un pull request borrador antes de depender de ella); el PDF requiere Microsoft Edge;
las herramientas viven en la máquina de quien documenta, no en el repositorio.

**Uso:** `docs/tools/README.md`.

## Decisión 17 — Tecnología avanzada declarada: integración con servicios de terceros

**Estado:** Aprobada (2026-09-22). Reemplaza a la Decisión 9 y cierra lo que la Decisión 15 dejó
pendiente.

**Elegida:** integración con servicios de terceros como única capacidad declarada: la pasarela
de IA propia (`services/api/app/services/ai_gateway`) con ruteo por plan (DeepSeek en el
gratuito, Claude en premium y OpenAI solo para vectores), tiempo límite de 60 s, reintentos con
espera creciente y errores públicos sanitizados. Resuelve un problema concreto: analizar un CV o
un puesto depende de servicios externos que fallan o demoran.

**Alternativas evaluadas:** (a) cola de tareas con consumidor independiente (Decisión 9) —
descartada: exige un proceso de trabajo permanente que Render no ofrece gratis (USD 7/mes,
Decisión 15) y sin él no se puede mostrar el mensaje entrando y saliendo de la cola; (b) declarar
además el almacenamiento de archivos — descartada: la consigna recomienda una sola capacidad y
descuenta si una adicional queda incompleta, y hoy `POST /profiles/documents` acepta la ruta del
archivo sin verificar que pertenezca a la persona (corregido el 2026-09-23: la ruta tiene que
estar en la carpeta de quien la registra y el perfil tiene que ser suyo);
(c) caché — el módulo nunca se usó y se quitó (Decisión 19).

**Fundamento:** es lo que el flujo central ya usa en producción, tiene tests propios (ruteo por
plan y manejo de errores) y cumple la condición de la consigna de contemplar la falla o la demora
del servicio externo, sin costo adicional.

**Prestación resignada:** la demostración en vivo depende de la disponibilidad y del saldo de los
proveedores; las tareas corren dentro de la API con su estado en memoria (Decisión 15). El
almacenamiento sigue siendo parte del producto, pero no se presenta como tecnología avanzada.

## Decisión 18 — Diagramas entregables en PlantUML

**Estado:** Aprobada (2026-09-22). Actualiza la Decisión 16 en lo que respecta a los diagramas
que se entregan.

**Elegida:** todos los diagramas entregables (DFD 0, 1 y 2, casos de uso, DER, arquitectura,
despliegue y recorrido del código) se escriben en PlantUML, con el `.puml` y el `.svg`
versionados en `docs/diagramas/`. El PDF de cada documento y una lámina A3 por diagrama se
generan con `docs/tools/build_pdf.py`. Mermaid queda solo para borradores o documentos internos.

**Alternativas evaluadas:** (a) Mermaid para DFD y DER, como indicaba la Decisión 16 —
descartada para entregables: al generar el PDF, Edge convirtió esos diagramas en imágenes (el PDF
de los DFD 0 y 1 pesaba 1 MB y su texto no era vectorial) y el acomodo automático de diagramas
grandes es difícil de controlar; (b) mezclar ambos lenguajes — dos notaciones para mantener y
explicar en la defensa, con aspecto distinto entre diagramas.

**Fundamento:** salida vectorial que se imprime nítida (letra mínima de 5,8 pt en A3), resultado
reproducible con la versión fijada por hash, notación UML completa y un solo lenguaje para todos
los diagramas. Los DFD 0 y 1 se pasaron de Mermaid a PlantUML el 2026-09-22 sin cambiar ningún
flujo: los 110 flujos se compararon uno por uno.

**Prestación resignada:** GitHub no dibuja PlantUML dentro del Markdown, así que después de editar
un `.puml` hay que regenerar su `.svg` (`python docs/tools/render_diagrams.py`) y versionar ambos;
generarlos requiere Java.

## Decisión 19 — Sin caché: el reporte ATS pide los vectores en lote

**Estado:** Aprobada (2026-09-23), en la auditoría del checkpoint. Reemplaza la tarea del plan
de código que proponía activar `ai_gateway/cache.py` para los vectores del reporte ATS.

**Elegida:** el reporte ATS pide los vectores de las palabras clave y de los términos del CV en
dos lotes (`embed_many`), y el módulo de caché, que nunca se había conectado, sale del código.

**Alternativas evaluadas:** (a) activar la caché en Redis para esos vectores — descartada: el
primer reporte de cada puesto seguiría haciendo cientos de llamadas en serie; la consigna define
la caché como una capa que evita consultar la base de datos, y esta no lo haría; y sumarla como
segunda capacidad avanzada resta si queda incompleta (Decisión 17); (b) dejar el módulo sin uso
— descartada: código muerto que la documentación tenía que explicar.

**Fundamento:** con 10 palabras faltantes y 40 términos en el CV, el reporte hacía 410 llamadas
a OpenAI una detrás de otra; ahora hace 2, con el mismo resultado. Un test cuenta las llamadas y
falla con el código anterior.

**Prestación resignada:** dos reportes seguidos del mismo puesto vuelven a pedir los vectores
(dos llamadas por reporte).

## Decisión 20 — La clave pública no accede a las tablas

**Estado:** Aprobada (2026-09-23). Migración 025, aplicada en el proyecto de pruebas y en
producción.

**Elegida:** los roles `anon` y `authenticated` de Supabase no tienen ningún privilegio sobre las
tablas de `public`, ni sobre las que se creen después. La web usa Supabase solo para Auth y para
subir el PDF al Storage; todos los datos pasan por la API, que usa la clave de servicio.

**Alternativas evaluadas:** (a) quitar el permiso de escritura solo en las columnas de cobro de
`users` — descartada: el mismo problema existía en las otras tablas (por ejemplo, registrar en
`uploaded_documents` la ruta del CV de otra persona y pedir que se procese); (b) un trigger que
rechace cambios de `tier` — descartada: cubre una columna y deja el resto abierto; (c) dejarlo
como estaba, confiando en las políticas RLS — descartada: esas políticas solo exigían que la fila
fuera propia, no qué columnas se podían cambiar.

**Fundamento:** con la clave pública y su propio token, una persona podía cambiarse el plan a
premium por la API REST de Supabase sin pasar por la API ni por el pago. Se reprodujo en el
proyecto de pruebas antes del cambio y quedó bloqueado después (`services/api/tests/sql/`). En
producción no había cuentas premium, así que nadie lo aprovechó.

**Prestación resignada:** una función futura que quiera leer datos desde el navegador tiene que
pasar por la API o pedir un permiso explícito en su migración.

## Decisión 21 — Roles con permisos guardados como datos

**Estado:** Aprobada (2026-09-24). Migración 026, aplicada primero en el proyecto de pruebas.

**Elegida:** dos roles, `user` y `admin`, en la tabla `roles`; sus permisos en
`role_permissions` (hoy `admin` tiene `metrics:read`); el rol de cada persona en `users.role`,
con `user` por defecto. Cada endpoint exige un permiso con `require_permission`, que consulta en
la base los permisos del rol de quien llama. El administrador ve métricas agregadas en `/admin`
(`GET /admin/metrics`), calculadas por una sola función de la base y filtradas por el modelo de
respuesta: nunca CV ni datos personales de otra persona. La web muestra la opción solo si
`GET /users/me` informa el permiso, y un 403 se explica en pantalla en vez de mandar al login.

**Alternativas evaluadas:** (a) una columna `is_admin` o comparar `role == "admin"` en el código
— descartada: la consigna no admite la comparación literal y cada permiso nuevo obligaría a
cambiar código; (b) el rol en los metadatos del token de Supabase — descartada: un cambio de rol
exige renovar la sesión y el dato queda fuera del modelo del dominio; (c) un solo campo para rol
y plan — descartada: son ejes independientes (`AGENTS.md`).

**Fundamento:** la consigna pide roles persistidos y consultados como cualquier dato, 403 para
quien no tiene permiso y control en el servidor. Un test da el permiso al rol `user` en la tabla
y comprueba que alcanza; otro falla si el control se cambia por una comparación de nombres. Nadie
puede cambiarse el rol desde el navegador: la clave pública no tiene privilegios sobre las tablas
(Decisión 20).

**Prestación resignada:** los endpoints con permiso hacen una consulta más por pedido (los
permisos no se guardan en memoria), y el rol admin se asigna con SQL en Supabase, sin pantalla.

## Decisión 22 — Cerrar sesión invalida el token al instante

**Estado:** Aprobada (2026-09-24). Migración 027, aplicada primero en el proyecto de pruebas.

**Elegida:** el botón «Cerrar sesión» pide a Supabase Auth que cierre la sesión de este
dispositivo, que la borra de `auth.sessions`, y vuelve al login con una navegación completa. La
API, además de validar la firma y el vencimiento del token, comprueba en cada pedido que la
sesión del token (`session_id`) siga abierta, con la función `session_is_active` (solo la
ejecuta la clave de servicio y devuelve un booleano). La comprobación corre en paralelo con la
lectura del usuario, así que no suma otra ida y vuelta. Si el cierre falla por conexión, la web
avisa y no sale, porque la sesión sigue abierta.

**Alternativas evaluadas:** (a) solo borrar la sesión del navegador — descartada: el token
seguiría sirviendo hasta vencer (una hora), y la consigna pide que cerrar sesión invalide el
acceso; (b) validar cada token llamando a Supabase Auth por HTTP — descartada: suma una ida y
vuelta de Oregón a São Paulo en cada pedido; (c) tokens de vida más corta — descartada: acorta
la ventana pero no la cierra y obliga a renovar más seguido.

**Fundamento:** se comprueba enviando el token de una sesión cerrada directo a la API: responde
401. Hay tests para la sesión cerrada, el token sin `session_id` y el camino validado por
Supabase Auth, y fallan si se quita la comprobación.

**Prestación resignada:** cerrar sesión cierra solo la del dispositivo actual; las abiertas en
otros dispositivos siguen hasta que se cierren o venzan.

## Actualización — Decisión 1 (2026-09-24)

**Estado:** Implementada.

`PATCH /jobs/{job_id}` y `DELETE /jobs/{job_id}` siguen las reglas de la Decisión 1. Precisiones de
la implementación:

- **Edición parcial:** cambia solo lo que se envía y un campo en `null` se borra. Cualquier otro
  campo (`raw_text`, `source_url`, `user_id`, el vector) responde 400 `VALIDATION_ERROR` sin tocar
  nada, y un cuerpo vacío, 400 `JOB_UPDATE_EMPTY`.
- **Valores válidos:** seniority `junior`, `mid`, `senior`, `staff` o `principal` y modalidad
  `remote`, `hybrid` u `onsite`: los mismos que entiende el cálculo del MatchScore, que ignoraría
  otro texto. La moneda es un código de tres letras en mayúsculas y los salarios, enteros de 0 a
  100 millones. Si se toca el salario, el mínimo no puede superar al máximo (400
  `JOB_SALARY_RANGE_INVALID`); un rango viejo mal detectado por la IA no impide corregir otro dato.
- **Borrado:** 409 `JOB_HAS_DEPENDENT_RESULTS` si hay comparaciones o kits, con el detalle de
  cuáles, y 204 si no. Las claves foráneas borrarían en cascada, pero la API no llega a esa
  cascada. El chequeo y el borrado no son atómicos: si una comparación termina justo entre los
  dos, la cascada la borra junto con el puesto. Es una ventana de milisegundos y la que pidió
  borrar es la misma persona.
- **Puesto ajeno o inexistente:** 404 `JOB_NOT_FOUND`, sin revelar que existe.
- **Id mal formado:** el id del puesto se valida como uuid y responde 400. Antes, con la base
  real, PostgreSQL rechazaba el valor y la API respondía 500; los tests no lo veían porque el
  simulador acepta cualquier texto. En los otros routers sigue pendiente.
- **Web:** la pantalla Jobs suma «Editar» (un formulario en la misma tarjeta que envía solo lo
  cambiado) y «Eliminar» (con confirmación, y el motivo del 409 cuando corresponde).

## Actualización — Decisión 8 (2026-09-24)

**Estado:** Ampliada.

Un dato con formato inválido que no valida FastAPI también responde 400 `VALIDATION_ERROR`:
cuando PostgreSQL rechaza un valor por su formato (código `22P02`, por ejemplo un id que no es
uuid en `/matches/{id}` o en el cuerpo de un pedido), el manejador global de errores de Supabase
lo traduce a 400 en lugar de 500. Cubre todas las rutas de una vez, incluidas las que se agreguen.
Los puestos, además, validan su id como uuid antes de consultar la base (Decisión 1). Cualquier
otro error de la base sigue respondiendo 500 y queda registrado.

## Actualización — Decisión 17 (2026-09-24)

**Estado:** Ajustada.

La pasarela de IA reintenta solo lo que puede andar en otro intento: fallas de red, tiempo
agotado (408), demasiados pedidos (429) y errores del proveedor (5xx). Cualquier otro 4xx, como
una clave rechazada o sin saldo (401), falla en el primer intento, y una clave que falta falla
antes de intentar. Antes, un CV con la clave de OpenAI rechazada esperaba 60 s (dos esperas de
30 s) hasta marcarse como fallido, y DeepSeek o Claude esperaban 90 s; esa espera además ocupaba
uno de los dos lugares de tareas simultáneas del modo local.

## Aclaración — Decisión 17 (2026-09-24)

La actualización anterior decía que una clave «sin saldo» responde 401, y no es así: cada
proveedor lo avisa distinto. DeepSeek responde 402 y Anthropic 400, y ninguno de los dos se
reintenta. OpenAI responde 429 con el código `insufficient_quota`, el mismo estado que usa para
un límite de pedidos por minuto, y la pasarela lo reintentaba 60 s. Ahora la pasarela distingue
los dos casos: la falta de saldo falla en el primer intento, con un error que lo dice, y el
límite de pedidos se sigue reintentando.
