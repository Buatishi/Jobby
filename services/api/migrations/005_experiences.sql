-- Migration 005: Create experiences table.
-- Date: 2026-06-26

CREATE TABLE experiences (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
profile_id UUID NOT NULL REFERENCES master_profiles(id) ON DELETE CASCADE,
company TEXT NOT NULL,
title TEXT NOT NULL,
started_at DATE,
ended_at DATE,
is_current BOOLEAN DEFAULT FALSE,
description TEXT,
achievements TEXT[],
created_at TIMESTAMPTZ DEFAULT NOW()
);
