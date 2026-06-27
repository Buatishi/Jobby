-- Migration 003: Create uploaded documents table and unique CV indexes.
-- Date: 2026-06-26

CREATE TABLE uploaded_documents (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
type TEXT NOT NULL, -- 'cv' | 'linkedin'
cv_slot SMALLINT, -- 1 | 2 (solo para type='cv')
is_primary BOOLEAN NOT NULL DEFAULT FALSE,
storage_path TEXT NOT NULL,
original_filename TEXT,
mime_type TEXT,
file_size INTEGER,
status TEXT DEFAULT 'pending', -- pending|processing|done|failed
parsed_data JSONB,
error_msg TEXT,
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Maximo un CV primario por usuario.
CREATE UNIQUE INDEX idx_one_primary_cv
ON uploaded_documents(user_id)
WHERE type = 'cv' AND is_primary = TRUE;

-- Maximo 2 CVs por usuario (slots 1 y 2).
CREATE UNIQUE INDEX idx_cv_slot_per_user
ON uploaded_documents(user_id, cv_slot)
WHERE type = 'cv';
