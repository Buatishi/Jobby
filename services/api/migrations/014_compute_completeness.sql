-- Migration 014: Create compute_completeness function.
-- Date: 2026-06-26

CREATE OR REPLACE FUNCTION compute_completeness(p_id UUID)
RETURNS SMALLINT AS $$
DECLARE score INT := 0; p RECORD;
BEGIN
SELECT * INTO p FROM master_profiles WHERE id = p_id;
IF p.headline IS NOT NULL AND p.headline != '' THEN score := score + 8; END IF;
IF p.summary IS NOT NULL AND p.summary != '' THEN score := score + 8; END IF;
IF p.target_role IS NOT NULL THEN score := score + 5; END IF;
IF p.target_seniority IS NOT NULL THEN score := score + 4; END IF;
IF p.work_modality IS NOT NULL THEN score := score + 3; END IF;
IF (SELECT COUNT(*) FROM experiences WHERE profile_id=p_id) >= 1
THEN score := score + 12; END IF;
IF (SELECT COUNT(*) FROM skills WHERE profile_id=p_id AND confirmed=true) >= 3
THEN score := score + 10; END IF;
IF (SELECT COUNT(*) FROM educations WHERE profile_id=p_id) >= 1
THEN score := score + 8; END IF;
IF (SELECT COUNT(*) FROM languages WHERE profile_id=p_id) >= 1
THEN score := score + 4; END IF;
IF EXISTS(SELECT 1 FROM uploaded_documents
WHERE profile_id=p_id AND type='cv' AND status='done')
THEN score := score + 20; END IF;
IF EXISTS(SELECT 1 FROM uploaded_documents
WHERE profile_id=p_id AND type='linkedin' AND status='done')
THEN score := score + 12; END IF;
IF p.linkedin_url IS NOT NULL AND p.linkedin_url != ''
THEN score := score + 6; END IF;
RETURN LEAST(score, 100);
END; $$ LANGUAGE plpgsql;
