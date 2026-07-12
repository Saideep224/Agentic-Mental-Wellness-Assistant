-- v6_expand_question_id_to_27.sql
-- Migration to expand user_question_answers check constraint range to 1..27 to support the new Age question.

ALTER TABLE public.user_question_answers
  DROP CONSTRAINT IF EXISTS user_question_answers_question_id_check;

ALTER TABLE public.user_question_answers
  ADD CONSTRAINT user_question_answers_question_id_check
  CHECK (question_id BETWEEN 1 AND 27);
