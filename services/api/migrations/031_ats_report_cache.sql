-- Migración 031: Guardar el último reporte ATS de cada puesto.
-- Date: 2026-10-20
--
-- Abrir un reporte ATS rehacía todo el cálculo cada vez (6 a 9 segundos): pedía las palabras
-- clave del puesto a la IA (y salían distintas en cada apertura), pedía los vectores a OpenAI
-- y gastaba una de las 5 consultas diarias del plan gratuito. Ahora la API guarda el último
-- reporte de cada puesto en `ats_reports` y lo sirve mientras coincidan el CV principal para
-- el que se calculó (documento y huella de su `parsed_data`) y la versión del algoritmo; si el
-- CV cambia, se recalcula. Las palabras clave del puesto son las de ese reporte
-- (`keyword_matches[].keyword`): al recalcular se reutilizan, así que no cambian entre
-- aperturas ni cuando cambia el CV.
--
-- ORDEN SEGURO: aplicar esta migración ANTES de desplegar el código. El código nuevo también
-- funciona si todavía no está aplicada (no encuentra nada guardado, calcula en cada apertura
-- y gasta la consulta, como hasta ahora), y la migración no afecta al código viejo: solo
-- agrega una tabla que nadie lee.
--
-- Va en una tabla aparte y no en columnas de `job_descriptions` porque el modelo
-- `JobDescription` de la API devuelve las columnas que no conoce, y el reporte lleva
-- fragmentos del CV (`matched_text`) que no deben salir en `GET /jobs`.

CREATE TABLE IF NOT EXISTS public.ats_reports (
  job_id UUID PRIMARY KEY REFERENCES public.job_descriptions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  -- Marcas de qué CV y qué algoritmo produjeron el reporte. No son claves foráneas: son
  -- la huella con la que la API decide si el reporte sigue valiendo.
  cv_document_id UUID NOT NULL,
  cv_fingerprint TEXT NOT NULL,
  report_version SMALLINT NOT NULL,
  ats_score SMALLINT NOT NULL,
  keyword_matches JSONB NOT NULL,
  format_issues JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Como en la 024: la API filtra por la persona dueña y el borrado en cascada recorre esta
-- columna. La clave primaria ya indexa `job_id`.
CREATE INDEX IF NOT EXISTS idx_ats_reports_user_id ON public.ats_reports (user_id);

-- Mismo esquema de acceso que el resto (migraciones 016 y 025): la API usa la clave de
-- servicio y la clave pública no tiene ningún privilegio sobre la tabla.
ALTER TABLE public.ats_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ats_reports_owner_policy ON public.ats_reports;
CREATE POLICY ats_reports_owner_policy ON public.ats_reports
FOR ALL USING (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM public.users WHERE supabase_uid = auth.uid()));

REVOKE ALL ON public.ats_reports FROM anon, authenticated;
