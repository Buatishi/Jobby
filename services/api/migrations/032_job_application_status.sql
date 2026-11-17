-- Migración 032: estado de postulación de cada puesto.
ALTER TABLE public.job_descriptions
  ADD COLUMN IF NOT EXISTS application_status TEXT NOT NULL DEFAULT 'saved'
  CHECK (application_status IN ('saved', 'applied', 'interview', 'offer', 'rejected'));