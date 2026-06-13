-- Esona V3 User Profile personalization migration
-- Run this SQL in the Supabase Dashboard SQL Editor to update the production database.

BEGIN;

CREATE TABLE IF NOT EXISTS public.user_profile (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE REFERENCES public.profiles(user_id) ON DELETE CASCADE,
  name text,
  age text,
  profession text,
  student_year text,
  communication_style text,
  interests jsonb NOT NULL DEFAULT '[]'::jsonb,
  hobbies jsonb NOT NULL DEFAULT '[]'::jsonb,
  goals jsonb NOT NULL DEFAULT '[]'::jsonb,
  stress_triggers jsonb NOT NULL DEFAULT '[]'::jsonb,
  coping_mechanisms jsonb NOT NULL DEFAULT '[]'::jsonb,
  support_system text,
  sleep_habits text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS and add Row Level Security policies for user_profile
ALTER TABLE public.user_profile ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_profile_select_own" ON public.user_profile;
CREATE POLICY "user_profile_select_own" ON public.user_profile 
  FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_profile_insert_own" ON public.user_profile;
CREATE POLICY "user_profile_insert_own" ON public.user_profile 
  FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_profile_update_own" ON public.user_profile;
CREATE POLICY "user_profile_update_own" ON public.user_profile 
  FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_profile_delete_own" ON public.user_profile;
CREATE POLICY "user_profile_delete_own" ON public.user_profile 
  FOR DELETE TO authenticated USING (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_profile TO authenticated;

-- Add updated_at trigger if not already present
DROP TRIGGER IF EXISTS set_user_profile_updated_at ON public.user_profile;
CREATE TRIGGER set_user_profile_updated_at BEFORE UPDATE ON public.user_profile 
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;
