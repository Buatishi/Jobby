-- Migration 001: Create public users table.
-- Date: 2026-06-26

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
supabase_uid UUID UNIQUE NOT NULL REFERENCES auth.users(id),
email TEXT NOT NULL,
full_name TEXT,
tier TEXT NOT NULL DEFAULT 'free', -- 'free' | 'premium'
stripe_customer_id TEXT,
created_at TIMESTAMPTZ DEFAULT NOW(),
updated_at TIMESTAMPTZ DEFAULT NOW()
);
