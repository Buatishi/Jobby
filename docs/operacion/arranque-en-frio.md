# Arranque en frío y suspensión por inactividad

Estado: vigente desde 2026-09-21 (Decisión 14 de `DECISIONS.md`), con la consulta periódica
de día sumada el 2026-09-25. Costo: USD 0.

## 1. Problema

La API corre en Render con el plan **Free**. Render duerme un servicio Free que pasa
15 minutos sin tráfico entrante y lo despierta con el siguiente pedido. Ese primer pedido
espera el arranque completo.

Mediciones del 2026-09-21 sobre `/health` (respuesta fija, sin base de datos ni IA):

| Situación | Tiempo de respuesta |
|---|---|
| Primer pedido tras estar dormida | **42,3 s** |
| Segundo pedido (ya despierta) | 0,24 s |
| Primera llamada 45 s después de abrir la web (con pre-calentamiento) | **0,245 s** |
| Pedido a través del dominio público (proxy de Vercel) con la API dormida | 43,5 s, HTTP 200 |
| Primera llamada directa 50 s después de abrir la web pública | **0,28 s** (la API duplicada `Jobby`, usada como control y sin visita, tardó 42,7 s) |

Los logs de Render muestran que su propio health check llama a `/health` cada 5 s mientras
el servicio corre y, aun así, el servicio estaba dormido: ese chequeo no cuenta como
tráfico entrante (inferencia; la documentación de Render no lo aclara).

Otros dos servicios del stack también se suspenden por inactividad y tienen consecuencias
distintas:

