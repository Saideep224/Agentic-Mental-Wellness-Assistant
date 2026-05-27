create extension if not exists "pgcrypto";

alter table public.profiles add column if not exists user_id uuid;
update public.profiles set user_id = id where user_id is null;
alter table public.profiles alter column user_id set not null;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'profiles_user_id_key') then
    alter table public.profiles add constraint profiles_user_id_key unique (user_id);
  end if;
end $$;

alter table public.profiles add column if not exists full_name text not null default '';
update public.profiles
set full_name = coalesce(nullif(full_name, ''), nullif(name, ''), email)
where full_name = '';
alter table public.profiles add column if not exists avatar_url text;
alter table public.profiles add column if not exists provider text not null default 'credentials';
alter table public.profiles add column if not exists personality_profile jsonb not null default '{}'::jsonb;
alter table public.profiles add column if not exists interests jsonb not null default '{}'::jsonb;
alter table public.profiles add column if not exists communication_style text;
alter table public.profiles add column if not exists personality_type text;
alter table public.profiles add column if not exists github_username text;
alter table public.profiles add column if not exists updated_at timestamptz not null default now();
alter table public.profiles add column if not exists last_login timestamptz;

create table if not exists public.user_question_answers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  question_id integer not null check (question_id between 1 and 20),
  question_text text not null default '',
  selected_answer jsonb not null default '[]'::jsonb,
  category text not null,
  custom_answer text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_user_question_answers_user_question unique (user_id, question_id)
);

alter table public.conversations add column if not exists title text not null default 'New Conversation';
alter table public.conversations add column if not exists emotional_tag text;
alter table public.conversations add column if not exists updated_at timestamptz not null default now();

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references public.profiles(user_id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  message text not null,
  emotion_detected text,
  mood_score double precision,
  agent_analysis jsonb,
  emotional_context jsonb,
  created_at timestamptz not null default now()
);

alter table public.user_personality add column if not exists user_id uuid references public.profiles(user_id) on delete cascade;
update public.user_personality up
set user_id = p.id
from public.profiles p
where up.user_id is null and up.user_email = p.email;
alter table public.user_personality add column if not exists personality_profile jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists emotional_baseline jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists comfort_preferences jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists emotional_style jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists stress_triggers jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists strengths jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists weaknesses jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists onboarding_answers jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists onboarding_completed boolean not null default false;
alter table public.user_personality add column if not exists emotional_summary jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists stress_patterns jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists emotional_triggers jsonb not null default '{}'::jsonb;
alter table public.user_personality add column if not exists preferred_response_style jsonb not null default '{}'::jsonb;

do $$
begin
  alter table public.user_personality alter column personality_type type jsonb
  using case
    when personality_type is null or personality_type = '' then '{}'::jsonb
    else jsonb_build_object('type', personality_type)
  end;
exception when datatype_mismatch or invalid_text_representation then
  null;
end $$;

do $$
begin
  alter table public.user_personality alter column communication_style type jsonb
  using case
    when communication_style is null or communication_style = '' then '{}'::jsonb
    else jsonb_build_object('preferred_style', communication_style)
  end;
exception when datatype_mismatch or invalid_text_representation then
  null;
end $$;

create index if not exists idx_user_question_answers_user_id on public.user_question_answers(user_id);
create index if not exists idx_conversations_user_updated on public.conversations(user_id, updated_at desc);
create index if not exists idx_chat_messages_conversation_created on public.chat_messages(conversation_id, created_at);
create index if not exists idx_chat_messages_user_created on public.chat_messages(user_id, created_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_profiles_updated_at on public.profiles;
create trigger set_profiles_updated_at before update on public.profiles for each row execute function public.set_updated_at();
drop trigger if exists set_user_question_answers_updated_at on public.user_question_answers;
create trigger set_user_question_answers_updated_at before update on public.user_question_answers for each row execute function public.set_updated_at();
drop trigger if exists set_conversations_updated_at on public.conversations;
create trigger set_conversations_updated_at before update on public.conversations for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.user_question_answers enable row level security;
alter table public.conversations enable row level security;
alter table public.chat_messages enable row level security;

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on
  public.profiles,
  public.user_question_answers,
  public.conversations,
  public.chat_messages
to authenticated;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles for select to authenticated using (auth.uid() = user_id);
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "profiles_delete_own" on public.profiles;
create policy "profiles_delete_own" on public.profiles for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "answers_select_own" on public.user_question_answers;
create policy "answers_select_own" on public.user_question_answers for select to authenticated using (auth.uid() = user_id);
drop policy if exists "answers_insert_own" on public.user_question_answers;
create policy "answers_insert_own" on public.user_question_answers for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "answers_update_own" on public.user_question_answers;
create policy "answers_update_own" on public.user_question_answers for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "answers_delete_own" on public.user_question_answers;
create policy "answers_delete_own" on public.user_question_answers for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "conversations_select_own" on public.conversations;
create policy "conversations_select_own" on public.conversations for select to authenticated using (auth.uid() = user_id);
drop policy if exists "conversations_insert_own" on public.conversations;
create policy "conversations_insert_own" on public.conversations for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "conversations_update_own" on public.conversations;
create policy "conversations_update_own" on public.conversations for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "conversations_delete_own" on public.conversations;
create policy "conversations_delete_own" on public.conversations for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "chat_messages_select_own" on public.chat_messages;
create policy "chat_messages_select_own" on public.chat_messages for select to authenticated using (auth.uid() = user_id);
drop policy if exists "chat_messages_insert_own" on public.chat_messages;
create policy "chat_messages_insert_own" on public.chat_messages for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "chat_messages_update_own" on public.chat_messages;
create policy "chat_messages_update_own" on public.chat_messages for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "chat_messages_delete_own" on public.chat_messages;
create policy "chat_messages_delete_own" on public.chat_messages for delete to authenticated using (auth.uid() = user_id);
