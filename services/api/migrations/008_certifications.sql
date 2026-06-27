-- Migration 008: Create certifications table.
-- Date: 2026-06-26

CREATE TABLE certifications (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
name TEXT NOT NULL,
issuer TEXT,
issued_at DATE,
expires_at DATE,
credential_url TEXT,
created_at TIMESTAMPTZ DEFAULT NOW()
);
