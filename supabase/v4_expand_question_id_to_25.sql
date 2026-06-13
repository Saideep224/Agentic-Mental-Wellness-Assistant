-- ============================================================
-- Migration: v4_expand_question_id_to_25
-- Purpose: Expand user_question_answers question_id CHECK constraint
--          from (1..20) to (1..25) to support the 5 new background
--          personalization questions prepended to the onboarding flow.
-- Run this in: Supabase SQL Editor (once)
-- ============================================================

-- Drop the old constraint
ALTER TABLE public.user_question_answers
  DROP CONSTRAINT IF EXISTS user_question_answers_question_id_check;

-- Add the updated constraint allowing question_id 1 to 25
ALTER TABLE public.user_question_answers
  ADD CONSTRAINT user_question_answers_question_id_check
  CHECK (question_id BETWEEN 1 AND 25);
