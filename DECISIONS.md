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

## Actualización — Decisión 4 (2026-09-24)

**Estado:** Implementada.

- **Dos carpetas, un comando:** `tests/unit/` (las pruebas de siempre, con la base simulada) y
  `tests/integration/` (contra el proyecto `jobby-test`). `poetry run pytest` corre las dos, en
  el equipo y en el CI.
- **Qué es real:** la API corre dentro del proceso (httpx con `ASGITransport`) y habla con
  PostgreSQL, PostgREST y Supabase Auth del proyecto de pruebas. Solo se reemplaza la sesión por
  la persona que crea cada prueba: la validación del token ya tiene sus pruebas unitarias.
- **Datos:** cada prueba crea su propia persona en Supabase Auth (el disparador de la migración
  015 crea su fila de `users` y su perfil) y al terminar borra esa fila, que arrastra en cascada
  todo lo demás, y después la identidad. No quedan datos y ninguna prueba depende de otra.
- **Falla cerrada:** sin `TEST_SUPABASE_URL` o `TEST_SUPABASE_SERVICE_ROLE_KEY`, cada prueba de
  integración falla con un mensaje que explica qué falta. Si la URL coincide con `SUPABASE_URL`,
  se niega a correr: nunca se usan las variables de producción.
- **Casos:** POST 201, GET 200, PATCH, DELETE, 400 (dato inválido e id mal formado en cuatro
  rutas), 404 (inexistente y ajeno) y la regla del perfil al 60 %; además, que el 409 de un puesto
  con comparaciones evita la cascada real de la base.
- **Orden:** `pytest-randomly`, dependencia de desarrollo, mezcla el orden en cada corrida (3.7.6)
  y deja la semilla en el encabezado. Antes de sumarlo, la suite pasó completa con tres órdenes
  mezclados distintos.

## Actualización — Decisión 17 (2026-09-25)

**Estado:** Confirmada por el autor.

La observabilidad (consigna 3.5) no se presenta como capacidad y queda como «No aplica», igual que
la cola, la caché y el tiempo real. El sistema tiene registros en Render y Sentry opcional en la
API, pero eso no alcanza para mostrar en la defensa qué pasó en producción en un momento dado, y la
consigna advierte que una capacidad adicional resuelta de manera deficiente resta. Se prefiere una
sola capacidad, la integración con terceros, comprendida en profundidad.

## Actualización — Decisión 14 (2026-09-25)

**Estado:** Ampliada, con aprobación del autor.

Se suma una consulta periódica a `/health` desde GitHub Actions (`keep-alive.yml`): cada 10
minutos de 8 a 24, hora de Buenos Aires. Las dos razones del descarte original ya no rigen: la
cuenta de GitHub dejó de estar bloqueada, y de los tres servicios gratis del workspace de Render
solo queda activo `jobmatch-api` (`Jobby` y `Dardo-Audio` están suspendidos). Despierta unas 16
horas por día, la API usa cerca de 500 de las 750 horas gratis del mes; de noche duerme y el
pre-calentamiento de la web sigue cubriendo el primer pedido.

**Límites:** GitHub puede demorar o saltear ejecuciones programadas en horas de mucha carga, así
que puede quedar algún arranque lento; la programación se apaga sola tras 60 días sin actividad
en el repositorio; si se reactiva otro servicio gratis de Render hay que volver a hacer la cuenta
de horas. Costo: USD 0.

## Actualización — Decisión 4 (2026-09-25)

**Estado:** Ampliada.

Las pruebas unitarias tampoco salen a la red. Los registros de Supabase de producción mostraron 35
pedidos en un día a `/auth/v1/user` con el token `invalid-token`: era
`test_invalid_token_returns_401`, que en el equipo local (con el `.env` apuntando a producción)
consultaba el Supabase Auth real. No exponía datos, pero una prueba unitaria no debe depender de
producción. Ahora simula esa respuesta, y `tests/unit/conftest.py` reemplaza los transportes reales
de httpx por uno que falla: cualquier prueba que intente salir a Internet queda en rojo, aunque el
código atrape el error. Con la guarda puesta, esa fue la única que la usaba.

## Decisión 23 — Menos espera en cada paso

**Estado:** Aprobada por el autor (2026-09-25) como cuatro mejoras, un pull request cada una. Se
hicieron las tres primeras; la cuarta se descartó al medirla. Después se probó una quinta
(mover la API a Virginia) y también se descartó al medirla.

**Problema:** cada paso se sentía lento. Medido en producción: la API corre en Oregon y la base en
São Paulo, así que cada consulta a la base cuesta entre 0,19 y 0,24 s (registros de Supabase), y
un pedido autenticado hace tres o cuatro seguidas. Además, cada vez que se volvía a una sección,
la pantalla quedaba vacía hasta que respondía la API.

**Elegido:**