| Servicio | Regla documentada | Consecuencia | Mitigación |
|---|---|---|---|
| Render Free | Se duerme a los 15 min sin tráfico; 750 horas gratis por workspace y mes; si se agotan, suspende **todos** los servicios Free hasta el mes siguiente ([doc](https://render.com/docs/free)) | Primer pedido de ~42 s | Este documento |
| Supabase Free | Pausa el proyecto con poca actividad de base de datos en 7 días; aviso por mail una semana antes; se restaura hasta 90 días después ([doc](https://supabase.com/docs/guides/platform/free-project-pausing)) | Auth y datos no disponibles hasta reanudar | Regla operativa de la sección 5 |
| Upstash Redis Free | Se archiva tras 30 días o más sin actividad, con aviso y respaldo ([FAQ](https://upstash.com/docs/redis/help/faq)) | Cola y limitador no disponibles hasta restaurar | Regla operativa de la sección 5 |

## 2. Solución adoptada

Tres piezas en el frontend, sin servicios externos (`apps/web/lib/api/cold-start.ts`):

1. **Pre-calentamiento por intención de uso.** Al abrir cualquier página, el navegador hace
   un `GET /api/backend/health` sin credenciales ni datos, una vez cada 10 minutos por
   pestaña (registro en `sessionStorage`). La API despierta mientras la persona lee la
   landing o inicia sesión. Solo consume horas gratis cuando hay visitas reales.
2. **Reintento de los GET.** Si un GET (o la conexión SSE de `/tasks`) falla por error de
   red o responde 502, 503 o 504, se reintenta con esperas de 1, 2, 4, 8, 15 y 20 s. Los
   POST, PATCH y DELETE **nunca** se reintentan, para no duplicar acciones.
3. **Aviso de espera.** Si un pedido tarda más de 4 s aparece un aviso accesible
   (`role="status"`): "Seguimos trabajando en tu pedido… puede demorar hasta un minuto".
   El texto es genérico a propósito: también se muestra ante una demora que no es de
   arranque.

El componente `ColdStartNotice` (`apps/web/components/cold-start-notice.tsx`) está montado
en el layout raíz, así que cubre también a quien entra directo a una pantalla interna.

Desde el 2026-09-25 hay una cuarta pieza, fuera de la web:

4. **Consulta periódica de día.** El workflow `.github/workflows/keep-alive.yml` pide
   `/health` cada 10 minutos de 8 a 24 (hora de Buenos Aires), así la API no llega a dormirse
   en el horario de uso. De noche duerme y la cubren las tres piezas anteriores. Es posible
   porque `jobmatch-api` quedó como el único servicio gratis activo del workspace: despierta
   unas 16 horas por día, usa cerca de 500 de las 750 horas del mes. En la pestaña Actions
   estas corridas aparecen junto a las del pipeline: para ver el pipeline, filtrar por el
   workflow «CI».

## 3. Alternativas evaluadas

| Opción | Costo real | Motivo |
|---|---|---|
| Monitor externo (UptimeRobot) cada 5 min | USD 0, pero 720 a 744 de las 750 horas | Descartada como principal: deja 6 a 30 horas para `Jobby` y `Dardo-Audio`; si se agotan Render suspende todo. `/health` no toca la base, así que no evita la pausa de Supabase. Sus términos permiten uso comercial ([política](https://uptimerobot.com/terms-fair-use/)). |
| Health check nativo de Render | USD 0 | No evita el sueño (observado en logs). |
| Cron job de Render | Mínimo USD 1/mes ([doc](https://render.com/docs/cronjobs)) | Costo real. |
| GitHub Actions programado | USD 0 | Descartado el 2026-09-21 (cuenta bloqueada y tres servicios gratis compartiendo las horas). **Adoptado el 2026-09-25**, solo de día, cuando esas dos condiciones cambiaron. |
| Optimizar imagen o imports | USD 0 | Uvicorn arranca unos 39 s después del pedido; no se puede separar plataforma de imports. No se justifica sin medir. |
| Worker o cola | USD 0 a 7 | No resuelve: el encolado ocurre dentro de la API dormida. |
| Render Starter (siempre despierta) | USD 7/mes, por segundo | Único arreglo total. Queda para evaluar ([precios](https://render.com/pricing)). |

## 4. Límites

- No evita reinicios ni deploys de Render.
- Si un GET falla por un motivo distinto de puerta de enlace (por ejemplo 500), no se
  reintenta: el error se muestra enseguida.
- Un POST enviado justo con la API dormida puede fallar; el pre-calentamiento al abrir la
  web hace que sea poco probable.
- En una build autoalojada (`next start`) el proxy de Next corta a los 30 s con un 500
  (medido el 2026-09-21); el pedido de pre-calentamiento falla, pero la API igual despierta.
- El proxy de Vercel, en cambio, **espera** al arranque: medido el 2026-09-21 a las 16:38 UTC,
  un pedido a través de `jobbyweb.vercel.app` con la API dormida devolvió 200 tras 43,5 s.
  Sin pre-calentamiento un pedido real también terminaría bien, pero después de esa espera;
  el aviso de demora y el reintento son la red de seguridad ante otros cortes.

## 5. Reglas operativas

- **Supabase:** entrar a la app o al panel de Supabase al menos una vez cada pocos días.
  Basta con unas pocas consultas al día. Si llega el mail de aviso de pausa, entrar al
  panel de inmediato. Pro (USD 25/mes) supera el presupuesto de USD 20/mes.
- **Upstash:** no pasar 30 días sin usar la app.
- **Día de la defensa y ensayos:** abrir la web 10 minutos antes. Opcionalmente, crear un
  monitor de UptimeRobot (plan gratuito, 5 min) sobre `/health` de la API durante 24 a
  48 h y borrarlo después; en 48 h consume unas 48 de las 750 horas. Verificar antes que
  `Jobby` (servicio duplicado) esté suspendido.

## 6. Cómo validar

1. Dejar la API sin tráfico 15 minutos (o más) y comprobar que está dormida:
   `curl -s -o /dev/null -w "%{time_total}\n" https://jobmatch-api-9xel.onrender.com/health`
   debería tardar unos 40 s. **Ojo:** esta llamada la despierta.
2. Con la API dormida, abrir la web en una pestaña nueva, esperar 45 s y repetir el
   `curl`: debería responder en menos de 1 s.
3. Tras cada promoción en Vercel, con la API dormida, pedir
   `https://jobbyweb.vercel.app/api/backend/health` y registrar el estado HTTP y el tiempo
   (resultado del 2026-09-21: 200 en 43,5 s). Para confirmar a qué API apunta el frontend,
   probar las dos APIs 50 s después: la del frontend debe responder en menos de 1 s y la
   otra tardar unos 42 s.
4. Tests automáticos: `cd apps/web && pnpm test` (`lib/api/cold-start.test.ts`, 19 casos:
   TTL del pre-calentamiento, ausencia de credenciales, reintentos solo en GET, límites de
   reintento y aviso de demora).

## 7. Qué cambiaría esta decisión

- Si el proyecto necesita cero espera de forma permanente: Render Starter (USD 7/mes,
  prorrateado por segundo). Combinado con el modo local de tareas
  (`docs/operacion/modo-local-de-tareas.md`) serían USD 7 en total.
