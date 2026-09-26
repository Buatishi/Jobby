-- Migración 028: Crear el perfil maestro al insertar cualquier fila en users.
-- Date: 2026-09-26
--
-- El disparador de la migración 015 crea users y master_profiles al registrarse en Supabase
-- Auth, pero la API también inserta en users cuando el token trae una persona sin fila (por
-- ejemplo, si el disparador no existía cuando se registró). Hasta ahora la API cubría ese caso
-- consultando master_profiles en cada pedido autenticado, una ida y vuelta más a la base
-- (Decisión 23). Con este disparador la base garantiza el perfil en todos los caminos y la API
-- deja de verificarlo.

CREATE OR REPLACE FUNCTION public.create_master_profile_for_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.master_profiles (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.create_master_profile_for_user() FROM PUBLIC, anon, authenticated;

CREATE TRIGGER on_public_user_created
AFTER INSERT ON public.users
FOR EACH ROW EXECUTE FUNCTION public.create_master_profile_for_user();

-- Relleno: toda persona existente sin perfil recibe uno (en producción eran 0 al 2026-09-26).
INSERT INTO public.master_profiles (user_id)
SELECT u.id
FROM public.users AS u
WHERE NOT EXISTS (SELECT 1 FROM public.master_profiles AS p WHERE p.user_id = u.id)
ON CONFLICT (user_id) DO NOTHING;