1. Funciones de Vercel en São Paulo (`gru1`, #36): entre 105 y 161 ms menos por página protegida.
2. El plan viaja con la sesión (#37): una consulta menos (0,21 s) al listar y analizar puestos, en
   el reporte ATS, el optimizador de CV y los kits. De paso, la web muestra el plan real.
   Verificado en producción (2026-09-26, 01:03 UTC, abriendo `/jobs` con sesión): desde el
   deploy no hay ninguna consulta `users?select=tier`, y `GET /jobs` hace tres idas y vueltas a
   la base en lugar de cuatro (sesión y usuario en paralelo, verificación del perfil, puestos).
   Después (aprobado el 2026-09-26) también salió la verificación del perfil: la migración 028
   agrega un disparador que crea el perfil maestro al insertar en `users`, y `get_current_user`
   ya no consulta `master_profiles`. Es otra ida y vuelta menos (~0,2 s) en cada pedido con sesión.
   Verificado en producción (2026-09-26, 02:43 UTC, recorriendo la app con sesión): ninguna
   consulta de verificación del perfil y ningún error en 36 pedidos a la base. `GET /jobs` pasó
   de 0,54 s a 0,22 s de base (dos idas y vueltas) y el resumen del dashboard de cuatro idas y
   vueltas (~0,9 s) a tres (~0,41 s).
3. Pantallas de carga, error y página inexistente (#39), y la última respuesta de cada pantalla en
   la memoria de la pestaña (`useApiResource`): al volver a una sección se ve al instante lo último
   y se actualiza por detrás; si la actualización falla, queda lo anterior junto con el error.
4. Descartada al medirla: que el navegador llame directo a la API, sin el proxy de Vercel. Desde
   Buenos Aires, con la conexión reutilizada como hace el navegador (10 pedidos por caso), el proxy
   suma unos 40 ms (268 ms contra 229 ms directo a Render). Ir directo obliga a una consulta previa
   de CORS de unos 190 ms por cada dirección distinta cada 10 minutos, y a abrir otra conexión con
   Render. La estimación anterior, de 200 ms por pedido, se había medido abriendo una conexión nueva
   en cada pedido.
5. Descartada al medirla: mover la API de Oregón a Virginia, que está más cerca de São Paulo
   (donde corre Supabase) y prometía unos 60 ms menos por consulta. Se creó el servicio, se
   apuntó la web a él y se midió con tráfico real en los registros de Supabase: cada ida y vuelta
   de la API a la base costó entre 0,40 y 0,50 s desde Virginia, contra 0,20 a 0,23 s desde
   Oregón. Una segunda prueba, con un token falso que obliga a una llamada a Supabase Auth, dio lo
   mismo (unos 0,45 s extra en Virginia contra 0,30 s en Oregón). Solo mejoró el tramo de Vercel
   a la API, unos 30 ms, y no compensa. Se volvió a Oregón (web, ping de mantenimiento, deploy y
   webhook de cobros). No se encontró la causa; la estimación se había hecho por distancia y no
   por medición. El servicio de Virginia quedó suspendido, no borrado.

**Privacidad:** la memoria es de la pestaña, nunca `localStorage`, y se borra al iniciar sesión,
registrarse y salir (`forgetSessionData`). Un contador descarta las respuestas pedidas con la
sesión anterior, así que una segunda cuenta en la misma pestaña no ve datos de la primera.

**No es la capacidad «caché» de la consigna (3.5):** cada visita igual consulta la API y la base;
solo evita la pantalla vacía mientras tanto. La Decisión 17 sigue declarando una sola capacidad y
la Decisión 19 (sin caché del lado del servidor) no cambia.

**Alternativas descartadas:** (a) SWR o TanStack Query: una dependencia nueva para lo que resuelve un hook propio de unas 100
líneas; (b) guardar las respuestas en `localStorage`: dejaría datos del CV en el navegador después
de cerrar la pestaña.

## Decisión 24 — El CV optimizado se verifica contra el reporte ATS

**Estado:** Aprobada por el autor (2026-10-04).

**Problema:** lo único que impedía que la IA inventara al reescribir el CV era una instrucción en
el prompt, que depende de qué tan obediente sea el modelo. Si escribía «Kubernetes» sin que la
persona lo tuviera, la web lo mostraba igual que una mejora real.

**Elegido:** después de la respuesta de la IA, `verify_sections` cruza el texto nuevo con el reporte
ATS ya calculado. Una palabra clave con estado literal o semántico tiene respaldo en el CV y queda
como agregada; una ausente, aunque la IA la haya escrito sin declararla, pasa a
`unverified_keywords` y la web avisa que solo se use si es cierta. Una palabra que la IA declaró
pero no escribió se descarta, y una que no es del puesto necesita aparecer en el CV. La búsqueda
respeta los límites de palabra («R» no está dentro de «React»). La respuesta suma
`ats_score_before` y `ats_score_after`: el segundo cuenta como literal solo una palabra semántica
que el texto nuevo nombra; las ausentes siguen ausentes.

**Costo:** ninguna llamada extra a la IA ni a los vectores; un test lo comprueba contando los
pedidos (`test_cv_optimizer_verification.py`).

**Alternativas evaluadas:** (a) una segunda llamada a la IA que revise a la primera — descartada:
duplica el costo y sigue dependiendo de un modelo; (b) volver a pedir vectores del texto nuevo para
recalcular el puntaje completo — descartada: cuesta tokens y la cobertura verificada se obtiene con
los estados que ya existen; (c) borrar del texto las palabras sin respaldo — descartada: cortar
frases generadas deja texto roto; se avisa y decide la persona.

**Origen de la idea:** se comparó con AIHawk, un generador de CV de código abierto (AGPL-3.0), que
reescribe el CV entero sin ninguna verificación. No se tomó código ni prompts de ese proyecto: su
licencia obligaría a publicar Jobby completo.

## Decisión 25 — El optimizador de CV también en el plan gratuito

**Estado:** Aprobada por el autor (2026-10-04). Cambia lo que incluye cada plan: hasta ahora el
optimizador era exclusivo de premium.

**Elegido:** el optimizador está en los dos planes, con un límite mensual en Redis
(`RateLimitKind.CV_OPTIMIZATION`): **3 por mes** en el gratuito, que usa DeepSeek, y **30 por
mes** en premium, que usa Claude. El contador se descuenta antes de llamar a la IA, como en los
puestos, y al pasarlo la API responde 429 `CV_OPTIMIZATION_RATE_LIMIT_EXCEEDED` con el límite y
la fecha en que se renueva. El Interview Kit sigue siendo solo premium.

**Fundamento:** la verificación de la Decisión 24 no depende del modelo, así que el modelo barato
tampoco puede presentar una palabra inventada como respaldada. Mostrar el CV mejorado en el plan
gratuito deja ver el valor completo del producto; premium vende más usos, un modelo mejor y la
preparación de entrevistas.

**Costo:** cada optimización del plan gratuito es una llamada a DeepSeek más el reporte ATS que
ya existía. El límite de 3 por persona y por mes acota el gasto dentro del presupuesto de USD 20
por mes del proyecto.

**Alternativas evaluadas:** (a) dejarlo solo en premium — descartada por el autor: el plan
gratuito no mostraba la mejora del CV; (b) 1 por mes en el gratuito — descartada: no alcanza para
comparar dos puestos; (c) pasar también premium a DeepSeek — descartada: `AGENTS.md` define a
Claude como la ampliación premium y hoy no hay uso premium que justifique cambiarlo.

## Decisión 26 — CV descargable en PDF

**Estado:** Aprobada por el autor (2026-10-04), que eligió sacar los datos de contacto del CV con
IA.

**Elegido:** `GET /profiles/cv` arma el CV con el perfil que la persona confirmó; si una sección
está vacía (por ejemplo, si salteó el último paso del asistente), usa lo que leyó el CV principal.
El encabezado (nombre, email, teléfono, ciudad y LinkedIn) lo extrae el lector de CV
(`contact` en `parsed_data`, sin migración: es parte del JSON del documento); si falta, se usan el
email de la cuenta y el LinkedIn del perfil. La web lo muestra en una columna con títulos
estándar, que es el formato que mejor leen los filtros ATS, y lo descarga con «Guardar como PDF»
del navegador. Antes de descargar, la persona puede corregir el contacto: esa corrección vive solo
en la pestaña y no se guarda. Desde el reporte ATS se pueden sumar las secciones optimizadas:
entran por defecto las que el CV respalda (Decisión 24); una sección cuyo fragmento original no
aparece en el CV no se aplica y se avisa, salvo el resumen y las habilidades, que se reemplazan
enteros. El prompt del optimizador fija los nombres de las secciones para poder ubicarlas.

**Datos personales:** el contacto queda en el documento del CV, que la persona ya había subido y
que el borrado de cuenta elimina en cascada. No llega al optimizador ni a las métricas del
administrador. Los CV subidos antes de este cambio no tienen contacto: se completa en la pantalla
o volviendo a subir el CV.

**Alternativas evaluadas:** (a) que la persona escriba el contacto en cada descarga — descartada
por el autor; (b) campos nuevos en el perfil maestro — descartada: exige migración y otra pantalla
para cargarlos; (c) generar el PDF en el servidor — descartada: suma una dependencia pesada a la
API (512 MB de RAM en Render) para lo que el navegador ya hace bien.

## Decisión 27 — Estética v2 para toda la web

**Estado:** Aprobada por el autor (2026-10-06), que eligió la versión v2 como la estética definitiva
de Jobby.

**Elegido:** una sola identidad visual para la landing, el acceso y el dashboard: Montserrat,
paneles oscuros con brillo verde y suelo de rejilla, botones en píldora, tarjetas blancas con
sombra suave y el anillo de match como pieza central (en el hero, la red de puestos, el
dashboard y la lista de matches). Se tomó como referencia la estructura de un sitio de
consultoría de talento (panel oscuro inset, lista que se despliega, frase que se pinta al
scrollear, columnas escalonadas), sin copiar su logo, sus textos ni sus cifras. Los colores de
estado siguen saliendo de `score-colors.ts`; sobre paneles oscuros las dos bandas verdes se
muestran con el verde vivo porque el verde oscuro no contrasta.

**Contenido:** todo número que no es de una persona real (hero, red de puestos, comparación,
ejemplos de la lista de momentos) se rotula como dato de ejemplo. Las afirmaciones del producto
salen de lo ya decidido: el optimizador va en los dos planes con 3 y 30 por mes (Decisión 25),
el administrador solo ve métricas agregadas y el CV descargable es de una columna (Decisión 26).
La página de precios y la landing siguen leyendo los límites reales de cada plan del diccionario.

**Alternativas evaluadas:** (a) tres direcciones iniciales (editorial cálida, producto denso,
oscura con acento lima) — descartadas por el autor por genéricas y poco juveniles; (b) tres
nuevas (amigable, atrevida, bolsa de trabajo moderna) — el autor pidió partir de una referencia
concreta; (c) librerías de animación (GSAP, Lottie, anime.js) y catálogos de estilos de
terceros — descartadas: la v2 se resuelve con `framer-motion`, que ya está instalado, y no suma
dependencias ni costo.

**Consecuencias:** se retiraron de la landing la sección de problema, la demo con pestañas y los
tres pasos; su contenido queda cubierto por la lista de momentos y la comparación requisito por
requisito. Las pantallas internas (perfil, jobs, ATS, kits, admin) heredan botones, tarjetas,
insignias y tipografía, y se retocan una por una en cambios aparte.

## Decisión 28 — Revisión de seguridad con herramientas propias y un workflow separado

**Estado:** Aprobada por el autor (2026-10-08), que pidió seguir con todas las fases de la
revisión.

**Elegido:** revisar el código y las dependencias con herramientas abiertas y reproducibles, y
dejar el escaneo automático en un workflow aparte (`.github/workflows/security.yml`) que no
toca los hooks de despliegue. Las herramientas son gitleaks (secretos en todo el historial),
Semgrep (análisis estático con las reglas de Python, TypeScript, React, OWASP Top 10, JWT y
secretos) y Trivy (vulnerabilidades en `poetry.lock` y `pnpm-lock.yaml`, solo altas y críticas
con versión corregida). Corre en cada PR hacia `main`, en cada push a `main` y una vez por
semana. La revisión manual usó la skill `variant-analysis` de Trail of Bits para buscar otras
apariciones del bug del PR #19.

**Resultado de la primera revisión (2026-10-07):** ningún secreto en 176 commits y cero
hallazgos de Semgrep. Se corrigieron: la variante del bug de pertenencia en `POST
/interview-kits` (el puesto y el match del cuerpo ahora deben ser del usuario, y las tareas solo
leen datos de quien las pidió), la validación del PDF (firma y 20 páginas como máximo), el
aviso de «dato, no instrucción» en los prompts que reciben texto de terceros, PyJWT 2.15,
urllib3 2.8, Next.js 15.5.27 y sharp 0.35.5, y se sumó una política de contenido en modo solo
reporte y una política de permisos en la web.

**Alternativas evaluadas:** (a) el servidor MCP de Semgrep — descartado: está archivado desde
octubre de 2025, se usa la CLI; (b) skills de pentesting de terceros sin licencia y con pocas
estrellas — descartadas por falta de respaldo; (c) agregar los escaneos al `ci.yml` que
despliega — descartado: un aviso nuevo de una dependencia no debe frenar un despliegue ni
mezclarse con el pipeline de cobro; (d) escaneo dinámico con ZAP o `nuclei` contra producción —
descartado: solo se prueba en local o en `jobby-test`.

**Pendiente a propósito:** pasar la política de contenido de la web a modo que bloquea (hace
falta repasar la consola con una sesión iniciada y, después, usar nonces); correr la API como
usuario sin privilegios y agregar un `HEALTHCHECK` en el `Dockerfile` (requiere probar la imagen
en Render); `braces` y `postcss-selector-parser` 6.x solo corren al compilar y no tienen
versión corregida compatible.

## Actualización — Decisión 28 (2026-10-12)

**Estado:** Ampliada, con aprobación del autor, que pidió seguir con todo lo que mejore la
seguridad y la calidad mientras pueda defenderse.

La segunda tanda de la revisión encontró un hueco, lo cerró y dejó una protección contra su
regreso.

**Hallazgo (#64).** `PATCH /profiles/documents/{id}/set-primary` delega la verificación de dueño
en la función SQL `set_primary_uploaded_document`, que levanta una excepción (`P0001`) si el
documento no existe, no es un CV o es de otra persona. La API no la atrapaba: respondía 500
`INTERNAL_ERROR` y mandaba un evento a Sentry. No hubo fuga ni cambios, porque la función filtra
por `user_id` y su permiso de ejecución está cerrado a `anon` y `authenticated`; pero la respuesta
no seguía el contrato (un recurso ajeno responde igual que uno inexistente) y cada intento
ensuciaba el registro de errores. Ninguna prueba lo veía porque el simulador devolvía vacío donde
la función real levanta; ahora levanta igual. Solo `P0001` pasa a 404 `DOCUMENT_NOT_FOUND`: un id
mal formado (`22P02`) sigue siendo 400 y cualquier otra falla de la base sigue siendo 500.

**Matriz de acceso (#65).** `tests/unit/test_cross_user_access.py` pide las 12 rutas con
identificador como persona ajena (404, sin datos, sin cambios, sin trabajo encolado y sin gastar
cupo) y como dueña (control, para que el 404 no sea un error de la prueba). Un inventario hecho
con OpenAPI falla si aparece una ruta sin sesión o sin caso: hoy hay 33 operaciones con sesión y
3 públicas a propósito, los dos `/health` y el webhook de LemonSqueezy, que se autentica por
firma. Se comprobó que la matriz detecta el fallo quitando a propósito el filtro de dueño de
cada consulta (puestos, comparaciones, kits, ATS y documentos): cada vez se puso en rojo, salvo
`PATCH /jobs/{id}`, cuyo `UPDATE` vuelve a filtrar por `user_id` y responde 404 igual (defensa en
profundidad). Esa comprobación se hizo primero a mano y después se sumó a
`tests/deliberate_bugs.py` como M12 a M17 (17 de 17 detectadas). Al hacerlo apareció un hueco de
la propia matriz: nadie pedía una comparación por el id del puesto como persona ajena, así que
quitar ese filtro (M14) no ponía nada en rojo. Ahora tiene sus casos.

**Dependencia (#66).** `multidict` 6.7.1 pierde referencias al unir o restar vistas de items
(alerta 82 de Dependabot). Llega por `yarl` a `postgrest`, `storage3` y `supabase`, o sea que
está en cada consulta a la base. Poetry resolvía a la 7.0.0, una versión mayor publicada el
2026-09-26 y sin revisar: se descartó y se fijó la 6.9.1, el parche mínimo, con el techo `<7` en
`pyproject.toml` y un caso en `test_dependency_floor.py`. El techo se sube cuando se revise la 7.

**Verificado en producción (solo metadatos, 2026-10-08).** Ninguna de las seis funciones de
`public` es ejecutable por `anon` ni `authenticated`, como indican las migraciones. Los avisos de
Supabase son dos: `roles` y `role_permissions` tienen RLS sin políticas, a propósito (cerradas a
la clave pública, Decisión 20), y la protección contra contraseñas filtradas está desactivada.
Esta última es un ajuste de Auth que decide el autor: según la documentación de Supabase está
disponible desde el plan Pro, así que cuenta contra el tope de USD 20 por mes.

**Alertas abiertas de Dependabot.** `braces` (alta) no tiene versión corregida y
`postcss-selector-parser` 6.x solo tiene parche en la 7. Ambas llegan por `tailwindcss` 3.4.19
(y `braces` también por `eslint-config-next`), herramientas de compilación y de lint que no se
ejecutan al atender pedidos.

## Actualización — Decisión 28 (2026-10-13)

**Estado:** Ampliada, con aprobación del autor, que pidió cerrar los pendientes de ciberseguridad
que fueran gratuitos y de bajo riesgo: un PR por cambio y ningún merge sin la prueba hecha. Lo que
requiere su aprobación (política de contenido que bloquea, `render.yaml`, workflows, variables,
planes de pago, PDF entregados) queda como propuesta, sin implementar.

**Contenedor sin root (#70).** La imagen de la API corría todo como root y `apt-get` instalaba
paquetes recomendados que no hacen falta. Ahora crea `appuser` (uid 10001), copia el código con
ese dueño y arranca con `USER appuser`; `apt-get` usa `--no-install-recommends`. Se probó en
Docker local con la imagen construida como la construye Render: la web arranca y `/health`
responde 200 con las mismas cabeceras, y el worker con el comando de `render.yaml`
(`celery -A app.tasks:celery_app worker -Q parsing,analysis`) se conecta a un Redis local, registra
la tarea de parseo y queda `ready`; ambos corren con uid 10001 y el archivo temporal del PDF se
escribe en `/tmp`. `tests/unit/test_dockerfile_hardening.py` falla si vuelve a faltar `USER` o el
flag. No se agregó `HEALTHCHECK`: en producción la comprobación es `healthCheckPath: /health` del
servicio web, y la misma imagen la usan los workers, que no tienen puerto HTTP; una sonda dentro
de la imagen los marcaría como no saludables en cualquier plataforma que la respete. El cambio no
toca `render.yaml`, variables ni el workflow.

**Alertas de Dependabot que seguían abiertas (#71).** `postcss-selector-parser` 6.x no tiene
parche: el arreglo (alerta 81, complejidad cuadrática al analizar selectores) está solo en la
7.1.6. Tailwind 3 y `postcss-nested` la piden con `^6`, así que un override de `package.json`
(`postcss-selector-parser@^6: ^7.1.6`) mueve a los dos. Solo corre al compilar. Se verificó que
es compatible: la compilación termina y los dos archivos de CSS que genera son idénticos byte a
byte a los de antes, con typecheck, lint y las 186 pruebas de la web en verde. Una prueba
(`apps/web/lib/security/dependency-floor.test.ts`) falla si el lock vuelve a la 6.x; para
revertir basta quitar la línea del override. `braces` (alerta 80) se descarta: la última versión
publicada es la 3.0.3, la misma que la alerta marca como afectada (`<= 3.0.3`), así que no existe
parche. Llega por Tailwind 3 (`chokidar`, `fast-glob`, `micromatch`) y también por
`eslint-config-next`, de modo que ni cambiar de Tailwind lo quitaría; es una herramienta de
compilación y de lint que no corre al atender pedidos. La alerta queda abierta a la espera de una
versión corregida.

**Escaneo dinámico, solo contra local (#72).** Se corrió nuclei 3.11.1 (imagen oficial
`projectdiscovery/nuclei`, 14 366 plantillas) contra la imagen de la API sin root con
`ENVIRONMENT=production` y valores ficticios, y contra el build de la web servido con `next
start`, los dos en la máquina del autor. No se tocó producción ni `jobby-test`: `SECURITY.md` pide
no correr escáneres contra los servicios en vivo. Hubo dos pasadas por objetivo: la automática por
tecnologías detectadas (`-as`, 20 y 21 plantillas) y la completa (todas las severidades, sin las
etiquetas `dos` ni `fuzz`; unas 14 000 conexiones por objetivo en 2 minutos). Resultado: en la
API, solo la detección de uvicorn; en la web, 10 hallazgos informativos y ninguno de severidad
baja o mayor (detección de Next.js, `robots.txt`, `llms.txt`, el método OPTIONS y cinco cabeceras
ausentes: `Strict-Transport-Security`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Embedder-Policy`,
`Cross-Origin-Resource-Policy` y `X-Permitted-Cross-Domain-Policies`). HSTS falta solo porque en
local se sirve por HTTP: en producción Vercel lo agrega (`max-age=63072000; includeSubDomains;
preload`, comprobado con una petición HEAD). Límite: el escaneo es sin sesión, así que cada ruta de
la API responde 401 y no se ejerció nada autenticado; eso lo cubren la matriz de acceso y la
prueba de errores deliberados.

**Queda como propuesta, sin implementar.** Requiere tu aprobación o cuesta dinero:
- Pasar la política de contenido de la web a modo que bloquea, con nonces (primero repasar la
  consola con una sesión iniciada).
- Cabeceras `Cross-Origin-Opener-Policy: same-origin-allow-popups`, `Cross-Origin-Resource-Policy`
  y `X-Permitted-Cross-Domain-Policies: none` en la web: bajo riesgo, pero hay que probar antes el
  inicio con Google; `Cross-Origin-Embedder-Policy` no, porque rompería las imágenes de terceros
  (`img-src https:`).
- Protección contra contraseñas filtradas de Supabase Auth: es del plan Pro y cuenta contra el
  tope de USD 20 por mes.
- Tamaño y tipo de archivo del bucket `cv-documents`: hoy no tiene `file_size_limit` ni
  `allowed_mime_types` (verificado con una consulta de solo metadatos). Arreglarlo es una
  migración aplicada en producción.
- Largo máximo en los modelos de escritura del perfil (`SkillCreate`, `ExperienceCreate`,
  `EducationCreate`, `LanguageCreate`, `UploadedDocumentCreate`): hoy solo `MasterProfileUpdate`
  los tiene, y esos textos llegan a los prompts.
- Límite de uso para `POST /profiles/documents`, que encola un parseo con IA sin ningún tope
  (los puestos, el ATS, los kits y la optimización sí lo tienen).

Los PDF entregados no se regeneran con esta tanda: se revisaron los documentos que los originan y
ninguno dice algo que estos cambios vuelvan falso (`docs/06` es el único que cita la Decisión 28
y solo habla del workflow de seguridad); `docs/08` no tiene PDF.

## Actualización — Decisión 28 (2026-10-14)

**Estado:** Ampliada, con aprobación del autor, que pidió implementar dos de las propuestas de
la actualización anterior, un PR por cambio y con tests, sin tocar la política de contenido,
COOP/CORP, el bucket, Supabase, las variables de entorno ni los workflows.

**Tope de cargas de documentos (#73).** `POST /profiles/documents` encolaba un parseo con IA
(DeepSeek y los embeddings de OpenAI) por cada registro, sin ningún tope: quien tuviera un archivo
en su carpeta del bucket podía registrarlo en bucle. Ahora usa el mecanismo de `rate_limits.py`
con un contador diario, 10 por día en free y 50 en premium, como constantes
(`DOCUMENT_UPLOADS_PER_DAY_FREE` y `DOCUMENT_UPLOADS_PER_DAY_PREMIUM`). Es un tope contra abuso, no
de producto: una persona normal registra uno o dos documentos por día. Al pasarlo responde 429
`DOCUMENT_UPLOAD_RATE_LIMIT_EXCEEDED` con el límite y la fecha de reinicio, y la web muestra ese
mensaje en el paso 2 del asistente. Tres decisiones de diseño: (a) se cuenta después de validar la
ruta y el perfil, así que un pedido ajeno o inválido no gasta cupo; (b) se cuenta antes de tocar
el slot del CV, así que un pedido bloqueado no borra el que ya estaba; (c) si Redis no responde se
deja pasar y se reporta, porque cargar el CV es el primer paso del onboarding y hoy no depende de
Redis (la tarea cae a modo local sin broker), a diferencia de los topes de puestos, ATS y kits,
que fallan sin él. Cubierto con 7 pruebas nuevas: 10 y 50 por día, el pedido bloqueado que no
registra ni encola, el CV del slot que sigue en su lugar, los pedidos rechazados que no gastan
cupo y el corte de Redis.

**Largo máximo en los modelos de escritura del perfil (#74).** Antes de poner los topes se
verificó por dónde pasan los datos del CV. El parseo (`tasks/parsing.py`) guarda con la clave de
servicio, las skills por `upsert` y el resto en `uploaded_documents.parsed_data`, y no usa ninguno
de los modelos de escritura: una prueba lo fija (un valor cinco veces por encima de los topes se
procesa igual). Lo que sí pasa por los modelos es el asistente web: el paso 3 envía las skills que
extrajo la IA a `POST /profiles/skills` y `POST /profiles/rejected-skills`, y el paso 2 registra el
documento. Por eso los topes van holgados y son los mismos para confirmar y para rechazar una skill:
200 caracteres para nombres, cargos, instituciones, idiomas y skills (como `headline`), 100 para
categoría, nivel y fuente, 500 para el motivo de un rechazo, 5 000 para la descripción de una
experiencia (como `summary`), 1 000 por logro con 50 como máximo, y en los documentos 64 para
`profile_id`, 32 para `type`, 1 024 para `storage_path` (el máximo de nombre de objeto de Supabase
Storage), 512 para el nombre del archivo y 255 para el tipo MIME. También se acotó cada ítem de
`target_industry`, que solo tenía tope de cantidad. Un texto más largo responde 400
`VALIDATION_ERROR` sin escribir nada. Una prueba arma un CV de 20 páginas con valores muy por
encima de lo real (150 skills y 20 experiencias de 4 000 caracteres con 30 logros cada una) y
comprueba que entra completo; otras 8 fallaron a propósito al quitar cuatro de los topes, así que
detectan la falta. 43 pruebas nuevas.

**Riesgo residual y lo que sigue abierto.** La IA no tiene tope en lo que devuelve: un nombre de
skill de más de 200 caracteres (no visto y absurdo para una skill) no se podría confirmar ni
rechazar en el paso 3. Si pasara, el arreglo es recortar en `ai_structurer.py` a la misma
constante. Siguen sin largo máximo los identificadores `job_id` y `match_id` de ATS y kits, y no hay
tope a la cantidad de filas por perfil (skills, experiencias): eso es un límite de uso, no de largo.

**Verificación con la imagen desplegada (#75).** Los pedidos con sesión no se pueden hacer contra
producción sin credenciales, así que #73 y #74 se verificaron con lo más cercano: la imagen
construida del commit desplegado (`7205847`), con las variables de Render
(`ENVIRONMENT=production`, `TASK_EXECUTION_MODE=local`), un Redis real y un Supabase simulado en la
máquina del autor, con tokens firmados con un secreto de prueba. Las 23 comprobaciones salieron
bien: los 11 campos fuera de tope responden 400 `VALIDATION_ERROR` sin escribir nada y sin tocar
Redis; el tope exacto se acepta (incluida una experiencia con 50 logros de 1 000 caracteres); free
registra 10 documentos y el 11.º responde 429 con `limit: 10` y la fecha de reinicio, sin insertar
ni borrar el CV del slot; la clave `rate:document_uploads:<id>:<día>` queda con TTL de hasta 24 h;
otra persona no se ve afectada; los pedidos rechazados no crean claves; y premium llega a 50 y el
51.º da 429. Con Redis detenido o colgado (nombre que no resuelve, dirección que no responde, o
un puerto que acepta y calla) la carga responde 201 con el aviso en el registro, en unos 4 a 5 s
contra 0,3 s con Redis sano: es el tiempo límite por defecto de redis-py 8 (5 s) y una prueba
avisa si una actualización lo cambia. En producción se comprobó que el deploy quedó `live` en
ese commit, `/health` 200, las 7 rutas de escritura con 401 sin sesión y ningún error ni
advertencia en los registros.

**Verificación en vivo del 400 (2026-10-14).** Con la sesión del autor abierta en el panel del
navegador, el formulario del paso 4 del asistente envió un único `POST /profiles/experiences` con
la empresa en 222 caracteres. Producción respondió 400 `VALIDATION_ERROR` con
`string_too_long` en `body.company` y `max_length: 200`, la web mostró «Datos de entrada
inválidos» y no se escribió nada. El 429 se intentó en vivo en un segundo paso, sin registrar
documentos reales: ver el párrafo siguiente.

**Verificación en vivo del tope: el Redis de producción no responde (2026-10-14).** Para probar el
429 sin crear filas ni parseos con IA se enviaron 12 pedidos a `POST /profiles/documents` con un
`file_size` fuera de rango (3 000 000 000) y la sesión del autor: pasan la ruta y el perfil, el
contador sube y la base rechaza la inserción (`22003`, visible en el registro de Render), así que
no se guardó ninguna fila. Los 12 respondieron 500 y ninguno 429. El registro de Render dice por
qué: en cada pedido aparece `No se pudo comprobar el tope de cargas de documentos: Connection
closed by server.`. Redis rechaza la conexión y el tope dejó pasar el pedido, como está diseñado
(deja pasar y reporta), de modo que en producción el tope está desplegado pero no puede actuar
mientras Redis no responda. Como no respondió, el contador no se movió y la cuenta no quedó
bloqueada. La causa probable es ambiental: `REDIS_URL` apunta a Upstash (README y `docs/06`), y su
plan gratuito archiva la base tras 30 días sin actividad (regla operativa de
`docs/operacion/arranque-en-frio.md`). No se pudo confirmar: el valor de `REDIS_URL` es secreto y
no hay ninguna instancia de Key Value en Render. El cliente es el mismo para los demás topes:
puestos (plan free), ATS, kits y optimizador del CV llaman a `increment_rate_limit` sin tolerar la
caída, así que es de esperar un 500 en esos pedidos (no se comprobó en vivo: todos exigen un puesto
o un perfil completo y crearían datos). La redis-py es la misma 8.0.1 desde el 2026-06-28, así que
no es un cambio de librería. Corregirlo es una acción del autor en Upstash (restaurar la base o
crear otra) y, si cambia la URL, actualizar `REDIS_URL` en Render; no requiere código. Con Redis
de vuelta se repite la misma prueba de 11 pedidos y el 11.º debe dar 429. Costo de la prueba: hasta
24 eventos en Sentry (12 del aviso de Redis y 12 del rechazo de la base).

**Verificación en vivo del 429, ya con Redis (2026-10-14).** Después del deploy manual del autor de
las 04:40 UTC, el registro de Render dejó de mostrar el aviso de Redis caído y se repitió la misma
secuencia con la sesión del autor y el `file_size` fuera de rango. Los pedidos 1 a 10 respondieron
500 (la base rechaza la inserción con `22003`, sin crear filas) y el 11.º respondió **429
`DOCUMENT_UPLOAD_RATE_LIMIT_EXCEEDED`** con `limit: 10` y `reset_at: 2026-10-15T00:00:00+00:00`. La
base sigue con un único documento (el CV, en `done`) y ninguna fila con `file_size` fuera de rango.
El tope queda verificado en producción. Mientras no pase la medianoche UTC, la cuenta del autor no
puede registrar documentos nuevos (el reintento de parseo con `set-primary` no pasa por el tope).
Con Redis de vuelta, los demás topes (puestos, ATS, kits y optimizador del CV) también quedan en
condiciones de responder en vez de dar 500.

---

## Decisión 29 — El porcentaje del perfil exige datos útiles y el puesto tiene que ser de tu área

**Estado:** Pedido por el autor (2026-10-14). La mecánica es lo pedido; los valores numéricos
(piso 0,15, umbral 0,4, cuatro menciones, mínimo de cinco palabras en la bio) son una propuesta
del cambio, **sin aprobar**, y se calibran con la prueba de todo el pasillo en producción.

**Problema (medido, no supuesto).** (1) `compute_completeness` devolvía el número y nadie lo
guardaba: en producción hay 4 perfiles, el máximo guardado es 38 y ninguno llega al 60 que pide el
análisis de puestos, así que nadie puede analizar un puesto aunque su perfil esté completo.
(2) Contaba que hubiera algo: «asdf» en el headline sumaba lo mismo que un cargo real. (3) Un CV
de sistemas contra un puesto de chef daba 52 puntos, y 80 si la IA no extraía ninguna skill del
puesto, porque cuatro de los seis componentes (seniority, idiomas, empresa y blandas) valen
0,75 a 0,85 apenas el puesto no pide algo puntual, sea cual sea el rubro.

**Elegido.**
- El porcentaje se calcula en Python (`services/profile_completeness.py`, sin migración) y se
  guarda en cada cambio del perfil (`refresh_completeness`). La función SQL queda sin uso. Un fallo
  del recálculo no tumba la escritura ni marca el CV como fallido.
- Mismos pesos (suman 100), pero cada criterio exige un dato útil (`services/text_quality.py`,
  reglas deterministas, sin IA y sin costo): headline y rol que no sean relleno («asdf», «N/A»,
  «profesional responsable»), bio con al menos 5 palabras con contenido y sin repetirse ni copiar
  el headline, seniority y modalidad dentro de los valores que entiende el motor, nombres reales
  en experiencias, skills (3 confirmadas y distintas), estudios e idiomas, URL de LinkedIn que sea
  un perfil. El CV y el documento de LinkedIn dan sus puntos completos solo si dejaron al menos 3
  skills con nombre válido, la mitad si dejaron algo, y nada si terminaron en `done` sin dejar
  datos.
- El MatchScore se multiplica por una **relevancia** (`s_relevance.py`): sin ninguna skill del
  puesto en común queda en 0,15 de su valor; con el 40 % de las skills pedidas ya es del área y
  no cambia. Si el puesto no lista skills, cuenta cuántas de las skills de la persona nombra su
  texto. El potencial no se atenúa (es «si cerraras la brecha»).

**Medido con el motor real y datos de prueba** (un perfil senior de sistemas con cinco skills).
Chef contra CV de sistemas: 52 → 8; sin skills extraídas: 80 → 12; puesto de backend que
coincide: 89 → 89.

**Límites que quedan abiertos (no se arreglan acá).**
- El asistente (paso 4) guarda la experiencia con `description: null`, la educación solo como
  `institution` y los idiomas con nivel fijo, así que las reglas no exigen descripción ni carrera:
  hacerlo volvería inalcanzable el 100 % que pide el kit de entrevista. Hasta que la web los
  pida, el motor compara estudios con un componente casi neutro y las blandas sin texto.
- El parser deja `degree_level` en texto libre y el motor lo busca en `phd/master/bachelor/...`:
  casi siempre cae al valor por defecto.
- El potencial de un puesto de otra área sigue siendo alto (87 en el caso del chef).
- Los porcentajes ya guardados se corrigen en el próximo cambio del perfil de cada persona; no
  hay migración de datos.

---

## Actualización — Decisión 29 (2026-10-14)

**Verificación en vivo y corrección de la relevancia.** Con la cuenta del autor en producción
(perfil en 82 % tras guardar el paso 1 y completar el paso 4; el porcentaje pasó de 38 a 58 y a 82 sin
tocar nada más) se analizaron dos puestos de prueba. Un puesto de chef dio **3/100** con la
relevancia en su piso (antes habría rondado 50): la compuerta funciona. Un puesto de desarrollo
full stack junior, del propio rubro del autor, dio **21/100**: el perfil tiene 4 filas de `skills`,
solo 1 de las 6 skills pedidas coincide literal, y la relevancia (0,50) partió a la mitad un puntaje
de 42. La bio y el headline nombran las 6.

**Corregido.** La evidencia de relevancia pasa a ser la mayor entre las filas de `skills` y las
skills pedidas que el perfil nombra (headline, rol, bio, cargos, descripciones y logros). El piso, el
umbral del 40 % y el potencial no cambian. Un puesto de otra área sigue en el piso aunque la bio
nombre tecnologías.

**Hallado y sin corregir en este cambio.** El idioma pedido llega de la IA como un texto entero
(`"Inglés intermedio (B1/B2)"`) y el motor lo compara literal con el nombre del idioma de la
persona («Inglés»): el componente de idiomas dio 0 con el idioma cargado. Pre-existente; propuesto
como cambio aparte. La web tampoco tiene dónde cargar la URL de LinkedIn ni un documento de
LinkedIn, así que con la web el máximo es 82 % y el kit de entrevista (que pide 100 %) no se puede
generar.

---

## Decisión 30 — Posicionamiento orgánico de la web, sin costo

**Estado:** Pedido por el autor (2026-10-15). Solo cubre lo gratuito y técnico; el dominio propio
es una propuesta **sin aprobar** y queda fuera de este cambio.

**Relevamiento (medido en producción, no supuesto).** La web ya servía HTML prerenderizado, título,
descripción, Open Graph, `sitemap.xml` y un `robots.txt` que deja pasar a los buscadores y bloquea
solo las rutas privadas. Faltaban: URL canónica, datos estructurados, títulos propios en
`/pricing`, `/terms` y `/privacy` (los tres heredaban el título de la home), y un `lastModified` del
sitemap que dijera la verdad (valía la fecha de cada build para todas las URLs). Una búsqueda de
`site:jobbyweb.vercel.app` no devolvió páginas del sitio; no prueba que no esté indexado, pero no
hay verificación en Search Console que lo confirme.

**Elegido.**
- La URL pública vive en un solo lugar (`lib/seo/site.ts`) y la usan `metadataBase`, Open Graph,
  el sitemap y los datos estructurados. `public/robots.txt` es estático y se edita a mano.
- Canónica propia en la home (`/`), `/terms` y `/privacy`. `/pricing` no la lleva a propósito:
  sus rutas hijas (`success`, `cancel`, `unavailable`) la heredarían y apuntarían a una página que
  no son.
- JSON-LD `WebSite` (con `alternateName` «Jobby web») y `WebApplication` en la home. No declara
  valoraciones ni reseñas: no existen.
- Título y descripción propios en `/pricing`, `/terms` y `/privacy`, vía un `layout.tsx` por ruta
  (las páginas son de cliente y no pueden exportar metadatos).
- El sitemap deja de publicar `lastModified`.
- La descripción de la home nombra el match score y la compatibilidad ATS.

**Límites que quedan abiertos.**
- Nadie garantiza una posición: depende de la indexación, de los enlaces entrantes y de la
  competencia del nombre («jobby» es también una plataforma italiana, paquetes de código y una
  palabra de jerga). El objetivo realista son búsquedas como «jobby web», «jobby cv» o
  «jobby match score».
- Falta que el autor dé de alta el sitio en Google Search Console y Bing Webmaster y envíe el
  sitemap; la verificación por etiqueta se agrega con el código que entregue cada servicio.
- `robots.txt` y el middleware bloquean a los rastreadores de IA (GPTBot, OAI-SearchBot,
  PerplexityBot y otros): el sitio no aparecerá en las respuestas de esos buscadores. Es una
  decisión previa y no se toca acá.
- El subdominio `vercel.app` no acumula autoridad propia. Un dominio propio obliga a tocar las URLs
  de Supabase Auth, LemonSqueezy y CORS, y a redirigir con 301; va en un cambio aparte.

---

## Actualización — Decisión 30 (2026-10-19): título de la home y organización

**Estado:** Pedido por el autor, con aprobación explícita.

**Medición (Search Console y Google, 2026-10-18).** La home ya está indexada (último rastreo el
2026-10-15, canónica declarada igual a la elegida por Google) y el sitemap se leyó sin errores
con 4 páginas descubiertas. Con Google en español, el sitio aparece primero en «jobby match
score» y en «jobbyweb», pero no en la primera página de «jobby web» ni de «jobby cv», donde
compiten sitios con la marca en el dominio (`jobby.lat`, `jobby.com.do`, `jobby.tn`). El
título de la home no nombraba ni el CV, ni el ATS, ni el match score.

**Elegido.**
- Título de la home: «Jobby — Match score y ATS: compará tu CV con el puesto» (54 caracteres, por
  debajo de los ~60 que Google suele mostrar completos). Dice qué hace el producto sin repetir
  palabras. El lema («Sabé cuánto matcheás antes de aplicar») sigue en el hero y en el título de
  Open Graph y Twitter, que son las tarjetas al compartir el enlace, no lo que lee Google.
- Nodo JSON-LD `Organization` en la home, con nombre, URL y `sameAs`. `sameAs` vive en
  `lib/seo/site.ts` (`SITE_SAME_AS`) y hoy tiene un solo valor: el repositorio público de GitHub.
- No se declara logo, contacto, fundadores ni LinkedIn: no hay logo propio publicado ni un perfil
  de LinkedIn del proyecto, y un perfil personal sería un dato personal que el sitio no debe
  publicar. Cuando exista un perfil del proyecto se agrega a `SITE_SAME_AS`.

**Límites.** No garantiza posición: el efecto de un título es lento y el peso grande lo siguen
teniendo los enlaces entrantes y el dominio. El dominio propio y la decisión sobre los
rastreadores de IA siguen abiertos, como en la Decisión 30.

---

## Actualización — Decisión 14 (2026-10-16)

**Estado:** Ampliada, con aprobación del autor.

**Medición.** La consulta periódica de la actualización del 2026-09-25 no cumplía lo
prometido: `keep-alive.yml` corrió el 2026-10-14 y el 2026-10-15 a las 19:40, 22:40, 00:55,
03:22, 15:24, 19:16 y 22:24 UTC, es decir, una vez cada ~3 horas, con huecos de hasta ~4 horas
dentro del horario (por ejemplo, ninguna corrida entre las 11:00 y las 15:24 UTC). La API Free
dormía buena parte del día y el primer pedido de cada período esperaba ~40 s: es la causa de
fondo de las demoras que se vieron en las pantallas del asistente. La limitación estaba prevista (GitHub puede demorar o saltear ejecuciones), pero
su peso no estaba medido.

**Elegido.** Los pedidos a `/health` pasan a hacerse desde la base de datos con `pg_cron` y
`pg_net` (migración 029): `*/10 11-23 * * *` y `*/10 0-2 * * *` en UTC, es decir, de 8 a 24 hora
de Buenos Aires, igual que antes. Un tercer trabajo borra a diario lo anterior a 7 días de
`cron.job_run_details`. Probado en `jobby-test` antes de aplicarlo (ejecuciones a los :00 y
`200` de `/health`) y aplicado en producción el 2026-10-16; el primer disparo real fue a las
02:00:00 UTC y devolvió `200`. La migración 030 dejó `pg_net` en el esquema `extensions`: el
Security Advisor avisó `extension_in_public` tras la 029 y el aviso desapareció. El workflow de
GitHub no se toca y queda como respaldo. Consumo y costo sin cambios: ~16 h por día, unas 500 de las 750 horas
gratis de Render, USD 0.

**Alternativas evaluadas.** (a) UptimeRobot cada 5 minutos: mantiene la API despierta las 24 h
(744 de 750 horas) y deja casi sin margen a los otros servicios del workspace; (b) cron de
Render: mínimo USD 1 por mes; (c) Render Starter (USD 7/mes): único arreglo total, sigue como
opción si el proyecto necesita cero espera de forma permanente.

**Escrituras durante un deploy.** Mientras Render cambia de instancia en un deploy, el
primer PATCH a `/profiles/me` recibió un 502 y no se reintentó (solo se reintentaban los GET).
`apiClient` acepta ahora `idempotent: true` y, con esa marca, reintenta la escritura con la
misma escalera de esperas. Se marcaron cuatro pedidos que dejan el mismo resultado al
repetirse: PATCH del perfil, POST de una skill (actualiza la fila ya guardada), PATCH de un
puesto y PATCH de la calificación. Ningún POST que crea filas ni ningún DELETE lleva la marca.

**Límites.** Si Supabase pausa el proyecto por inactividad, el ping se detiene hasta que se lo
restaure; no está verificado que la propia actividad del cron evite esa pausa. Revertir:
`select cron.unschedule(jobname) from cron.job;` y `drop extension pg_cron; drop extension
pg_net;`.

## Actualización — Decisión 29 (2026-10-14): idiomas del puesto

**Estado:** Corrección pedida por el autor tras medir en producción con una cuenta real. Las
reglas marcadas como «propuesta» no fueron aprobadas y se pueden cambiar.

**Problema (medido).** La IA devuelve cada idioma del puesto como un único texto, por ejemplo
«Inglés intermedio (B1/B2)», y `s_languages.py` lo buscaba entero contra el nombre del idioma
del perfil («Inglés», nivel `professional`). No coincidía nunca y el componente daba 0 (10 % del
MatchScore) aunque la persona tuviera el idioma. Pasaba igual con «Inglés básico» y con «English».
Es lo que la actualización anterior dejó como «hallado y sin corregir».

**Elegido.** Separar nombre y nivel del texto, sin IA y sin tocar los pesos:
- El nombre se reconoce dentro del texto, sin acentos ni mayúsculas, con las equivalencias es/en
  de inglés, español, portugués, francés, alemán e italiano; el nombre del perfil se compara con
  las mismas. Un idioma fuera de la tabla coincide por su propio nombre («Chino intermedio» con
  «Chino»).
- El nivel se lee por palabras (básico, intermedio, avanzado, nativo, bilingüe y sus formas en
  inglés) y por códigos del MCER; sin nivel, intermedio, como antes.
- Propuesta: el MCER se mapea A1/A2 → básico, B1/B2 → intermedio, C1 → avanzado y C2 → nativo;
  un rango («B2/C1») pide su nivel más bajo; un texto con dos idiomas («Inglés y portugués») pide
  los dos, con el nivel que nombra el texto.

**Límites que quedan abiertos.** El nivel del perfil se sigue leyendo solo con las palabras en
inglés de `LANGUAGE_LEVEL` y sin códigos MCER: un «Avanzado» o «C1» cargado a mano cae en
intermedio. «Fluido» o «fluent» tampoco se reconoce como nivel en el texto del puesto.

## Actualización — Decisión 29 (2026-10-16): el paso 4 edita lo guardado

**Estado:** Corrección pedida por el autor tras el recorrido de punta a punta del
2026-10-15, donde quedó anotado que el paso 4 no precargaba y agregaba filas al repetirse.

**Problema (medido en el código y en vivo).** El paso 4 abría siempre vacío y cada «Guardar y
finalizar» enviaba un `POST` por cada campo completo. Volver a pasar por el paso agregaba otra
experiencia, otro estudio y otro idioma iguales, y no había forma de ver ni corregir lo que
ya estaba cargado.

**Elegido.**
- `GET /profiles/details` devuelve las experiencias, estudios e idiomas cargados a mano, de la
  más nueva a la más vieja, sin vectores ni filas de otra persona.
- `PATCH /profiles/experiences/{id}`, `/educations/{id}` y `/languages/{id}` hacen un cambio
  parcial: solo tocan los campos enviados y un `null` no vacía una columna obligatoria. Una fila
  de otra persona responde 404 igual que una inexistente (casos nuevos en la matriz de
  `test_cross_user_access.py`). Después de cada cambio se recalcula el porcentaje del perfil.
- El paso 4 abre con la fila más nueva de cada tipo. Al guardar, edita esa fila si el valor
  cambió, no hace ningún pedido si no cambió y crea solo cuando no hay ninguna. Si un pedido
  falla y otro salió bien, lo que salió bien se recuerda: reintentar no lo repite.
- Mientras carga lo guardado se puede escribir (lo tocado no se pisa) y el guardado se habilita
  al llegar. Si la carga falla, no se guarda hasta reintentar: guardar sin saber qué hay
  duplicaría datos.
- Los `PATCH` del paso llevan `idempotent: true`, así que se reintentan ante un 502 de deploy
  (ver la actualización de la Decisión 14 del 2026-10-16); los `POST` que crean, no.

**Límites que quedan abiertos.**
- Vaciar un campo no borra lo guardado: la API no tiene borrado de estas filas.
- Las filas duplicadas que ya existen (por ejemplo en las cuentas de prueba) no se unifican.
- El paso muestra y edita solo la más nueva de cada tipo; si hay más, siguen en el perfil.
- El nivel del idioma sigue fijo en `professional` al crearlo y el paso no pide carrera ni
  descripción (ver los límites de la Decisión 29).

## Actualización — Decisión 30 (2026-10-19): rastreadores de búsqueda de IA

**Estado:** Decidido por el autor. Cierra el límite que la Decisión 30 dejó abierto.

**Antes.** `robots.txt` bloqueaba en todo el sitio a 14 rastreadores de IA, incluidos los de
búsqueda (`OAI-SearchBot`, `PerplexityBot`) y el que actúa a pedido de una persona
(`ChatGPT-User`): el sitio no podía aparecer en ChatGPT search ni en Perplexity. Una precisión a
la Decisión 30: el middleware solo responde 403 a esos rastreadores en las **rutas privadas**
(`/dashboard`, `/profile`, `/jobs`, `/ats`, `/reality-gap`, `/interview-kits`, `/wizard`,
`/billing`, `/admin`, `/api`); las páginas públicas las bloqueaba únicamente `robots.txt`.

**Elegido.**
- Se quitan de `robots.txt` los grupos de `OAI-SearchBot`, `PerplexityBot` y `ChatGPT-User`. Sin
  grupo propio siguen las reglas de `*`: leen las páginas públicas y no las rutas privadas.
- Según la documentación oficial (OpenAI y Perplexity, consultada el 2026-10-19), `OAI-SearchBot` y
  `PerplexityBot` son de búsqueda y no entrenan modelos; `ChatGPT-User` visita páginas cuando una
  persona lo pide y OpenAI avisa que ahí `robots.txt` puede no aplicar.
- Siguen bloqueados en todo el sitio los de entrenamiento y extracción: `GPTBot`, `ClaudeBot`,
  `Claude-User`, `Google-Extended`, `Amazonbot`, `Bytespider`, `CCBot`, `Applebot-Extended`,
  `Meta-ExternalAgent`, `YouBot` y `Anthropic-ai`.
- El middleware no cambia: sigue siendo el respaldo que corta a los tres en las rutas privadas.
- `llms.txt` decía que no se autorizaba a resumir ni indexar nada; se reescribe para que no
  contradiga a `robots.txt`: los tres pueden leer y citar las páginas públicas con enlace, y todo lo
  demás (entrenamiento, extracción, rutas privadas, contenido de usuarios) sigue prohibido.
- Tres archivos de tests fijan la política: `lib/seo/robots.test.ts` (grupos de `robots.txt` y texto
  de `llms.txt`) y `src/middleware.test.ts` (403 en cada ruta privada para los tres y paso libre en
  las públicas).

**Límites.**
- Que el sitio pueda ser leído no garantiza que aparezca en ChatGPT search o en Perplexity.
- Que esos rastreadores no entrenan es lo que declaran sus empresas; el sitio no lo verifica. Si
  alguno cambia de política, el bloqueo vuelve con un grupo `Disallow: /`.
- No se abrieron `Claude-User` ni `Perplexity-User`, que no estaban en lo aprobado; abrirlos queda
  como una propuesta aparte.

---

## Decisión 31 — LinkedIn en el perfil: el enlace y el PDF

**Estado:** Pedido por el autor (2026-10-16): «arreglá lo de LinkedIn sin UI». Es el hallazgo que
dejó la Decisión 29: sin dónde cargar la URL ni el documento de LinkedIn, el 18 % del porcentaje
(6 de la URL y 12 del documento) era inalcanzable por la web y el kit de entrevista, que pide
100 %, no se podía generar. El **reparto de pantallas y la regla de lectura** son propuesta del
cambio y no fueron aprobados por separado.

**Elegido.**
- Una tarjeta «LinkedIn» en «Mi perfil» (`/profile`), separada del asistente para no tocar el
  flujo del CV. Tiene el enlace al perfil y la subida del PDF que LinkedIn exporta («Guardar en
  PDF»). `GET /profiles/linkedin` devuelve el enlace, el estado del PDF (sin su contenido) y
  cuántas skills ya guardadas nombra.
- El enlace se valida igual que la API (`linkedin.com/in/<usuario>`) y se guarda con `PATCH
  /profiles/me`. Dejarlo vacío lo quita.
- El PDF se sube al mismo bucket privado y se registra como `uploaded_documents.type =
  'linkedin'`. Un PDF nuevo reemplaza al anterior; no ocupa el lugar del CV ni es CV primario.
- La tarea de lectura distingue el tipo. Con `linkedin` usa el mismo lector, pero **solo marca
  `skills.in_linkedin`** en las skills que la persona ya tiene (nombre sin acentos ni mayúsculas,
  sin mirar la categoría). No toca `in_cv`, no agrega skills y no calcula vectores. Un CV nuevo
  conserva esa marca.
- El documento de LinkedIn da sus 12 puntos según las skills que **LinkedIn** nombró (3 o más:
  completos; alguna o datos del perfil: la mitad; nada: cero). Antes, sin interfaz, se medía con
  las skills del CV. El Reality Gap ya leía `in_linkedin`, que nada marcaba.

**Por qué no agrega skills.** El motor de comparación usa todas las skills guardadas, confirmadas
o no, y un perfil de LinkedIn suele traer aptitudes que nadie revisó: agregarlas habría movido
los MatchScore sin que la persona las confirmara. Tampoco se pidió leer LinkedIn por la web: sin
sesión devuelve un muro de registro y no se usa scraping del perfil propio.

**Límites que quedan abiertos.**
- Una skill que figura solo en LinkedIn no se agrega: hay que cargarla y confirmarla a mano.
- Borrar el PDF no apaga `in_linkedin` (igual que borrar un CV no apaga `in_cv`); subir otro
  vuelve a marcar, pero no desmarca.
- La coincidencia es literal por nombre: «API REST» y «REST APIs» no coinciden.
- Cada PDF cuenta en el tope diario de cargas (10) y en el costo de lectura con IA.
- El asistente sigue sin pedir LinkedIn; solo está en «Mi perfil».

## Actualización — Decisión 31 (2026-10-16): alias y traducciones

**Estado:** Pedido por el autor tras probar en vivo con su PDF, donde LinkedIn nombró «React.js»
y «API Integrations» y el perfil tenía «React» e «Integración de APIs»: no coincidían por
compararse el texto literal. Pedido: «que reconozca alias y traducciones, pero que sea lógico».
La lista de equivalencias es propuesta del cambio y no fue aprobada entrada por entrada.

**Elegido.** `services/api/app/services/skill_names.py` decide cuándo dos nombres son la misma
skill, con reglas fijas, sin IA y sin costo. Dos nombres coinciden si quedan iguales después de:
1. Quitar acentos y mayúsculas e ignorar la puntuación (salvo `.`, `+` y `#`: «Node.js», «C++»).
2. Llevar un producto escrito de varias maneras a una sola («Power BI», «Microsoft Power BI» y
   «PowerBI»; «React», «React.js» y «ReactJS», solo para los frameworks de la lista).
3. Llevar las palabras genéricas a un inglés único y en singular («integración», «integraciones» e
   «integrations»). Los nombres que la tabla no conoce solo coinciden consigo mismos.
4. Descartar conectores («de», «y», «of») y palabras que no cambian de qué skill se habla
   («skills», «habilidades», «metodologías», «herramientas»).
5. Ignorar el orden: «API REST» y «REST API».

**Qué no se iguala (lo fijan las pruebas).** Java y JavaScript, C, C++ y C#, React y React Native,
Angular y AngularJS, SQL con PostgreSQL, MySQL y NoSQL, Git y GitHub, Project y Product
Management, Data Science y Data Analysis, Machine y Deep Learning, Seguridad y Ciberseguridad,
Frontend y Backend, Power BI y Power Automate. Cada alias de la tabla tiene que ser la misma
skill, no una parecida o relacionada; ante la duda no se agrega.

**Alternativas descartadas.** Distancia de edición: iguala «Java» con «Lava». Similitud por
vectores: cuesta un vector por nombre, no explica por qué dos nombres coinciden y habría que
fijar un umbral que se equivoca en los dos sentidos.

**Dónde se aplica.** Solo al marcado de `skills.in_linkedin` por el PDF de LinkedIn.

**Dónde NO se aplica (propuesta sin aprobar).** El MatchScore (`s_skills`: coincidencia literal
y respaldo semántico con peso 0,6), el reporte ATS (`keyword_matcher`), la deduplicación al
leer un CV y `POST /profiles/skills`. Aplicarlo ahí convertiría coincidencias semánticas en
literales («API REST» contra «REST APIs») y movería los puntajes de personas reales: conviene
hacerlo como cambio aparte, midiendo antes y después con los mismos perfiles y puestos.

**Límites que quedan abiertos.** La tabla es finita: un alias nuevo se agrega a `_GROUPS` y su
par negativo a `test_skill_names.py`. Un PDF ya subido no se vuelve a leer solo: hay que subirlo
otra vez para que marque las coincidencias nuevas.

## Actualización — Decisión 31 (2026-10-18): alias y traducciones en el MatchScore y el ATS

**Estado:** Opción A aprobada por el autor («A, dale»), que la propuesta del 2026-10-16 había
dejado sin aprobar. Cubre las skills del MatchScore, el stack tecnológico de la compatibilidad
con la empresa y las palabras clave del ATS. No incluye el límite de palabra del ATS (opción B).

**Elegido.**
- `match_engine/common.py::skill_key` compara por la forma común de `canonical_skill_key`; si el
  nombre solo tiene relleno, por su texto en minúsculas, como antes. La usan `s_skills` (skills
  pedidas por el puesto) y `s_company` (stack tecnológico).
- ATS (`analyze_keywords`): una palabra clave es «literal» si lo era por la regla de siempre
  («contenida en» un término del CV) o si su forma común coincide con la de un término. Lo que
  coincide así ya no pide vectores, lo que abarata el reporte.
- Cada skill pedida cuenta por separado. Con alias es normal que un puesto liste «REST API» y
  «API REST»: las dos coinciden y no se divide por la cantidad de nombres distintos.
- Se arregló `missing_skills`: tomaba las últimas N skills del puesto en vez de las que faltan, y
  figuraba «git» (que la persona tiene) en lugar de «api rest». Ahora son las que no coincidieron
  ni literal ni semánticamente, en el orden del puesto. `semantic_match_indexes` devuelve qué
  skills del puesto se parecieron a algo del perfil (`count_semantic_matches` sigue igual).
- Un puesto cuyas skills pedidas están todas en blanco ya no divide por cero: queda en el puntaje
  neutro de un puesto sin skills.

**El puntaje solo puede subir.** Todo lo que coincidía literal sigue coincidiendo, y cada alias
convierte una coincidencia semántica (0,6) o una falta en una literal (1,0). Una prueba lo exige
comparando contra la regla anterior en 30 combinaciones de perfil y puesto.

**Medición antes y después con producción.** Las 6 comparaciones guardadas (2 perfiles, 6
puestos, ninguna con coincidencias semánticas en las skills): el cálculo con la regla anterior
reproduce exactamente los 6 puntajes guardados, y con alias cambia **una**: el puesto «Desarrollador/a
Full Stack Jr» del perfil con CV de Canva pasa de 65 a 71 (pide «API REST», el perfil tiene «REST
APIs»; skills de 5 de 6 a 6 de 6). Las otras cinco no cambian (el puesto de datos pide «Excel» y el
perfil tiene «Office (Word, Excel, PowerPoint)»; el del chef no tiene nada en común). ATS, con las
18 skills y tecnologías de esos puestos como palabras clave y el CV real: 1 de 18 pasa a literal
(«API REST» por «REST APIs»). Los puntajes guardados **no se recalculan**: cambian cuando la
persona vuelve a analizar el puesto.

**Hallazgos de la medición, sin tocar (propuestas sin aprobar).**
- El stack tecnológico solo compara contra skills con `category = "technical"`, pero el lector de
  CV no fija las categorías (pide «minúsculas cuando se pueda»): un CV leído hoy trae
  «programming», «frontend», «api», «devops»… y el componente da 0 aunque la persona tenga las 10
  tecnologías del puesto. En el puesto de la medición, compararlo contra todas las skills lo
  llevaría a 1,0 (el componente de empresa pesa 15 % y el stack la mitad de ese: unos +7,5 puntos).
  Cambia puntajes de muchas personas, por eso queda aparte.
- ATS: la regla «contenida en» no respeta límites de palabra: «Java» cuenta dentro de
  «JavaScript», «Go» dentro de «Google Sheets», «R» dentro de «React» y «Angular» dentro de
  «AngularJS». Infla el puntaje; corregirlo lo baja en esos casos (opción B).
- Los nombres compuestos («Office (Word, Excel, PowerPoint)», «Agile / Scrum») no se parten en
  componentes, así que «Excel» no coincide con el primero.

---

## Decisión 32 — Guías públicas para llegar a quien busca sin conocer Jobby

**Estado:** Pedido por el autor (2026-10-19, punto 4 de la lista de posicionamiento). El texto es un
borrador redactado con asistencia de IA: **el autor lo revisa y lo hace suyo antes de publicarlo**.

**Relevamiento.** Google indexaba 4 URLs (home, precios, términos y privacidad); todo lo demás
está detrás del login. Una persona que busca «cómo saber si mi CV pasa un ATS» no tenía a dónde
llegar, y la home ya sale primera en «jobby match score» y «jobbyweb» pero no en búsquedas más
amplias.

**Elegido.**
- Una sección `/guias` con cuatro guías: `que-es-un-ats`, `que-es-el-match-score`,
  `como-adaptar-tu-cv-a-una-oferta` y `palabras-clave-del-cv`. Son Server Components con
  `generateStaticParams`: el build las genera como HTML estático (el texto está en la respuesta, no
  depende de JavaScript) y un slug que no existe responde 404.
- Ampliación (2026-10-19, siguiente paso del plan de posicionamiento): cuatro guías más, cada una
  con una búsqueda objetivo: `cv-compatible-con-ats` («cv compatible con ats»),
  `analizar-cv-con-ia` («analizar cv con ia»), `optimizar-cv-con-ia` («optimizar cv con ia») y
  `habilidades-para-poner-en-el-cv` («habilidades para poner en el cv»). Cada una de las cuatro
  guías anteriores enlaza a una nueva. Siguen siendo borradores con IA que el autor revisa antes
  de mergear. Lo que dicen del CV Optimizer («Sin respaldo en tu CV», puntaje ATS antes y después,
  PDF de una columna) se contrastó con `cv_optimizer.py` y `optimized-cv-result.tsx`; los topes del
  plan salen de `facts.ts` y `guides.test.ts` los compara con `rate_limits.py`.
- El contenido vive en `lib/guides/guides.ts` como datos tipados, no dentro de JSX; las cifras del
  producto viven aparte, en `lib/guides/facts.ts`.
- Solo en español: es el idioma de las búsquedas que se quieren captar. En el pie de la home el
  enlace dice «Guías» y, en inglés, «Guides (in Spanish)».
- Cada página lleva canónica propia, título de hasta 60 caracteres y su tarjeta para compartir
  (`lib/seo/share.ts`; las tarjetas de una página reemplazan a las del layout raíz, no se mezclan).
  Las guías y el índice entran al sitemap y se enlazan desde el pie de la home y entre sí, para que
  no queden huérfanas.
- No se declaran datos estructurados `Article`: no hay autor ni fecha que el sitio pueda respaldar.

**Cómo se evita publicar algo falso.**
- Toda cifra del producto sale de `facts.ts` y `lib/guides/guides.test.ts` la compara con el código
  del backend: los seis pesos del match score (`formula.py`), el umbral de brecha, la fracción de
  habilidades que da relevancia plena (`s_relevance.py`), los descuentos de formato del ATS
  (`format_checker.py`) y lo que suma cada palabra clave (`scoring.py`). Si la fórmula cambia y la
  guía no, el test falla. Se comprobó que detecta un peso cambiado, un porcentaje inventado y una
  promesa de resultado.
- Las guías no citan estadísticas de mercado ni prometen entrevistas o contrataciones (un test
  rechaza porcentajes que no sean del producto y palabras como «garantizamos»).
- Lo que el producto hace hoy y la guía no afirma: la guía de palabras clave **no** dice que el ATS
  distinga «Java» de «JavaScript», porque la regla «contenida en» del ATS no respeta límites de
  palabra (hallazgo abierto de la Decisión 31). El consejo de no mezclarlos va como consejo de
  redacción para la persona, no como comportamiento del sistema.

**Límites.**
- No garantiza posición ni tráfico: son búsquedas muy competidas y el sitio es nuevo. El efecto, si
  llega, es lento y se mide en Search Console.
- El contenido describe criterios de Jobby y consejos generales; cada empresa usa su propio sistema
  de selección. El pie de cada guía lo aclara.
- Hay que revisarlo y mantenerlo: si cambia la fórmula, `facts.ts` y el texto cambian juntos.

---

## Actualización — Decisión 30 (2026-10-19): «Jobby web» y «analizador de CV» en lo que Google lee

**Estado:** Pedido por el autor (objetivo: aparecer en la mayor cantidad de búsquedas y lo más
arriba posible, con el dominio `jobbyweb.vercel.app`). El texto exacto se mostró antes de
implementarlo; la aprobación final es la revisión del PR, que no se mergea sin ella.

**Medición.** El sitio sale primero en «jobbyweb» porque esa palabra única coincide con el dominio
y nadie más la usa. En «jobby web» no aparece en la primera página: es una búsqueda de dos palabras
que se decide por el contenido, y la home no decía «web» en el título, la descripción ni el texto
visible (el h1 es el lema), mientras que otros sitios con «jobby» en el nombre sí la tienen.

**Elegido.**
- Título de la home: «Jobby web — Analizador de CV: match score y ATS con IA» (54 caracteres) y
  descripción con «Jobby web». Reemplaza al título de la actualización anterior, que Google todavía
  no había vuelto a leer.
- Pie de la home (visible, en español e inglés): «Jobby web: analizador de CV con IA para entender
  mejor cada postulación antes de aplicar.» Es el único texto visible que se toca: el h1 y el
  diseño de la v2 quedan como estaban.
- `/pricing`: título «Planes y precios del analizador de CV — Jobby web» y descripción con las
  mismas palabras.
- Tests: la home y precios nombran «Jobby web» y «analizador de CV»; los títulos no pasan de 60
  caracteres ni las descripciones de 160; el pie contiene la frase.

**Límites.** No garantiza posición: Google puede reescribir el título y el efecto es lento. «Analizador
de CV» es una búsqueda genérica que dominan sitios con años de enlaces; lo realista es ganar las
búsquedas con «Jobby» más un término. Siguen abiertos los enlaces entrantes, más guías para
búsquedas largas y el dominio propio.

---

## Decisión 33 — El reporte ATS se calcula una vez y después se lee

**Estado:** Pedido por el autor a partir de la queja de una persona usuaria real. Cambio listo para
revisión: la migración 031 se aplicó y verificó el 2026-10-20 en `jobby-test` y después en
producción (`jobby`), con aprobación del autor, antes de desplegar el código; el merge del PR
(que despliega) sigue esperando su aprobación. El texto es un borrador redactado con asistencia de IA que el autor revisa y
hace suyo.

**Medición previa** (2026-10-19 y 2026-10-20, cuenta real, horarios de los registros de Render):
abrir un reporte ATS tardaba de 6 a 9 segundos cada vez y cada apertura gastaba una de las 5
consultas diarias del plan gratuito (50 en premium). Abrir el mismo reporte tres veces seguidas
gastaba tres.

**Causa** (confirmada en el código). `GET /ats/{job_id}` rehacía todo y no guardaba nada: (1)
`extract_job_keywords` pedía las palabras clave del puesto a DeepSeek, y como es una IA salían
distintas en cada apertura; (2) `_semantic_matches` pedía a OpenAI los vectores de las palabras y
de los términos del CV, aunque las skills del perfil ya guardan el suyo; (3) el límite diario se
descontaba antes de mirar si ya había un resultado.

**Elegido.**
- **Un reporte guardado por puesto** en la tabla nueva `ats_reports` (migración 031, clave primaria
  `job_id`): puntaje, `keyword_matches`, `format_issues`, el documento del CV principal con el que se
  calculó, una huella de su `parsed_data` y la versión del algoritmo (`ATS_REPORT_VERSION`).
  Va en una tabla aparte y no en columnas de `job_descriptions` porque el modelo `JobDescription`
  devuelve las columnas que no conoce (`extra="allow"`) y el reporte lleva fragmentos del CV
  (`matched_text`) que no deben salir en `GET /jobs`.
- **Cuándo vale.** El reporte guardado se sirve si coinciden el id del CV principal, la huella de su
  `parsed_data` y la versión del algoritmo. Se usó la huella del contenido y no `updated_at`:
  releer un CV reemplaza `parsed_data` sin tocar esa fecha (solo `set-primary` la actualiza). Si el
  CV principal cambia, el reporte se recalcula. Subir `ATS_REPORT_VERSION` al cambiar una regla del
  cálculo (por ejemplo, si se aprueba el límite de palabra) hace que lo guardado con la regla vieja
  se recalcule en vez de seguir mostrándose.
- **Palabras clave estables.** Son las del reporte (`keyword_matches[].keyword`): no hay otra
  columna que mantener sincronizada. La primera vez que se abre el reporte de un puesto se extraen
  con IA, como hasta ahora (así se completan también los puestos anteriores a este cambio, que no
  tienen nada guardado); desde entonces, cada recálculo (por ejemplo, tras cambiar el CV) las
  reutiliza y no vuelve a consultar a la IA.
- **Límite diario.** Solo cuenta calcular un reporte nuevo (primera vez, o rehacerlo tras cambiar el
  CV principal). Releer uno guardado no gasta nada, ni siquiera con el cupo del día agotado. El 429
  conserva el esquema de error estándar (`ATS_RATE_LIMIT_EXCEEDED`, con `limit` y `reset_at`). Un
  reporte desactualizado con el cupo agotado también da 429: no hay forma de recalcularlo.
- **`POST /ats/optimize`** parte del mismo reporte guardado (así «antes» coincide con lo que la
  persona vio y las palabras clave no cambian entre el reporte y la optimización) y, si no hay uno
  vigente, lo calcula y lo guarda sin gastar el límite del ATS (tiene su propio cupo mensual,
  Decisión 25).
- **Vectores ya guardados.** Los términos del CV que son skills del perfil se comparan con el vector
  que ya está en `skills.embedding`, buscado por nombre exacto: el mismo modelo sobre el mismo texto
  da el mismo vector, así que el resultado no cambia (una prueba compara los estados con y sin
  vectores guardados). Los términos sin vector (experiencia, estudios, skills cargadas a mano) siguen
  yendo a OpenAI en un lote, y los vectores guardados de otro tamaño se descartan. La lectura de
  `skills` solo ocurre si hay palabras sin coincidencia literal.
- El puntaje y cada coincidencia no cambian para las mismas palabras clave: la suite del ATS
  (`test_ats_reality.py`, `test_skill_aliases_in_matching.py`) pasa sin modificar.

**Alternativa descartada: sacar las palabras clave al analizar el puesto.** Sumaría al paso del
análisis, que la persona mira esperando (Decisión 23), una llamada a DeepSeek de varios segundos por
cada puesto, también por los que nunca abren el ATS, y igual haría falta el camino de la primera
apertura para los puestos que ya existen. Costo de no hacerlo: la primera apertura de cada reporte
sigue incluyendo esa llamada. Si el autor prefiere pagarla antes, la opción que no suma espera es
pedirlas en la tarea de comparación, en paralelo con la explicación con IA; no se implementó.

**Si la migración todavía no está aplicada.** Toda lectura y escritura de `ats_reports` se atrapa y
se registra como aviso: el reporte se calcula en cada apertura y gasta la consulta, igual que antes
de este cambio. Una prueba lo cubre simulando la tabla ausente.

**Orden de despliegue (cambio de esquema: requiere aprobación explícita del autor).**
1. Aplicar `031_ats_report_cache.sql` primero en `jobby-test` y comprobar la tabla, la política y que
   `anon` y `authenticated` no tengan privilegios. **Hecho el 2026-10-20** (ver abajo).
2. Aplicarla en producción (`jobby`). Es aditiva: una tabla nueva que el código viejo no lee.
   **Hecho el 2026-10-20**: mismas comprobaciones de catálogo (sin escribir datos de prueba en
   producción); la tabla quedó vacía y los 9 puestos y 4 usuarios que había, intactos.
3. Recién después, mergear y desplegar el código.

**Qué cambia para la persona.**
- Releer un reporte ya visto es una lectura de la base y no gasta el límite.
- Las palabras clave de un puesto dejan de cambiar entre aperturas. La primera apertura después de
  desplegar recalcula (no hay nada guardado todavía) y gasta una consulta; las palabras clave que
  salgan pueden diferir de las que la persona vio antes.
- Cambiar el CV principal recalcula el reporte (gasta una consulta) sin cambiar las palabras clave.
- Editar el puesto con `PATCH /jobs/{id}` no vuelve a extraer palabras clave: sus datos editables
  son título, empresa, seniority, modalidad y salario, y corregirlos no debe cambiar el reporte.
- No hay botón para pedir palabras clave nuevas de un puesto.

**Datos de personas.** `ats_reports.keyword_matches[].matched_text` copia fragmentos del CV. La tabla
sigue el esquema de acceso del resto (RLS por dueño, sin privilegios para `anon` ni `authenticated`),
ningún endpoint de administración la lee (el admin solo ve métricas agregadas) y se borra en cascada
con el puesto y con la cuenta.

**Límites y pendientes.**
- Dos primeras aperturas simultáneas del mismo reporte calculan las dos y gastan dos consultas;
  gana la última escritura. Es el comportamiento de antes y es raro.
- No se midió en producción después del cambio: el objetivo es menos de 1 segundo al releer. Se
  mide al desplegar, con los registros de Render.
- Siguen siendo decisiones del autor, sin tocar: qué fuentes cuentan como evidencia, qué cuenta como
  palabra clave, la regla «contenida en» sin límite de palabra y cualquier cambio en el puntaje.
- La reutilización de vectores es una optimización chica: el lote de términos del CV sigue existiendo
  mientras haya experiencia o estudios en el CV.
- **Pruebas:** `tests/unit/test_ats_report_cache.py`. Primera apertura calcula y guarda; la segunda no
  llama a la IA ni a los vectores y no gasta el límite; cambiar el CV principal, releerlo o subir la
  versión del algoritmo invalida; un puesto sin nada guardado se completa; la 6.ª apertura de un
  reporte nuevo del plan gratuito da 429 y lo ya calculado se sigue leyendo; una fila dañada se
  recalcula; sin la tabla el reporte funciona como antes. La migración se probó dos veces seguidas
  en un PostgreSQL 16 descartable (cascada, `ON CONFLICT (job_id)` y sin acceso para la clave
  pública). El 2026-10-20 se aplicó en `jobby-test` y en producción y se comprobó contra su catálogo: 9 columnas,
  clave primaria `job_id`, dos claves foráneas con cascada, índice por `user_id`, RLS activo, la
  política de dueño, y `anon` y `authenticated` sin ningún privilegio (`service_role` sí). Un bloque
  con la identidad de cada rol, deshecho al final como `tests/sql/direct_table_access.sql`, dio dos
  upserts = una fila con el último puntaje, lectura y escritura con «permiso denegado» para `anon` y
  `authenticated`, y cascada al borrar el puesto; no quedó ningún dato de prueba (ese bloque solo se
  corrió en `jobby-test`).

---

## Actualización — Decisión 33 (2026-10-20): el tope diario de ATS del plan gratuito pasa de 5 a 10

**Estado:** Pedido y aprobado por el autor el mismo día en que el tope lo dejó sin poder abrir
reportes.

**Qué pasó (medido).** Los registros de Render (hora UTC, el día del tope empieza a las 00:00 Z) muestran
5 aperturas con 200 entre las 03:03 y las 03:42 (cuatro del mismo reporte) y dos con 429 desde las
03:42. El autor dijo «hoy no hice ningún ATS, solo revisé los que tenía»: era cierto, y era justo lo
que gastaba el cupo, porque hasta el #105 releer un reporte lo recalculaba y contaba como uno nuevo.
El contador vive en Redis (`rate:ats:{persona}:{día UTC}`), se reinicia a las 00:00 UTC (21:00 en
Argentina) y también suma los intentos rechazados.

**Por qué el #105 solo no alcanzaba.** Releer un reporte guardado no gasta cupo, pero la tabla
`ats_reports` arrancó vacía: la primera apertura de cada reporte lo calcula, lo guarda y gasta una
consulta. La cuenta tiene 6 puestos, así que con 5 por día no podía ver todos aunque esperara al
reinicio.

**Elegido.** `rate_limits._rule`: el plan gratuito pasa de 5 a **10** reportes nuevos por día; premium
sigue en 50. El 10 iguala a los análisis de puestos gratuitos por mes (10): cada puesto genera como
mucho un reporte nuevo por versión del CV, así que el tope diario deja de ser lo que impide ver los
reportes de los puestos que la persona tiene. Las pruebas del tope (`test_rate_limits.py` y
`test_ats_report_cache.py`) pasan a 10 y a 11 puestos.

**Costo.** Cada reporte nuevo es una llamada de texto a DeepSeek (palabras clave) y hasta dos lotes
de vectores de OpenAI; no se midió su costo por reporte. Queda acotado: 10 por día por persona y solo
reportes nuevos, no relecturas.

**Lo que no cambia (queda como estaba).** El día se cuenta en UTC; los intentos rechazados siguen
sumando; premium; y la regla de que solo un reporte nuevo, o rehecho tras cambiar el CV principal,
gasta cupo.

---

## Actualización — Decisión 28 (2026-10-21): `certifi` y `pillow`

**Estado:** Pedido por el autor tras el rojo del escaneo de Trivy en el PR #107.

**Qué encontró Trivy.** Ocho hallazgos altos o críticos con versión corregida, todos en
`services/api/poetry.lock` (`pnpm-lock.yaml`: cero): `certifi` 2026.6.17 (crítico, GHSA-6q48-6c7w-9gw2:
el paquete incluye raíces de emSign con claves intermedias comprometidas; corregido en 2026.10.19) y
`pillow` 12.3.0 (siete avisos, corregidos en 13.0.0: uno crítico en el decodificador JPEG, que el informe
corta, denegación de servicio con imágenes de ancho cero, con un GIF armado, con lecturas fuera de
límites en el decodificador y en el codificador de TIFF y con un PDF armado al agregar páginas, y una fuga
por memoria no inicializada al decodificar TIFF). Aparecieron porque se actualizó la base de
vulnerabilidades: el escaneo falla en cualquier PR aunque el PR no toque dependencias.

**Alcance real** (analizado, no supuesto).
- `certifi` es el almacén de certificados de todo el HTTPS de salida (`httpx`, `httpcore`, `requests` y
  `sentry-sdk`), o sea de las llamadas de la API a los servicios externos. Quien pudiera usar esas claves
  en la red entre la API y esos servicios podría suplantarlos. Es el de más peso, aunque exige una
  posición en la red.
- `pillow` solo lo trae `pdfplumber` (`Pillow>=12.2.0`, sin tope). El código propio no lo importa y la app
  solo llama a `extract_text()` sobre los PDF subidos, que no decodifica sus imágenes: el riesgo directo hoy
  es bajo. Se cierra igual porque la detección de formato del CV va a mirar las imágenes de los PDF.
- `braces` (alta, alerta 80 de Dependabot) sigue sin versión corregida y ya está analizada más arriba
  (herramientas de compilación y de lint, no corre al atender pedidos). No se toca.

**Elegido.** `poetry update certifi pillow --lock`: solo esos dos cambian en el lock (`certifi` 2026.6.17 →
2026.10.19 y `pillow` 12.3.0 → 13.0.0); `pyproject.toml` no cambia. Dos casos nuevos en
`test_dependency_floor.py` fijan el piso de versión, como se hizo con `multidict`.

**Verificado.** En un entorno nuevo instalado desde el lock: los 935 tests del backend pasan (sin los de
base real, que corren en el CI), `mypy app/` y `ruff check app/ tests/` quedan limpios; el texto que
`extract_pdf_text` saca de un PDF de dos columnas es idéntico con Pillow 12.2 y con 13.0 (mismo hash) y
`page.to_image` sigue funcionando; con el `certifi` nuevo validan su TLS DeepSeek, OpenAI, Supabase,
LemonSqueezy, la API y la web. Los dos casos del piso fallan con el entorno viejo y pasan con el nuevo.

**Límites.** Pillow pasa de la versión 12 a la 13, una versión mayor: la compatibilidad con `pdfplumber`
0.11.10 se probó con la lectura de un PDF generado, no con un CV real subido en producción; eso se comprueba
después del despliegue. Los 13 tests de `test_real_database.py` no corren en la máquina del autor, solo en
el CI.

---

## Decisión 34 — El formato del CV se lee del PDF y el ATS avisa cuando no lo pudo evaluar

**Estado:** Aprobada. Pedido a partir de un hallazgo del 2026-10-21 y mergeada por pedido del autor
(PR #109) con los PR #110 y #111 en un solo despliegue: desde entonces baja el puntaje ATS de los CV
de varias columnas, con imágenes o con tablas que se lean. El texto es un borrador redactado con
asistencia de IA que el autor revisa y hace suyo.

**Hallazgo** (2026-10-21, código y base de producción). `parsed_data.format_flags` (`has_tables`,
`multi_column`, `has_images`, `headers`) solo se **leía**, en `ats_analyzer/format_checker.py`;
ninguna parte de `services/api/app` lo escribía. En producción había 2 CV leídos y ninguno tenía la
clave. Consecuencia: las penalizaciones de formato (tablas −10, varias columnas −10, imágenes −10,
títulos no habituales −5; `ATS_FORMAT_PENALTIES` en `apps/web/lib/guides/facts.ts`) no se aplicaban
nunca y el reporte decía «No detectamos problemas de formato» para cualquier CV. Las guías públicas
(«Qué es un ATS…» y «CV compatible con ATS») dicen que Jobby las resta: no era cierto en la práctica.

**Segundo problema, el mismo origen.** `pdf_extractor.py` leía con `page.extract_text()`, que agrupa
por renglón de la hoja: en un CV de dos columnas **intercala** un renglón de cada lado. Una persona
con una plantilla de Canva (dos columnas, foto, títulos poco habituales) quedó con 4 habilidades
leídas de más de 20: las que listaba en la barra lateral salían pegadas a las viñetas de la otra
columna («Python • Mentoría a dos personas…»), y por eso el ATS le marcaba como faltantes SQL, Git,
Linux o React.

**Elegido.**
- **Se anota el formato al leer el CV** (`cv_parser/pdf_layout.py`, la misma pasada de `pdfplumber`,
  local, sin IA ni costo) y se guarda en `parsed_data.format_flags` con la forma que ya leía el
  chequeo. Solo para `type = cv`: el ATS evalúa el CV que la persona envía, no la exportación de
  LinkedIn. Si el análisis del diseño falla, la lectura sigue con el texto plano de siempre y **la
  clave no se escribe** (un `{}` diría «sin problemas»).
- **Varias columnas.** Hay un hueco vertical de al menos 10 pt (cuatro espacios de texto de 10 pt)
  que cruzan a lo sumo el 10 % de los renglones (el nombre o un título de ancho completo) y, a cada
  lado, una columna de al menos 6 renglones de texto seguidos, separados por poco más que el alto
  de una letra. Se descartan así los casos que dejan un hueco parecido sin ser columnas: las fechas
  alineadas a la derecha (un renglón cada varios), las viñetas con sangría ancha (la viñeta no es
  texto) y un encabezado con el contacto a un costado (menos de 6 renglones). Se midió con CV
  sintéticos hechos con `reportlab` (solo para calibrar; no es dependencia). Los 9 de columnas
  (barra lateral a izquierda o a derecha, con pocos renglones o con títulos en minúscula, columnas
  iguales, tres columnas, banner arriba, interlineado doble) dieron «varias columnas»; los 5 de una
  columna (fechas en una tabla sin bordes, texto justificado, grilla de habilidades, tabla con
  bordes, contacto a la derecha) no. El umbral de 10 pt sale de dos columnas justificadas con el
  hueco variable: se detecta desde 12 pt y no a 10 pt o menos, que ya es el tamaño de un espacio
  estirado de texto justificado.
- **Imágenes.** Cuenta una imagen que ocupe al menos el 0,5 % de la hoja (una foto, un logo): los
  íconos de contacto de las plantillas (unos 20 × 20 pt, 0,08 %) no. Es una decisión mía sobre el
  texto «si tiene imágenes»: sin el umbral, un solo ícono restaría 10 puntos.
- **Tablas.** `find_tables()` con bordes visibles y al menos dos celdas con texto: una línea bajo un
  título o un recuadro no son una tabla. Una tabla **sin bordes** no se detecta (si arma columnas,
  sí cuenta como varias columnas).
- **Títulos de sección.** Renglones de hasta 4 palabras, sin números, con estilo de título (tamaño
  1,2 veces el del cuerpo, o negrita en mayúsculas) y que compartan ese estilo con al menos otro
  renglón. Quedan afuera el texto más grande de la primera hoja (el nombre), los cargos en negrita
  del tamaño del cuerpo y un CV con un solo título. Se prefiere perder un título a inventarlo: cada
  título de más puede restar 5 puntos que la persona no merece. Para compararlos con
  `STANDARD_HEADERS` se ignoran mayúsculas, acentos y los dos puntos finales (antes «Educación»,
  con acento, contaba como no habitual aunque `educacion` esté en la lista).
- **Texto en orden de lectura.** Si la hoja tiene columnas, cada una se lee entera, la izquierda
  antes que la derecha, y los renglones de ancho completo cortan el orden de arriba abajo. Una hoja
  de una columna se lee exactamente igual que antes (una prueba compara el texto con el de
  `extract_text()`). En los 14 PDFs el conjunto de palabras es idéntico antes y después (no se
  pierde texto) y las habilidades de la barra lateral que quedan solas en su renglón pasan, por
  ejemplo, de 6 a 17 de 17 (barra a la izquierda con foto), de 10 a 17 (banner arriba) o de 1 a 13
  (tres columnas). El tiempo por hoja sube de unos 35 ms a unos 40 ms en las plantillas de columnas;
  el caso más caro medido (una hoja de una columna con seis renglones armados con tablas sin bordes)
  pasó de 49 a 84 ms. `find_tables()` tardó hasta 1,7 s en una hoja con 6.000 trazos vectoriales
  (un máximo de 20 hojas por CV); no se le puso tope.
- **El reporte ATS dice cuándo no se pudo evaluar.** `ATSReport.format_evaluated` es `false` cuando
  el CV principal no tiene `format_flags` (leído antes de este cambio, o con el análisis fallido): la
  pantalla muestra «No pudimos evaluar el formato de este CV» con cómo evaluarlo, en vez de «No
  detectamos problemas de formato». Sin banderas no se descuenta nada, así que **el puntaje de esos
  CV no cambia**. No se guarda en `ats_reports` (sin migración): sale del CV principal, cuya huella
  ya valida el reporte guardado.
- **`ATS_REPORT_VERSION` pasa de 1 a 2** (Decisión 33): lo guardado con el algoritmo viejo deja de
  servirse y se recalcula en la próxima apertura. Estrictamente, un reporte guardado de un CV sin
  banderas daría lo mismo recalculado; se sube igual porque la regla del cálculo cambió y es lo que
  esa decisión pide.

**Qué cambia para la persona.**
- Los CV ya leídos **no se reprocesan solos**. Para evaluar el formato de uno hay que **volver a
  subirlo** (Mi perfil → Mejorar perfil, paso 2: reemplaza al CV del slot 1 y lo vuelve a leer, con
  la misma llamada a la IA de siempre): queda con banderas y su reporte se recalcula.
- Un CV leído desde el despliegue pierde hasta 35 puntos de ATS: −10 por tablas, −10 por varias
  columnas, −10 por imágenes y −5 por títulos no habituales (piso en 0). Por ejemplo, una plantilla
  de dos columnas con foto y «Perfil académico» baja 25 puntos.
- La primera vez que se abra cada reporte después del despliegue se recalcula (por la versión) y
  cuenta para el tope diario: 10 en el plan gratuito. Las palabras clave del puesto no cambian
  (Decisión 33).
- El texto que recibe la IA de un CV de columnas es el de cada columna entera: debería rendir más
  habilidades que las 4 que se leyeron antes. No se midió con la IA real ni con el CV de esa persona
  (no se usan datos personales reales).

**Decisiones que quedan en manos del autor.**
- **Mergear** (despliega, reinicia la API de Render y baja puntajes de los CV que se lean desde
  entonces): resuelta, el autor pidió mergearla.
- **El vocabulario de `STANDARD_HEADERS`.** Tal como está solo admite `experiencia`, `educacion`,
  `habilidades`, `idiomas`, `certificaciones` y sus equivalentes en inglés, así que «Experiencia
  laboral», «Formación académica», «Perfil» o «Proyectos» cuentan como no habituales y restan 5.
  Probablemente sea lo que más CV penalice. No lo amplié: es qué se considera «habitual», y las
  guías públicas lo describen con esa palabra. Propuesta aparte: sumar esos títulos a la lista.
- **El umbral de imágenes** (0,5 %): con otro valor cambia qué íconos cuentan.
- **Si las guías deben aclarar** que «imágenes» son fotos y logos y no íconos. El texto actual sigue
  siendo exacto en lo que dice; no se tocó.

**Límites conocidos.**
- Una tabla sin bordes no cuenta como tabla; un CV de tres o más columnas se marca como varias y se
  lee mejor que antes, pero no perfecto; un título con las letras muy separadas («P E R F I L») se
  lee como letras sueltas y no se reconoce; un nombre centrado que cae dentro de la columna derecha
  se lee después de la barra lateral (no se pierde, solo cambia de lugar).
- La viñeta de algunas fuentes se lee como `(cid:127)` (pasaba antes y pasa ahora; la IA la ignora).
- No hay migración ni cambios en `render.yaml`, variables de entorno o flujos de cobro.

**Pruebas.** `tests/unit/test_pdf_layout.py` (PDFs armados a mano, sin dependencias: dos columnas con
foto, barra lateral angosta, nombre de ancho completo, una columna igual que antes, fechas y viñetas
que no son columnas, ícono contra foto, tabla con bordes contra línea y recuadro, títulos, y que un
fallo del análisis no rompe la lectura), `test_format_checker.py` (penalizaciones, títulos sin
acentos, estado «evaluado»), `test_ats_report_cache.py` (versión 1 recalculada, puntaje con
penalizaciones, estado «no evaluado» guardado y recalculado al releer) y `test_async_tasks.py` (las
banderas se guardan con el CV, no con el PDF de LinkedIn, y de punta a punta con un PDF de dos
columnas). Frontend: `format-issues-card.test.tsx` y las claves en ambos idiomas. Se verificó que
todos fallaban contra el código anterior.

---

## Decisión 35 — El ATS mide habilidades reales del aviso y las busca por palabra completa

**Estado:** Pedida por el autor el 2026-10-22. Cambio listo para revisión en un PR abierto; **no está
mergeado**: mergearlo despliega y cambia el puntaje de los reportes ATS ya calculados, que se rehacen
la primera vez que se abren. El texto es un borrador redactado con asistencia de IA que el autor revisa
y hace suyo.

**Hallazgo** (2026-10-21, reportes guardados en producción y código). Dos reglas hacían que el ATS
midiera cosas que no son habilidades y que marcara coincidencias que no lo eran:

- **Qué se pedía.** `extract_job_keywords` le ordenaba a la IA incluir «skills, frameworks,
  herramientas, seniority, idiomas y títulos requeridos». Los reportes guardados traen «Junior», el
  título del puesto entero, «Modalidad híbrida», «Vicente López», «Seniority mínimo 1 año de
  experiencia» o tareas como «Escritura de consultas SQL y mantenimiento de base de datos». Nada de
  eso se escribe en un CV: cuenta como faltante y baja el puntaje de quien sí cumple.
- **Cómo se buscaba.** La coincidencia literal era «el texto está contenido en el término del CV»:
  «Git» aparecía en «Digital» (se vio en el reporte de un puesto real con el CV de la persona),
  «SQL» en «PostgreSQL», «Java» en «JavaScript» y «Go» en «Django».

**Elegido.**
- **Se le pide otra cosa a la IA.** Solo habilidades (lenguajes, frameworks, librerías, herramientas,
  plataformas, metodologías, certificaciones e idiomas), con su nombre corto y común («SQL», no
  «Escritura de consultas SQL»), y se le dice qué dejar afuera: título, nivel, modalidad, jornada,
  ciudad o país, empresa y tareas escritas como frase.
- **Un filtro propio, conservador, como segunda defensa** (`ats_analyzer/keyword_filter.py`), porque la
  IA no es determinista. Descarta: palabras de nivel, modalidad y jornada («junior», «híbrida», «full
  time», incluidos el femenino y «home office»); el título del puesto y el nombre de la empresa
  enteros (un «Python» dentro del título sigue valiendo); lo que el puesto guarda como nivel y
  modalidad, que es texto libre y suele traer el lugar; una ciudad o país de una lista corta; y toda
  keyword de más de 5 palabras (una tarea escrita como frase). Quita repetidas.
- **El filtro corre sobre las keywords de la IA y sobre las ya guardadas del puesto.** Un reporte
  viejo no vuelve a pedirle keywords a la IA (Decisión 33): se rehace con las que tenía, ya filtradas.
- **Palabra completa.** La keyword tiene que aparecer rodeada de algo que no sea letra, número, `+`
  ni `#`: «C» no está en «C++» ni «Git» en «Digital»; un punto al final de la oración no cuenta como
  parte de la palabra («Python.»). Los alias y las traducciones («API REST» y «REST APIs») siguen
  contando como literales por su camino de siempre.
- **`ATS_REPORT_VERSION` pasa de 2 a 3** (Decisión 33): lo guardado con las reglas viejas deja de
  servirse y se recalcula en la próxima apertura.

**Medido con los reportes reales** (solo lectura, 2026-10-22): el puesto de Iquall pasa de 36 a 29
keywords (salen el título, «Modalidad híbrida», «Vicente López», «Seniority mínimo 1 año…», la
residencia y dos frases largas) y el puesto de prueba de 20 a 15 (salen el título, «Junior» y tres
frases). Con el CV actual de la persona, el puesto de prueba pasaría de 32 a unos 47 (10 de 15
habilidades presentes, menos 20 de formato); es una cuenta, no una medición del reporte nuevo.

**Qué cambia para la persona.**
- La primera vez que se abra cada reporte después del despliegue se recalcula y cuenta para el tope
  diario (10 en el plan gratuito). Las keywords del puesto no se piden de nuevo a la IA.
- Sube el puntaje de quien perdía puntos por «Junior», la ciudad o el título, y puede bajar el de quien
  tenía de más una coincidencia por texto contenido («SQL» por «PostgreSQL»).
- Un puesto analizado desde el despliegue pide keywords más cortas y solo de habilidades.

**Decisiones que quedan en manos del autor.**
- **Mergear** (despliega, reinicia la API de Render y cambia puntajes de reportes ya vistos).
- **La lista de ciudades y países** (`_PLACES`): es corta a propósito; quien trabaje en otra región la
  amplía. Fuera de ella, lo evita el pedido a la IA.
- **El tope de 5 palabras** (`MAX_SKILL_WORDS`): descarta tareas escritas como frase; con 4 se iría
  también «Testing y mantenimiento de software».
- **Si las habilidades blandas cuentan** («Comunicación», «Autonomía», «Trabajo en equipo»): hoy
  cuentan, igual que antes, y casi nunca coinciden de forma literal con un CV.

**Límites conocidos.**
- Quedan como keywords, en los puestos ya guardados, frases cortas que la IA devolvió y que no son
  una herramienta («Automatización de procesos internos», «Integraciones», «Backend»): el filtro solo
  descarta lo que seguro no es una habilidad.
- El CV se compara por sus habilidades, experiencias y estudios, no por su lista de idiomas: una
  keyword «Inglés» sale faltante aunque el CV lo declare en idiomas. No se cambió; es una propuesta
  aparte.
- Si el filtro deja la lista vacía, el reporte queda sin keywords y su puntaje es 100 menos las
  penalizaciones de formato, que es lo que ya pasaba cuando la IA devolvía una lista vacía.
- No hay migración ni cambios en `render.yaml`, variables de entorno o flujos de cobro.

**Pruebas.** `tests/unit/test_ats_real_skills.py` (nivel, modalidad, jornada, ciudad, título, tareas
escritas como frase, texto libre del puesto, repetidas; «Git» en «Digital», «SQL» en «PostgreSQL»,
«Java» en «JavaScript», «Go» en «Django», «C» en «C++»; palabra completa en una skill, una oración y
una lista; lo que se le pide a la IA y que lo guardado se filtra sin consultarla) y
`test_ats_report_cache.py` (un reporte de la versión 2 con «Junior» y «Buenos Aires» guardados se
rehace sin ellos y sin volver a la IA). Se verificó que los nuevos fallaban contra el código anterior.

---

## Actualización — Decisión 28 (2026-10-23): `next`

**Estado:** Pedido por el autor tras el rojo del escaneo de Trivy en `main` (merge del PR #112). Cambio
listo para revisión en un PR abierto; **no está mergeado**: mergearlo despliega la web en Vercel.

**Qué encontró Trivy.** Dos hallazgos con versión corregida, ambos en `pnpm-lock.yaml`
(`services/api/poetry.lock`: cero), sobre `next` 15.5.27:
- **GHSA-2464-fhr4-w9xw (crítico):** ejecución remota de código sin autenticación en la API de
  optimización de imágenes cuando hay archivos SVG, en Linux con glibc. Afecta de 10.0.0 a 15.5.27 y de
  16.0.0 a 16.4.0; corregido en 15.5.28 y 16.4.1 (el aviso también acepta `sharp` 0.35.5 o más).
- **CVE-2026-94482 (alto):** denegación de servicio con pedidos armados contra Server Actions.

Aparecieron porque la base de Trivy se actualizó: el escaneo del PR #112 había pasado dos días antes.

**Alcance en este repositorio.** El código no importa `next/image` y `next.config.ts` no configura
`images`. **No se comprobó** si `/_next/image` queda alcanzable con esa configuración, ni cómo lo sirve
Vercel; no se afirma que el sitio fuera explotable. Se actualiza igual porque es crítico y la corrección es
un parche del mismo minor.

**Elegido.** `next` de 15.5.27 a **15.5.28**: `apps/web/package.json` pasa a `^15.5.28` y el lock cambia
solo en `next`, `@next/env` y los ocho binarios `@next/swc-*` con sus hashes (45 líneas). Se hizo con
`pnpm install --lockfile-only` porque `pnpm up next@^15.5.28` también re-resolvía `esbuild`, `rollup` y otras
dependencias sin relación (731 líneas), lo que no era necesario. `eslint-config-next` queda en 15.5.27: no
figura en los avisos. Los `overrides` del lock siguen igual. Un test de piso en
`lib/security/dependency-floor.test.ts` avisa si el lock vuelve a una `next` anterior.

**Verificado.** `pnpm install --frozen-lockfile`, `typecheck`, `lint`, los 492 tests de la web,
`pnpm build` (Next.js 15.5.28, 25 páginas, con valores de relleno en las variables públicas) y Trivy local
con los mismos argumentos que el workflow: 0 hallazgos con el cambio, 2 sin él.

**Lo que no cambia.** El backend, los workflows, `render.yaml`, las variables de entorno y los webhooks.
**Decisión del autor:** mergear (despliega la web).

## Actualización — Decisión 31 (2026-10-23): el stack tecnológico se compara por nombre, no por categoría

**Estado:** Hallazgo de la medición del 2026-10-18, que quedó como propuesta sin aprobar. El autor
preguntó el 2026-10-23 si seguía sin arreglar y se tomó como pedido de arreglarlo. El límite de
palabra del ATS (el otro hallazgo) ya lo había cerrado la Decisión 35.

**Problema (medido).** La compatibilidad con la empresa mezcla el stack tecnológico del puesto (la
mitad de ese componente, que pesa 15 % del MatchScore). `s_company` solo comparaba contra las skills
con `category = "technical"`, pero el lector de CV no fija las categorías (pide «minúsculas cuando se
pueda») y deja «programming», «frontend», «api», «devops», «tools»… Un CV leído hoy puede no traer
ninguna «technical»: el perfil con las 10 tecnologías del puesto «Full Stack Jr» daba 0 en el stack, y
otro con Git, Linux y Docker bajo «tools» tampoco las contaba.

**Elegido.** El stack se compara con **todas** las skills y por su forma común (`skill_key`): lo que
decide es el nombre, no la etiqueta. Se mantienen sin cambios el resto del componente (modalidad,
industria) y el respaldo semántico, que sigue usando solo las skills «technical»: ampliarlo cambia
qué se parece a qué y no es lo que se corrige. La categoría de una skill no se tocó ni se
reasigna en los datos guardados.

**Medición con producción** (7 comparaciones donde las skills guardadas hoy coinciden con las del
momento del cálculo; la regla anterior reproduce el puntaje y el componente guardados de las 7):

| Puesto | Stack antes → ahora | Puntaje guardado → nuevo |
|---|---|---|
| Full Stack Jr (cuenta con CV de Canva) | 0,00 → 1,00 | 65 → 73 |
| Analista de Datos Jr (misma cuenta) | 0,00 → 0,75 | 45 → 51 |
| Backend Python Jr (otra cuenta) | 0,10 → 1,00 | 46 → 53 |
| Generalist Software Engineer | 0,11 → 0,56 | 19 → 20 |
| Software Development Engineer | 0,00 → 0,20 | 10 → 10 |
| Chef Ejecutivo (sin stack) | 0,80 → 0,80 | 3 → 3 |
| Software Engineer | 1,00 → 1,00 | 18 → 18 |

Sube el puntaje de cuatro de siete, hasta unos 8 puntos, y ninguno baja: solo se suman coincidencias.
Junto con los alias de la Decisión 31 (el puesto Full Stack pasaría de 73 a unos 78). Los puntajes
guardados **no se recalculan**: cambian cuando la persona vuelve a analizar el puesto.

**Límites que quedan abiertos.** Una skill con el nombre del stack cuenta aunque el lector la haya
clasificado como blanda o metodología (el nombre manda). Los nombres compuestos («Office (Word,
Excel, PowerPoint)», «Agile / Scrum») siguen sin partirse en componentes, así que «Excel» no
coincide con el primero. El respaldo semántico compara contra el vector de todo el puesto y no
contra cada tecnología, por lo que casi nunca suma (0 coincidencias en las comparaciones medidas).

---

## Actualización — Decisión 30 (2026-10-28): enlaces a las guías, alias del nombre y favicon

**Estado:** Pedido por el autor (seguir ampliando las búsquedas en las que aparece el sitio, con
el dominio actual); el texto exacto se mostró antes de implementarlo y la aprobación final es la
revisión del PR.

**Medición (Search Console y Bing Webmaster, 2026-10-28).** De las 13 URLs del sitemap, Google
indexó 1 (la home) y deja las otras 12 en «Descubierta: actualmente sin indexar»: las conoce pero
no las rastreó, es decir, hay poca demanda de rastreo y no un error del sitio. Googlebot pidió
`/favicon.ico` dos veces (15 y 27 de octubre) y recibió 404; el ícono declarado medía 32 px y la
guía de Google recomienda un favicon cuadrado de más de 48 px. «Solicitar indexación» respondió
«Cuota superada» en tres intentos; no hay forma documentada de ampliar ese cupo.

**Elegido.**
- Pie de la home: una lista con las ocho guías, cada una con su nombre como texto del enlace.
  Las etiquetas viven en `lib/guides/links.ts` y no en `guides.ts` porque el pie es un componente
  de cliente y importar las guías metería su texto completo en el JavaScript de la home; un test
  comprueba que haya un enlace por guía y en el mismo orden.
- `alternateName` de `WebSite` y `WebApplication`: «Jobby web» y «JobbyWeb» (`SITE_ALTERNATE_NAMES`
  en `lib/seo/site.ts`). El dominio es `jobbyweb`, así que el nombre se busca junto y separado.
- Favicon: `src/app/favicon.ico` con imágenes de 96, 48, 32 y 16 px (la más grande primero, porque
  Next copia el tamaño de la primera entrada en `<link sizes>`) y `icon.tsx` generado a 96 px. Un
  test lee el encabezado del ICO y el tamaño declarado.

**Límites.** Ninguno de los tres cambios hace que Google rastree antes: lo que más pesa sigue
siendo que otros sitios enlacen al nuestro. El favicon solo afecta al ícono junto al resultado,
nada indica que influya en la indexación ni en la posición. «JobbyWeb» es una pista para Google,
no una garantía de que lo tome como nombre.

---

## Decisión 37 — La lectura del PDF corre en un proceso aparte y el navegador del scraper sale por un proxy que valida al conectar

**Estado:** Pedida por el autor el 2026-10-28, a partir de tres pistas que la auditoría de seguridad
(skill `security-audit`, perfil `quick`) dejó sin cerrar. Cambio en la rama `fix/auditoria-hallazgos`,
**sin mergear**: mergearlo despliega. El texto es un borrador redactado con asistencia de IA que el
autor revisa y hace suyo.

### A. Lectura del PDF (pista 5 de la auditoría)

**Hallazgo.** Un PDF lo arma quien sube el archivo. El único control era el tamaño comprimido (10 MB) y
las 20 páginas, ambos después de descargarlo y abrirlo. Nada limitaba lo que se expande (un flujo
comprimido que se descomprime a GB), la cantidad de objetos ni el tiempo, y la lectura corría en un
hilo de la API (`asyncio.to_thread`), que no se puede cancelar y comparte los 512 MB con las tareas
locales. Un PDF armado a propósito podía reiniciar la API para todos o dejar ocupado uno de sus dos
cupos de tarea.

**Elegido.** `extract_pdf_content` valida lo barato (extensión, tamaño, firma `%PDF-`) y lanza
`python -m app.services.cv_parser.pdf_worker`, un **proceso hijo** que lee el PDF y devuelve una línea de
JSON con el texto y las banderas de formato, o el error con su código.

- **Topes del hijo** (Linux): puede crecer 200 MiB sobre lo que ya ocupa con las librerías cargadas
  (`RLIMIT_AS`), 20 s de CPU (`RLIMIT_CPU`) y se marca con `oom_score_adj=1000` para que, si el
  contenedor se queda sin memoria, el sistema elija al hijo y no a la API. Plazo de reloj de 120 s,
  holgado a propósito: la instancia gratuita tiene una fracción de CPU.
- **Aislamiento:** el hijo no hereda las llaves (Supabase, proveedores de IA, webhook) ni lee el `.env`
  (entorno mínimo y carpeta de trabajo sin él), y la API valida la respuesta en vez de confiar en ella.
  El texto devuelto se corta en 200 000 caracteres y la salida del hijo en 4 MiB.
- **Errores:** `PDF_TIMEOUT` (venció el plazo), `PDF_TOO_COMPLEX` (el sistema lo cortó o se cayó),
  `PDF_READ_ERROR` (respuesta inválida, o el PDF no se pudo leer: también cuando llegó al tope de
  memoria, porque el `MemoryError` se atrapa dentro del hijo). La persona ve el mismo mensaje de
  siempre (`public_error_message`); los códigos son para los registros.

**Alternativas descartadas.** (a) Worker de Render: USD 7/mes, fuera del presupuesto sin aprobación, y
no cambia que una lectura sin tope puede ocupar la máquina. (b) Seguir en un hilo con un tope de
caracteres o de páginas: el flujo comprimido se expande antes de que haya páginas que contar, y el hilo
no se puede matar. (c) `multiprocessing` con `fork`: la API es multihilo y el hijo heredaría su memoria
y sus llaves.

**Medición.** En Windows, con un PDF sintético de 20 páginas y 145 000 caracteres: ~2 KB de memoria de
Python por carácter y un pico de ~285 MB. En la imagen de la API (Linux, contenedor de 512 MB sin
swap), RSS máximo del hijo: 77 MB para un CV de 2 páginas, 95 MB (6 páginas), 156 MB (10 páginas
densas, 47 000 caracteres) y 222 MB (14 páginas muy densas, 80 000 caracteres), todos leídos en 1 a 3 s.
El PDF extremo (114 000 caracteres en Linux) usa 292 MB sin tope y con el tope falla con
`PDF_READ_ERROR`. Un CV real (1 a 4 páginas, 5 000 a 20 000 caracteres) queda lejos del tope.

**Verificado en Linux** (imagen construida con el `Dockerfile` de la API, usuario `appuser`,
`--memory=512m --memory-swap=512m`, Docker Desktop sobre WSL2): un PDF de 1,57 MB cuyo flujo de contenido
se expande a 1,5 GiB **mata el contenedor con la lectura anterior** (`OOMKilled=true`, salida 137) y,
con el hijo, falla en 1,8 s con `PDF_READ_ERROR` mientras la API sigue viva. Dentro del hijo: `RLIMIT_AS`
aplicado, `RLIMIT_CPU` de 20 s, `oom_score_adj` 1000, entorno con solo `LANG`, `PATH`, `PYTHONPATH` y
`PYTHONUTF8` (las llaves que se le pasaron al contenedor no aparecen) y carpeta de trabajo `/tmp`; un
bucle con 2 s de CPU se cortó a los 2,0 s con `PDF_TOO_COMPLEX`. La suite unitaria completa pasa en la
imagen (1117 tests; los 4 de Chromium se saltan porque la imagen no lo trae).

**Límites que quedan abiertos.**

- **No se probó en Render:** la verificación de arriba es en Docker Desktop (WSL2). El núcleo y los
  cgroups de Render pueden diferir; después del despliegue conviene subir un CV propio. En Windows
  (desarrollo) solo rige el plazo.
- Durante la lectura hay un intérprete más en memoria (77 MB en un CV de 2 páginas); con los dos cupos
  locales pueden coincidir dos.
- El PDF se sigue descargando entero a memoria antes de la validación de tamaño; el bucket no tiene
  `file_size_limit` (cambiarlo es una migración, no incluida acá).

### B. Navegador del scraper y DNS rebinding (pista 16)

**Hallazgo.** `ensure_public_http_url` y la guarda de `page.route` resolvían el nombre para decidir y
Chromium lo volvía a resolver para conectar. Un DNS del atacante que contesta una IP pública la primera
vez y una interna la segunda (127.0.0.1, la red privada, los metadatos de la nube) hacía que el
navegador llegara adonde la guarda había dicho que no. Hoy está dormido: la imagen de la API no
instala Chromium (pendiente aparte).

**Elegido.** `EgressProxy` (`scraper/egress_proxy.py`): un proxy HTTP en 127.0.0.1 con el que se lanza
Chromium, único camino de salida. Por cada conexión resuelve el nombre **una vez**, exige que **todas**
las IP sean públicas y conecta a esas mismas direcciones, sin una segunda consulta. HTTPS pasa como
túnel (`CONNECT`): el certificado lo sigue validando el navegador. Solo puertos 80 y 443. Como todo
sale por ahí, cubre también redirecciones, service workers, WebSockets y recursos de otros orígenes.
La guarda de `page.route` queda como corte temprano.

**Alternativas descartadas.** (a) `--host-resolver-rules` con la IP validada: se fija al lanzar, sirve
para un host y los recursos de otros orígenes quedarían sin resolver. (b) Atender cada pedido desde la
API con `route.fulfill`: cambia cookies, compresión y tamaños de todo el scraping. (c) Un proxy
externo: otro servicio que mantener y pagar.

**Verificación con Chromium real** (el de Playwright instalado en el equipo): con la validación real,
`127.0.0.1`, `localhost`, `[::1]` y HTTPS a loopback no llegaron al servicio interno (0 accesos), y
Playwright manda el tráfico de loopback por el proxy aunque no se lo pida. Un nombre sin DNS
(`sitio.test`) cargó por HTTP y por HTTPS: Chromium usa la resolución del proxy.

**Límites.** WebRTC (UDP) no pasa por el proxy: puede enviar paquetes a una IP interna sin leer la
respuesta. No se agregó el flag de Chromium para cerrarlo porque no se pudo comprobar su efecto.

**Pruebas.** `test_egress_proxy.py` (sockets reales: túnel, HTTP plano, destinos internos y puertos no
web, respuesta mixta, DNS que cambia de respuesta, destino caído, pedidos mal formados, cierre),
`test_egress_proxy_chromium.py` (Chromium real, se salta si no está instalado), `test_pdf_worker.py`
(hijo real, plazo, caída, respuesta inválida, límites simulados, entorno sin llaves) y los fakes de
los scrapers, que ahora comprueban que el navegador se lance con el proxy.

### C. El avance del asistente de alta pertenece a una cuenta (pista 14)

**Hallazgo.** El asistente de alta (el «wizard»: cuatro pasos para armar el perfil, ver la
explicación al final) guardaba su avance en `localStorage` bajo una sola clave, igual para todas las
cuentas del navegador: el paso en que iba, el borrador del paso 1 y las habilidades leídas de su CV.
Quien entraba después desde ese navegador (porque la sesión venció, o con otra cuenta) las veía en
el paso 3 y recibía el aviso «Terminá tu onboarding» de la persona anterior. La Decisión 23 ya
establece el principio contrario para la memoria de pantallas: nunca datos de la persona en el
navegador de la siguiente.

**Elegido.** Atar el avance a la cuenta, más borrarlo al cerrar sesión con el botón.

- El avance se guarda con el id de la cuenta (`ownerId`). Al leerlo, si el id no coincide, o el
  avance no tiene dueño (es de antes del cambio), se descarta y se devuelve el estado inicial.
- Quien vuelve con la misma cuenta (sesión vencida, otro día) retoma donde estaba.
- Un layout nuevo del wizard (`WizardOwnerProvider`) espera a saber quién es la cuenta y se la da a
  los cuatro pasos y al aviso. Si no se pudo saber, los pasos funcionan igual, sin leer ni guardar
  avance local, y no se borra el de nadie.
- «Cerrar sesión» sigue borrándolo (es lo que cubre quien lo usa en un equipo compartido: el
  texto no queda en el navegador).

**Alternativa descartada.** Solo borrar al cerrar sesión: deja afuera la sesión vencida y el inicio de
sesión, y quien sale a mitad del asistente perdía las habilidades leídas.

**Efecto visible.** Un avance guardado antes de este cambio se descarta una vez; la persona que lo
tuviera a medias vuelve al paso 1 (el perfil que ya guardó en el servidor se conserva).

**Verificación.** `progress.test.ts` y `owner.test.ts` (11 casos) y un recorrido con la web real en
Chromium, con Supabase y API falsos y dos personas: la versión anterior mostraba las habilidades de
una persona a la otra al vencer la sesión (5 de 11 comprobaciones); la nueva pasa las 11.

**Qué es el asistente de alta.** Es la guía de cuatro pasos que se abre desde «Completar perfil» (en el dashboard y en «Mi
perfil»): (1) datos
básicos del perfil (titular, resumen, puesto buscado, nivel, modalidad), (2) subir el CV en PDF,
(3) confirmar o rechazar las habilidades que se leyeron del CV y (4) revisar y finalizar. Se puede
saltear y retomar; el avance se guarda para no empezar de cero.
