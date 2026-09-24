# Pendientes de producto y frontend

Estado: 2026-09-21, actualizado el 2026-09-23. Origen: auditoría del frontend en vivo y en el código, y evaluación de
propuestas de redes sociales. Nada de esto está implementado salvo lo marcado como hecho;
cada ítem necesita aprobación antes de programarse (`AGENTS.md`, sección 3).

## 1. Hecho

| ID | Qué | Referencia |
|---|---|---|
| F1 | Arranque en frío de la API: pre-calentamiento al abrir la web, reintento de GET y aviso de demora | Decisión 14, `docs/operacion/arranque-en-frio.md` |
| M1 | Tareas en segundo plano en modo local (análisis, match y kits) | Decisión 15, `docs/operacion/modo-local-de-tareas.md` |
| F9 | `/og-image.png` salía con 200 y 0 bytes: Satori exige `display: flex` en todo `<div>` cuyo contenido no sea solo texto, y la pista de cada barra no lo tenía. Corregido el 2026-09-23, con un test que genera la imagen y valida el PNG | `apps/web/src/app/og-image.png/route.test.ts` |

## 2. Frontend

| ID | Prioridad | Problema y evidencia | Beneficio y cómo se valida | Riesgo y esfuerzo | Áreas |
|---|---|---|---|---|---|
| F2 | Alta | No existe ninguna página `not-found`, `error`, `global-error` ni `loading`: se ven las pantallas por defecto de Next | Marca coherente y salida de errores. Validar con una URL inexistente y un error forzado | Bajo, S | Cuatro archivos nuevos en `apps/web/src/app` |
| F3 | Media | 161 colores hex fijos en 30 archivos y dos verdes de marca (`#0F6E56` en 83 usos, `#007a5e` en 11), aunque `AGENTS.md` pide tokens | Consistencia y base para temas. Validar con un grep sin hex y capturas antes y después | Medio (toca todas las pantallas), M | `globals.css`, `tailwind.config.ts`, sidebar, dashboard, login, registro |
| F4 | Media | Sin toasts ni skeletons; solo 4 componentes shadcn (`badge`, `button`, `card`, `tooltip`) | Confirmaciones y estados de carga claros. Validar con pruebas manuales por flujo | Bajo–medio, M; una dependencia posible (toasts) a justificar | `apps/web/components/ui`, wizard |
| F5 | Media | Solo el layout raíz define `metadata`; sin título ni descripción por página | Mejor SEO y pestañas legibles. Validar inspeccionando `<title>` y con Lighthouse | Bajo, S | Páginas públicas de `apps/web/src/app` |
| F6 | Media | 15 atributos `aria` y 1 `sr-only`; el titular de la landing tardaba más de 3 s en tomar su color final (observación puntual) | Accesibilidad. Validar con Lighthouse o axe | Bajo, S–M | Componentes compartidos y landing |
| F7 | Baja | Modo oscuro forzado a claro en `globals.css` (`color-scheme: light` y un bloque `prefers-color-scheme: dark` que repite los valores claros); depende de F3 | Comodidad; no es requisito de la consigna | Medio, M–L | `globals.css`, `layout.tsx`, `lib/utils/score-colors.ts` |
| P1 | Media | `next.config.ts` cae a `https://jobby-fp0r.onrender.com` (API duplicada) si faltan las variables de entorno | Evita apuntar en silencio a un servicio que se va a suspender. Validar con un build sin variables | Bajo, S | `apps/web/next.config.ts` |
| P2 | Alta | La interfaz fija el plan en `free` (`(app)/layout.tsx`), así que un usuario premium vería funciones bloqueadas | Plan real en la UI. Validar con un usuario premium de prueba | Medio, M | `apps/web/src/app/(app)/layout.tsx`, `components/app-shell.tsx` |
| P3 | Media | No hay ningún control de cierre de sesión en la interfaz | Cierre de sesión explícito. Validar iniciando y cerrando sesión | Bajo, S | `components/app-sidebar.tsx` |

## 3. Backend y producto

| ID | Prioridad | Problema y evidencia | Beneficio y cómo se valida | Riesgo y esfuerzo | Áreas |
|---|---|---|---|---|---|
| B1 | Alta | El análisis por URL usa Playwright, pero el `Dockerfile` de la API no instala Chromium ni hay respaldo sin navegador: es probable que falle en producción (inferencia, no probado para no ejecutar análisis reales) | La función "pegar una URL" de la consigna. Validar con una prueba controlada tras el cambio | Alto (imagen más pesada y 512 MB de RAM); decidir entre instalarlo o limitar a texto pegado | `services/api/Dockerfile`, `services/api/app/services/scraper/` |

## 4. Herramientas evaluadas

| Herramienta | Decisión | Motivo |
|---|---|---|
| Skill `frontend-design` (Anthropic, Apache-2.0) | Instalada a nivel usuario el 2026-09-21 | Solo instrucciones de diseño. Usarla únicamente en una pasada visual deliberada e indicar que se respeten shadcn y los tokens de color de `AGENTS.md` |
| Graphify (Apache-2.0) | No instalada | Sus hooks ejecutan un comando en cada búsqueda o lectura y su skill instala paquetes de PyPI sin fijar versión; el ahorro de tokens no aplica a un repo de unas 18 mil líneas |
| Manus | No recomendada | Servicio de pago por créditos, patrocinado en el reel, sin relación con el repositorio |
| `claude-code-action` (GitHub) | No ahora | Requiere API key con costo aparte y permisos amplios de GitHub; las Actions están bloqueadas por facturación |
