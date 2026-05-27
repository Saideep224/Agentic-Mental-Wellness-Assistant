-- Esona Database Identity & Chat Persistence Standardization Migration
-- Standardizes foreign key constraints, drops legacy tables, and fixes RLS policies around auth.uid()

BEGIN;

-- 1. Deprecate legacy tables safely
DROP TABLE IF EXISTS public.chat_history CASCADE;
DROP TABLE IF EXISTS public.user_answers CASCADE;

-- 2. Drop old foreign key constraints
ALTER TABLE public.conversations DROP CONSTRAINT IF EXISTS conversations_user_id_fkey;
ALTER TABLE public.chat_messages DROP CONSTRAINT IF EXISTS chat_messages_user_id_fkey;
ALTER TABLE public.memories DROP CONSTRAINT IF EXISTS memories_user_id_fkey;
ALTER TABLE public.user_personality DROP CONSTRAINT IF EXISTS user_personality_user_id_fkey;
ALTER TABLE public.user_question_answers DROP CONSTRAINT IF EXISTS user_question_answers_user_id_fkey;

-- 3. Translate existing user_id values from profiles(id) to profiles(user_id)
-- This ensures we preserve conversation ownership, profile records, and memories without loss of data
UPDATE public.conversations c
SET user_id = p.user_id
FROM public.profiles p
WHERE c.user_id = p.id;

UPDATE public.chat_messages m
SET user_id = p.user_id
FROM public.profiles p
WHERE m.user_id = p.id;

UPDATE public.memories m
SET user_id = p.user_id
FROM public.profiles p
WHERE m.user_id = p.id;

UPDATE public.user_personality up
SET user_id = p.user_id
FROM public.profiles p
WHERE up.user_id = p.id;

UPDATE public.user_question_answers uqa
SET user_id = p.user_id
FROM public.profiles p
WHERE uqa.user_id = p.id;

-- 4. Establish a unique constraint on profiles.user_id (necessary for foreign key target mapping)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'profiles_user_id_key') THEN
    ALTER TABLE public.profiles ADD CONSTRAINT profiles_user_id_key UNIQUE (user_id);
  END IF;
END $$;

-- 5. Recreate foreign key constraints referencing profiles(user_id)
ALTER TABLE public.conversations
  ADD CONSTRAINT conversations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(user_id) ON DELETE CASCADE;

ALTER TABLE public.chat_messages
  ADD CONSTRAINT chat_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(user_id) ON DELETE CASCADE;

ALTER TABLE public.memories
  ADD CONSTRAINT memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(user_id) ON DELETE CASCADE;

ALTER TABLE public.user_personality
  ADD CONSTRAINT user_personality_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(user_id) ON DELETE CASCADE;

ALTER TABLE public.user_question_answers
  ADD CONSTRAINT user_question_answers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(user_id) ON DELETE CASCADE;

-- 6. Re-enable Row Level Security (RLS) on crucial tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_personality ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_question_answers ENABLE ROW LEVEL SECURITY;

-- 7. Audit & Update all Row Level Security (RLS) policies using direct auth.uid() = user_id checks

-- profiles policies
DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
CREATE POLICY "profiles_select_own" ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
CREATE POLICY "profiles_insert_own" ON public.profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;
CREATE POLICY "profiles_update_own" ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "profiles_delete_own" ON public.profiles;
CREATE POLICY "profiles_delete_own" ON public.profiles FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- conversations policies
DROP POLICY IF EXISTS "conversations_select_own" ON public.conversations;
CREATE POLICY "conversations_select_own" ON public.conversations FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "conversations_insert_own" ON public.conversations;
CREATE POLICY "conversations_insert_own" ON public.conversations FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "conversations_update_own" ON public.conversations;
CREATE POLICY "conversations_update_own" ON public.conversations FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "conversations_delete_own" ON public.conversations;
CREATE POLICY "conversations_delete_own" ON public.conversations FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- chat_messages policies
DROP POLICY IF EXISTS "chat_messages_select_own" ON public.chat_messages;
CREATE POLICY "chat_messages_select_own" ON public.chat_messages FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "chat_messages_insert_own" ON public.chat_messages;
CREATE POLICY "chat_messages_insert_own" ON public.chat_messages FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "chat_messages_update_own" ON public.chat_messages;
CREATE POLICY "chat_messages_update_own" ON public.chat_messages FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "chat_messages_delete_own" ON public.chat_messages;
CREATE POLICY "chat_messages_delete_own" ON public.chat_messages FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- user_question_answers policies
DROP POLICY IF EXISTS "answers_select_own" ON public.user_question_answers;
CREATE POLICY "answers_select_own" ON public.user_question_answers FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "answers_insert_own" ON public.user_question_answers;
CREATE POLICY "answers_insert_own" ON public.user_question_answers FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "answers_update_own" ON public.user_question_answers;
CREATE POLICY "answers_update_own" ON public.user_question_answers FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "answers_delete_own" ON public.user_question_answers;
CREATE POLICY "answers_delete_own" ON public.user_question_answers FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- user_personality policies
DROP POLICY IF EXISTS "personality_select_own" ON public.user_personality;
CREATE POLICY "personality_select_own" ON public.user_personality FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "personality_insert_own" ON public.user_personality;
CREATE POLICY "personality_insert_own" ON public.user_personality FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "personality_update_own" ON public.user_personality;
CREATE POLICY "personality_update_own" ON public.user_personality FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "personality_delete_own" ON public.user_personality;
CREATE POLICY "personality_delete_own" ON public.user_personality FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- memories policies
DROP POLICY IF EXISTS "memories_select_own" ON public.memories;
CREATE POLICY "memories_select_own" ON public.memories FOR SELECT TO authenticated USING (auth.uid() = user_id);
DROP POLICY IF EXISTS "memories_insert_own" ON public.memories;
CREATE POLICY "memories_insert_own" ON public.memories FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "memories_update_own" ON public.memories;
CREATE POLICY "memories_update_own" ON public.memories FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS "memories_delete_own" ON public.memories;
CREATE POLICY "memories_delete_own" ON public.memories FOR DELETE TO authenticated USING (auth.uid() = user_id);

COMMIT;
