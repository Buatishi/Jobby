-- Migración 023: Restaurar set_primary_uploaded_document en la base de producción.
-- Date: 2026-09-22
-- La migración 018 creó esta función, pero no quedó aplicada en el proyecto productivo:
-- el endpoint PATCH /profiles/documents/{id}/set-primary la invoca por RPC y fallaba.
-- Se repite tal cual (CREATE OR REPLACE), así que es segura de aplicar más de una vez.

CREATE OR REPLACE FUNCTION public.set_primary_uploaded_document(
  p_user_id UUID,
  p_document_id UUID
)
RETURNS uploaded_documents
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  selected_document uploaded_documents;
BEGIN
  SELECT *
  INTO selected_document
  FROM uploaded_documents
  WHERE id = p_document_id
    AND user_id = p_user_id
    AND type = 'cv'
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or not a CV';
  END IF;

  UPDATE uploaded_documents
  SET is_primary = FALSE,
      updated_at = NOW()
  WHERE user_id = p_user_id
    AND type = 'cv'
    AND is_primary = TRUE;

  UPDATE uploaded_documents
  SET is_primary = TRUE,
      status = 'pending',
      updated_at = NOW()
  WHERE id = p_document_id
  RETURNING * INTO selected_document;

  RETURN selected_document;
END;
$$;

-- Misma restricción que el resto de las funciones SECURITY DEFINER (migraciones 020 y 021):
-- solo la API, con la clave de servicio, puede ejecutarla.
REVOKE EXECUTE ON FUNCTION public.set_primary_uploaded_document(UUID, UUID) FROM public;
REVOKE EXECUTE ON FUNCTION public.set_primary_uploaded_document(UUID, UUID) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.set_primary_uploaded_document(UUID, UUID) FROM anon;
