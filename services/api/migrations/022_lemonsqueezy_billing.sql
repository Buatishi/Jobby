-- Migración 022: Agregar metadata de billing para Lemon Squeezy.
-- Date: 2026-07-03
-- Mantiene columnas legacy de pagos en desuso para no perder datos históricos.

ALTER TABLE users
ADD COLUMN IF NOT EXISTS payment_provider TEXT DEFAULT 'lemonsqueezy',
ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_id TEXT,
ADD COLUMN IF NOT EXISTS lemonsqueezy_subscription_id TEXT,
ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'none',
ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ;
