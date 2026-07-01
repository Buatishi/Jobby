-- Migración 021: Restringir ejecución directa de compute_completeness.
-- Date: 2026-07-01
-- Corrige warnings de Supabase Security Advisor para funciones SECURITY DEFINER
-- ejecutables por public y authenticated.

REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM public;
REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM authenticated;
REVOKE EXECUTE ON FUNCTION public.compute_completeness(UUID) FROM anon;
