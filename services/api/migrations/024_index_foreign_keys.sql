-- Migración 024: Índices para las 15 claves foráneas que no tenían uno.
-- Date: 2026-09-23
--
-- Postgres no indexa solo las columnas de una clave foránea. La API filtra por estas
-- columnas en casi todas las consultas (el perfil o la persona dueña de cada fila) y los
-- borrados en cascada (baja de cuenta, borrado de un puesto) las recorren en cada tabla
-- hija: sin índice, cada una de esas operaciones lee la tabla entera.
--
-- Las tablas son chicas, así que CREATE INDEX sin CONCURRENTLY toma un bloqueo breve y
-- puede correr dentro de la transacción de la migración. IF NOT EXISTS la hace repetible.

CREATE INDEX IF NOT EXISTS idx_certifications_profile_id ON public.certifications (profile_id);
CREATE INDEX IF NOT EXISTS idx_educations_profile_id ON public.educations (profile_id);
CREATE INDEX IF NOT EXISTS idx_experiences_profile_id ON public.experiences (profile_id);
CREATE INDEX IF NOT EXISTS idx_interview_kits_job_id ON public.interview_kits (job_id);
CREATE INDEX IF NOT EXISTS idx_interview_kits_match_id ON public.interview_kits (match_id);
CREATE INDEX IF NOT EXISTS idx_interview_kits_profile_id ON public.interview_kits (profile_id);
CREATE INDEX IF NOT EXISTS idx_interview_kits_user_id ON public.interview_kits (user_id);
CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_id ON public.job_descriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_job_id ON public.job_matches (job_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_profile_id ON public.job_matches (profile_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_user_id ON public.job_matches (user_id);
CREATE INDEX IF NOT EXISTS idx_languages_profile_id ON public.languages (profile_id);
CREATE INDEX IF NOT EXISTS idx_rejected_skills_profile_id ON public.rejected_skills (profile_id);
CREATE INDEX IF NOT EXISTS idx_skills_profile_id ON public.skills (profile_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_documents_profile_id ON public.uploaded_documents (profile_id);
