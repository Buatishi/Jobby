-- Migración 029: Despertar la API gratuita de día con pg_cron + pg_net.
-- Date: 2026-10-16
--
-- Render duerme la API Free a los 15 min sin tráfico y el primer pedido espera ~40 s
-- (docs/operacion/arranque-en-frio.md). El workflow keep-alive.yml la consulta «cada 10
-- minutos», pero GitHub retrasa y saltea los cron de repos gratuitos: entre el 2026-10-14 y el
-- 2026-10-15 corrió cada ~3 horas, así que la API dormía casi todo el día. pg_cron corre a la
-- hora exacta (probado en jobby-test el 2026-10-16: ejecuciones a los :00 de cada minuto y
-- 200 de /health con pg_net).
--
-- Mismo horario que el workflow: 08:00 a 23:50 hora de Buenos Aires (UTC-3), es decir
-- 11:00 a 23:50 y 00:00 a 02:50 UTC. Con ~16 h por día usa cerca de 500 de las 750 horas
-- gratis del mes. El pedido es a /health: público, sin credenciales y sin tocar la base.
--
-- La URL es la pública de la API (figura en el README y en docs/06). Si cambia el servicio,
-- se reprograma con cron.schedule (el nombre del trabajo actualiza el existente).

CREATE EXTENSION IF NOT EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
  'keep-api-awake-utc-11-23',
  '*/10 11-23 * * *',
  $job$SELECT net.http_get(
    url := 'https://jobmatch-api-9xel.onrender.com/health',
    timeout_milliseconds := 90000
  )$job$
);

SELECT cron.schedule(
  'keep-api-awake-utc-00-02',
  '*/10 0-2 * * *',
  $job$SELECT net.http_get(
    url := 'https://jobmatch-api-9xel.onrender.com/health',
    timeout_milliseconds := 90000
  )$job$
);

-- cron.job_run_details guarda una fila por ejecución (unas 100 por día) y no se limpia sola.
SELECT cron.schedule(
  'keep-api-awake-cleanup',
  '17 6 * * *',
  $job$DELETE FROM cron.job_run_details WHERE end_time < now() - interval '7 days'$job$
);
