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
