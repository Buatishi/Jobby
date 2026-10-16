-- Migración 030: Mover pg_net al esquema `extensions`.
-- Date: 2026-10-16
--
-- La migración 029 hizo CREATE EXTENSION pg_net sin esquema y quedó en `public`: el Security
-- Advisor de Supabase avisa `extension_in_public` (la migración 020 ya había movido pgvector
-- por lo mismo). pg_net no se puede reubicar con ALTER EXTENSION: se la baja y se la vuelve a
-- crear en `extensions`. Sus funciones siguen en el esquema `net`, así que los trabajos de
-- pg_cron (`SELECT net.http_get(...)`) no cambian. La ventana sin extensión dura una
-- transacción; los trabajos corren cada 10 minutos.

DROP EXTENSION IF EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
