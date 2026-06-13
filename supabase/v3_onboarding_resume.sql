-- Esona V3 Onboarding Resume Migration
-- Run this SQL in the Supabase Dashboard SQL Editor to update the database.

BEGIN;

-- Add onboarding_step to profiles table
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS onboarding_step integer DEFAULT 1;

COMMIT;
