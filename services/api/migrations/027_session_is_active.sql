-- Migración 027: Verificar que la sesión de un token siga abierta.
-- Date: 2026-09-24
--
-- La consigna (3.4.2) pide que cerrar sesión invalide efectivamente el acceso. La API valida
-- la firma y el vencimiento del token localmente, así que un token de una sesión cerrada
-- seguiría sirviendo hasta vencer (una hora). Con esta función la API comprueba, en cada
-- pedido, que la sesión del token (`session_id`) exista todavía en Supabase Auth: cerrar
-- sesión la borra y el token deja de servir al instante.
--
-- SECURITY DEFINER porque `auth.sessions` no es accesible para los roles de la API; solo la
-- ejecuta la clave de servicio y devuelve un booleano, nunca datos de la sesión.

CREATE OR REPLACE FUNCTION public.session_is_active(p_session_id UUID, p_supabase_uid UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM auth.sessions AS s
    WHERE s.id = p_session_id
      AND s.user_id = p_supabase_uid
      AND (s.not_after IS NULL OR s.not_after > now())
  );
$$;

REVOKE ALL ON FUNCTION public.session_is_active(UUID, UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.session_is_active(UUID, UUID) TO service_role;
