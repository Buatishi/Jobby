-- Migración 025: Cerrar el acceso directo a las tablas con la clave pública.
-- Date: 2026-09-23
--
-- Supabase da por defecto todos los privilegios sobre las tablas de `public` a los roles
-- `anon` y `authenticated`, y las políticas RLS solo exigían que la fila fuera propia. Con
-- la clave pública y su propio token, cualquier persona podía escribir sus filas por la API
-- REST de Supabase sin pasar por la API de Jobby: por ejemplo, cambiarse el plan a premium
-- en `users`, o registrar en `uploaded_documents` la ruta del CV de otra persona y pedir que
-- se procese. Se reprodujo en el proyecto de pruebas.
--
-- La web solo usa Supabase para Auth y para subir el PDF al Storage (con sus propias
-- políticas); todas las lecturas y escrituras de datos pasan por la API, que usa la clave de
-- servicio. Por eso esos dos roles pierden todos los privilegios sobre las tablas actuales y
-- sobre las que se creen después. Las políticas RLS quedan como segunda barrera.

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL ON TABLES FROM anon, authenticated;
