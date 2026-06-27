-- Migration 017: Create Storage bucket policies for user documents.
-- Date: 2026-06-26

INSERT INTO storage.buckets (id, name, public)
VALUES ('cv-documents', 'cv-documents', FALSE)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY cv_documents_select_own ON storage.objects
FOR SELECT USING (
  bucket_id = 'cv-documents'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY cv_documents_insert_own ON storage.objects
FOR INSERT WITH CHECK (
  bucket_id = 'cv-documents'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY cv_documents_update_own ON storage.objects
FOR UPDATE USING (
  bucket_id = 'cv-documents'
  AND auth.uid()::text = (storage.foldername(name))[1]
) WITH CHECK (
  bucket_id = 'cv-documents'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY cv_documents_delete_own ON storage.objects
FOR DELETE USING (
  bucket_id = 'cv-documents'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
