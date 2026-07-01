-- Migración 020: Endurecimiento de seguridad para warnings de Supabase Security Advisor.
-- Date: 2026-07-01
-- Corrige search_path de funciones, restringe ejecución directa de funciones
-- SECURITY DEFINER y mueve pgvector a un schema dedicado.

-- 1. Corrige el warning de search_path mutable en compute_completeness().
CREATE OR REPLACE FUNCTION public.compute_completeness(p_id UUID)
RETURNS SMALLINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE score INT := 0; p RECORD;
BEGIN
SELECT * INTO p FROM master_profiles WHERE id = p_id;
IF p.headline IS NOT NULL AND p.headline != '' THEN score := score + 8; END IF;
IF p.summary IS NOT NULL AND p.summary != '' THEN score := score + 8; END IF;
IF p.target_role IS NOT NULL THEN score := score + 5; END IF;
IF p.target_seniority IS NOT NULL THEN score := score + 4; END IF;
IF p.work_modality IS NOT NULL THEN score := score + 3; END IF;
IF (SELECT COUNT(*) FROM experiences WHERE profile_id=p_id) >= 1
THEN score := score + 12; END IF;
IF (SELECT COUNT(*) FROM skills WHERE profile_id=p_id AND confirmed=true) >= 3
THEN score := score + 10; END IF;
IF (SELECT COUNT(*) FROM educations WHERE profile_id=p_id) >= 1
THEN score := score + 8; END IF;
IF (SELECT COUNT(*) FROM languages WHERE profile_id=p_id) >= 1
THEN score := score + 4; END IF;
IF EXISTS(SELECT 1 FROM uploaded_documents
WHERE profile_id=p_id AND type='cv' AND status='done')
THEN score := score + 20; END IF;
IF EXISTS(SELECT 1 FROM uploaded_documents
WHERE profile_id=p_id AND type='linkedin' AND status='done')
THEN score := score + 12; END IF;
IF p.linkedin_url IS NOT NULL AND p.linkedin_url != ''
THEN score := score + 6; END IF;
RETURN LEAST(score, 100);
END;
$$;

REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM public;
REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM anon;

-- 2. Evita la ejecución manual del trigger function desde roles cliente.
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM public;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM anon;

-- 3. Mueve pgvector fuera de public. Las columnas vector e índices HNSW
-- existentes siguen referenciando los mismos objetos; solo cambia el schema.
CREATE SCHEMA IF NOT EXISTS extensions;
ALTER EXTENSION vector SET SCHEMA extensions;

-- Mantiene resolubles futuras referencias no calificadas como vector(1536)
-- en la base actual, incluyendo bases locales que no se llamen "postgres".
DO $$
BEGIN
  EXECUTE format(
    'ALTER DATABASE %I SET search_path = public, extensions',
    current_database()
  );
END;
$$;
