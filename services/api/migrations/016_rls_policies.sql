-- Migration 016: Enable RLS and create owner policies for all tables.
-- Date: 2026-06-26

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;
ALTER TABLE educations ENABLE ROW LEVEL SECURITY;
ALTER TABLE languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE certifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE rejected_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_kits ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_scrape_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_owner_policy ON users
FOR ALL USING (supabase_uid = auth.uid())
WITH CHECK (supabase_uid = auth.uid());

CREATE POLICY master_profiles_owner_policy ON master_profiles
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));

CREATE POLICY uploaded_documents_owner_policy ON uploaded_documents
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));

CREATE POLICY skills_owner_policy ON skills
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY experiences_owner_policy ON experiences
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY educations_owner_policy ON educations
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY languages_owner_policy ON languages
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY certifications_owner_policy ON certifications
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY rejected_skills_owner_policy ON rejected_skills
FOR ALL USING (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()))
WITH CHECK (profile_id IN (SELECT mp.id FROM master_profiles mp JOIN users u ON u.id = mp.user_id WHERE u.supabase_uid = auth.uid()));

CREATE POLICY job_descriptions_owner_policy ON job_descriptions
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));

CREATE POLICY job_matches_owner_policy ON job_matches
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));

CREATE POLICY interview_kits_owner_policy ON interview_kits
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));

CREATE POLICY linkedin_scrape_cache_owner_policy ON linkedin_scrape_cache
FOR ALL USING (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()))
WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_uid = auth.uid()));
