-- Migration 013: Create LinkedIn scrape cache table.
-- Date: 2026-06-26

CREATE TABLE linkedin_scrape_cache (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
linkedin_url TEXT NOT NULL,
raw_data JSONB,
scraped_at TIMESTAMPTZ DEFAULT NOW(),
expires_at TIMESTAMPTZ,
created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_linkedin_scrape_cache_user_url
ON linkedin_scrape_cache(user_id, linkedin_url);
