-- Migración 026: Roles con permisos y métricas agregadas para administración.
-- Date: 2026-09-23
--
-- La consigna (3.4) pide al menos dos roles con permisos distintos, persistidos y consultados
-- como cualquier otro dato, sin comparar nombres en el código. Cada rol tiene permisos en
-- `role_permissions` y cada endpoint exige un permiso, nunca un nombre de rol. El rol de cada
-- persona vive en `users.role`; nadie puede cambiarlo desde el navegador porque la clave
-- pública no tiene privilegios sobre las tablas (migración 025).
--
-- El administrador ve solo métricas agregadas (conteos y promedios): nunca el contenido de un
-- CV ni datos personales de otra persona (AGENTS.md). Rol (user/admin) y plan (free/premium)
-- son ejes independientes.

CREATE TABLE IF NOT EXISTS public.roles (
  id TEXT PRIMARY KEY,
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.role_permissions (
  role_id TEXT NOT NULL REFERENCES public.roles (id) ON DELETE CASCADE,
  permission TEXT NOT NULL,
  PRIMARY KEY (role_id, permission)
);

INSERT INTO public.roles (id, description) VALUES
  ('user', 'Usa Jobby con sus propios datos'),
  ('admin', 'Además ve métricas agregadas; nunca CV ni datos personales de otras personas')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission) VALUES
  ('admin', 'metrics:read')
ON CONFLICT DO NOTHING;

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user' REFERENCES public.roles (id);

CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);

ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.roles, public.role_permissions FROM anon, authenticated;

-- Todas las métricas en una sola consulta. Los días son en UTC.
CREATE OR REPLACE FUNCTION public.admin_metrics()
RETURNS JSONB
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  WITH days AS (
    SELECT generate_series(current_date - 13, current_date, INTERVAL '1 day')::date AS day
  )
  SELECT jsonb_build_object(
    'generated_at', now(),
    'users', (
      SELECT jsonb_build_object(
        'total', count(*),
        'free', count(*) FILTER (WHERE tier = 'free'),
        'premium', count(*) FILTER (WHERE tier = 'premium'),
        'new_last_7_days', count(*) FILTER (WHERE created_at >= now() - INTERVAL '7 days'),
        'new_last_30_days', count(*) FILTER (WHERE created_at >= now() - INTERVAL '30 days')
      )
      FROM users
    ),
    'cvs', (
      SELECT jsonb_build_object(
        'total', count(*),
        'done', count(*) FILTER (WHERE status = 'done'),
        'failed', count(*) FILTER (WHERE status = 'failed'),
        'in_progress', count(*) FILTER (WHERE status NOT IN ('done', 'failed'))
      )
      FROM uploaded_documents
      WHERE type = 'cv'
    ),
    'jobs', (
      SELECT jsonb_build_object(
        'total', count(*),
        'last_7_days', count(*) FILTER (WHERE created_at >= now() - INTERVAL '7 days')
      )
      FROM job_descriptions
    ),
    'matches', (
      SELECT jsonb_build_object(
        'total', count(*),
        'last_7_days', count(*) FILTER (WHERE created_at >= now() - INTERVAL '7 days'),
        'average_score', round(avg(match_score))::int,
        'rated', count(user_rating),
        'average_rating', round(avg(user_rating)::numeric, 1)
      )
      FROM job_matches
    ),
    'interview_kits', (
      SELECT jsonb_build_object(
        'total', count(*),
        'done', count(*) FILTER (WHERE status = 'done'),
        'failed', count(*) FILTER (WHERE status = 'failed')
      )
      FROM interview_kits
    ),
    'daily_activity', (
      SELECT jsonb_agg(
        jsonb_build_object(
          'day', d.day,
          'cvs', (SELECT count(*) FROM uploaded_documents u WHERE u.type = 'cv' AND u.created_at::date = d.day),
          'jobs', (SELECT count(*) FROM job_descriptions j WHERE j.created_at::date = d.day),
          'matches', (SELECT count(*) FROM job_matches m WHERE m.created_at::date = d.day)
        )
        ORDER BY d.day
      )
      FROM days d
    )
  );
$$;

REVOKE ALL ON FUNCTION public.admin_metrics() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_metrics() TO service_role;
