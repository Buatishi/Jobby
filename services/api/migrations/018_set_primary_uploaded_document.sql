-- Migration 018: Create atomic primary CV switch function.
-- Date: 2026-06-27

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
