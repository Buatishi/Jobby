# AGENTS.md — JobMatch AI (repositorio raíz)

Prioridad de instrucciones: (1) reglas de la plataforma/sistema, (2) pedido explícito del
usuario en la tarea actual, (3) este archivo, (4) los AGENTS.md de `services/api/` y
`apps/web/` (detalle de stack de cada workspace; léelos al trabajar ahí, no los repitas).

## 0. Contexto estable
- Monorepo pnpm: `apps/web` (Next.js 15 + React 19 + TS estricto), `services/api` (FastAPI +
  Python 3.13+, Poetry), `packages/shared-types` (tipos TS compartidos).
- Supabase: Postgres + pgvector + Auth + Storage. Celery + Redis para tareas async.
- AI Gateway: DeepSeek es el proveedor principal (flujo free); Claude es ampliación premium,
  no el foco de desarrollo; OpenAI se usa únicamente para embeddings.
- Billing (LemonSqueezy) separa plan **free/premium**; independiente del rol **user/admin**.
  No mezclar ambos ejes en una misma condición.
- El admin solo accede a métricas agregadas. Nunca al contenido de CV ni a datos personales
  de otro usuario.
- Flujo core: registro → carga CV → análisis → creación de puesto → comparación →
  MatchScore → reporte ATS.
- Fuente de verdad: este repositorio y sus Markdown. No asumir contexto no documentado acá.
- Nunca hardcodear secretos, tokens ni datos personales reales (código, tests, fixtures, docs).
- Presupuesto operativo: máx. USD 20/mes, plazo máx. 3 meses. Toda dependencia o servicio
  que lo comprometa se señala explícitamente antes de adoptarse.

## 1. El sistema está en producción real
- Hay usuarios, datos y pagos reales (Render, Supabase, LemonSqueezy). Un cambio roto no es
  un error académico: rompe algo que funciona ahora mismo.
- Extremar cuidado y avisar explícitamente antes de tocar: `render.yaml`, `.github/workflows/`,
  variables de entorno, webhooks de LemonSqueezy, o cualquier cosa que afecte el pipeline de
  despliegue o el cobro real a usuarios premium.
- Ante duda entre una solución rápida y una segura, priorizar la que no arriesgue producción.

## 2. Antes de modificar
- Inspeccionar el estado real (código, tests, migraciones, docs afectadas) antes de tocar nada.
- Cargar solo el contexto de la tarea puntual; no releer todo el repo por defecto.
- No modificar `services/api/migrations/` ya aplicadas. Cambios de esquema van en una
  migración nueva.

## 3. Jerarquía de intención (distinguir siempre)
1. **Requisito obligatorio**: pedido explícito del usuario.
2. **Decisión aprobada**: elección ya confirmada (stack, librería, enfoque).
3. **Opción no aprobada**: algo mencionado o explorado sin confirmación.
No tratar (3) como (1) o (2). Si no fue confirmado, preguntar o presentarlo como propuesta
aparte, no implementarlo.

## 4. Alcance
- Priorizar solo requisitos vigentes + decisiones explícitas ya aprobadas.
- No agregar funcionalidades, refactors o "mejoras" no pedidas; proponerlas aparte.
- No agregar dependencias nuevas sin justificar en una línea qué requisito cubren.

## 5. Cómo evaluar cada cambio
Resumir antes de codear: **Requisito** (qué pide) · **Impacto** (qué workspace/módulo toca) ·
**Riesgo** (qué puede romperse: auth, roles, plan free/premium, datos de CV, despliegue,
cobros) · **Prueba** (cómo se verifica).

## 6. Ejecución
- Cambios pequeños y verificables: un requisito por cambio, fácil de revisar y revertir.
- Preservar código y decisiones existentes del usuario; no reformatear código no relacionado.
- TypeScript estricto sin `any`. Backend Python async en toda ruta de I/O; nada bloqueante
  en el event loop.
- Identificadores/APIs/nombres de archivo en inglés; comentarios en español solo si aclaran
  intención o un caso borde no obvio.

## 7. Tests y documentación
- Todo comportamiento nuevo o modificado necesita test (unitario o de integración según
  workspace).
- Actualizar solo la documentación directamente afectada.
- Una función está terminada solo con: código + tests + documentación relacionada + evidencia
  de que funciona. Sin alguno de los cuatro, no está terminada.

## 8. Delegación a subagentes
- Delegar solo si la subtarea es independiente y mejora tiempo o calidad real.
- Sintetizar y verificar (código, tests o evidencia) todo resultado de un subagente antes de
  integrarlo. No integrar output no verificado.

## 9. Comunicación
- Explicar brevemente el porqué de cada cambio importante (requisito + decisión tomada).
- Todo el trabajo debe ser defendible por el usuario sin asistencia de IA.
- No presentar una opción explorada como si fuera una decisión ya tomada.

## 10. Referencias
- Stack backend, esquema de error y comandos: `services/api/AGENTS.md`.
- Stack frontend, rutas y convenciones de componentes: `apps/web/AGENTS.md`.
