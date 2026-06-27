-- Migration 006: Create educations table with HNSW vector index.
-- Date: 2026-06-26

CREATE TABLE educations (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
institution TEXT NOT NULL,
field_of_study TEXT,
degree_level TEXT, -- phd|master|bachelor|associate|technical|course|none
started_at DATE,
ended_at DATE,
is_ongoing BOOLEAN DEFAULT FALSE,
embedding vector(1536), -- embed(institution + field_of_study)
created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_educations_embedding ON educations
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
