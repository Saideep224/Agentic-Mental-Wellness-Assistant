-- Esona V2 Database Schema Migration
-- Run this SQL in the Supabase Dashboard SQL Editor to update the production database.

BEGIN;

-- 1. Standardize chat_messages table to use 'emotion' column
ALTER TABLE public.chat_messages ADD COLUMN IF NOT EXISTS emotion text;

-- If 'emotion_detected' already has data, migrate it to the new 'emotion' column
UPDATE public.chat_messages 
SET emotion = emotion_detected 
WHERE emotion IS NULL AND emotion_detected IS NOT NULL;

-- 2. Create the emotion_logs table for tracking user emotional state
CREATE TABLE IF NOT EXISTS public.emotion_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles(user_id) ON DELETE CASCADE,
  message text NOT NULL,
  detected_emotion text NOT NULL,
  confidence_score double precision NOT NULL,
  timestamp timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS and add Row Level Security policies for emotion_logs
ALTER TABLE public.emotion_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "emotion_logs_select_own" ON public.emotion_logs;
CREATE POLICY "emotion_logs_select_own" ON public.emotion_logs 
  FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "emotion_logs_insert_own" ON public.emotion_logs;
CREATE POLICY "emotion_logs_insert_own" ON public.emotion_logs 
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT ON public.emotion_logs TO authenticated;

-- 3. Update the memories table schema
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS memory_type text;
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS memory_content text;
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS importance_score double precision;
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.memories ADD COLUMN IF NOT EXISTS behavior_patterns jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Migrate existing data from 'memory_summary' to 'memory_content' if needed
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema='public' AND table_name='memories' AND column_name='memory_summary'
  ) THEN
    UPDATE public.memories 
    SET memory_content = memory_summary 
    WHERE memory_content IS NULL;
  END IF;
END $$;

-- Add updated_at trigger if not already present
DROP TRIGGER IF EXISTS set_memories_updated_at ON public.memories;
CREATE TRIGGER set_memories_updated_at BEFORE UPDATE ON public.memories 
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;
