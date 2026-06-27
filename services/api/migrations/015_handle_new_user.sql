-- Migration 015: Create auth trigger for new Supabase users.
-- Date: 2026-06-26

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public AS $$
BEGIN
INSERT INTO public.users (supabase_uid, email, full_name)
VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name')
ON CONFLICT (supabase_uid) DO NOTHING;
INSERT INTO public.master_profiles (user_id)
SELECT id FROM public.users WHERE supabase_uid = NEW.id
ON CONFLICT (user_id) DO NOTHING;
RETURN NEW;
END; $$;

CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
