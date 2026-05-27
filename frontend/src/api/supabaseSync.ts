/**
 * Supabase sync — profile & answer synchronization with Supabase.
 * 
 * Handles direct Supabase database operations for profile syncing
 * and onboarding answer persistence.
 */

import { supabase } from '@/database/supabase';

// ============================================
// TYPES
// ============================================

type QuestionAnswerSaveInput = {
  questionId: number;
  questionText: string;
  category: string;
  selectedAnswers: string[];
  customAnswer?: string;
};

type SupabaseErrorLike = {
  message?: string;
  details?: string | null;
  hint?: string | null;
  code?: string;
  status?: number;
};

// ============================================
// HELPERS
// ============================================

function formatSupabaseError(prefix: string, error: SupabaseErrorLike): Error {
  const parts = [
    error.message,
    error.code ? `code: ${error.code}` : null,
    error.status ? `status: ${error.status}` : null,
    error.details ? `details: ${error.details}` : null,
    error.hint ? `hint: ${error.hint}` : null,
  ].filter(Boolean);

  return new Error(`${prefix}: ${parts.join(' | ') || 'Unknown Supabase error'}`);
}

/**
 * Derive a personality profile from onboarding answers.
 * Maps selected answers to personality traits for the Supabase profiles table.
 */
function derivePersonalityProfile(responses: QuestionAnswerSaveInput[]) {
  const selected = new Set(responses.flatMap((response) => response.selectedAnswers || []));
  const has = (...values: string[]) => values.some((value) => selected.has(value));

  const replyLength = has('short_replies', 'long_paragraphs') ? 'short' : 'medium';
  const humorPreference = has('humor_hide', 'distraction', 'laugh', 'memes');
  const stressPattern = has('overthink', 'overthinking', 'future', 'anxious')
    ? 'overthinking'
    : has('isolate', 'go_silent', 'need_space')
      ? 'shutdown'
      : has('pressure', 'career')
        ? 'performance_pressure'
        : 'mixed';
  const communicationStyle = has('straightforward', 'handle_truth')
    ? 'direct'
    : has('gentle', 'comfort', 'listening')
      ? 'gentle'
      : has('close_friend', 'smart_chill')
        ? 'casual'
        : 'warm';

  return {
    communication_style: communicationStyle,
    humor_preference: humorPreference,
    reply_length: replyLength,
    stress_pattern: stressPattern,
    support_preference: has('advice') ? 'practical_advice' : has('listening', 'need_space') ? 'listening' : 'validation',
    emotional_tone: has('numb') ? 'numb' : has('storms', 'unpredictable') ? 'intense' : has('calm') ? 'calm' : 'reflective',
    updated_at: new Date().toISOString(),
  };
}

// ============================================
// SUPABASE PROFILE SYNC
// ============================================

/**
 * Ensure the user's Supabase profile row exists (upsert).
 * Called before saving answers to satisfy foreign key constraints.
 */
async function ensureSupabaseProfile(user: NonNullable<Awaited<ReturnType<typeof supabase.auth.getUser>>['data']['user']>) {
  const metadata = user.user_metadata || {};
  const provider = user.app_metadata?.provider || user.identities?.[0]?.provider || 'credentials';

  const { error } = await supabase.from('profiles').upsert(
    {
      id: user.id,
      user_id: user.id,
      email: user.email || '',
      full_name: metadata.full_name || metadata.name || user.email?.split('@')[0] || 'Esona User',
      avatar_url: metadata.avatar_url || metadata.picture || null,
      provider,
      github_username: provider === 'github' ? metadata.user_name || null : null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: 'user_id' }
  );

  if (error) {
    console.error('[Supabase] Profile upsert failed:', error);
    throw formatSupabaseError('Unable to sync your profile before saving answers', error);
  }
}

// ============================================
// ANSWER SYNC
// ============================================

/**
 * Save onboarding answers directly to Supabase and update personality profile.
 * This syncs the frontend-derived personality traits to the profiles table.
 */
export async function upsertQuestionAnswersToSupabase(
  responses: QuestionAnswerSaveInput[]
): Promise<void> {
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (userError) {
    console.error('[Supabase] Auth user lookup failed:', userError);
    throw formatSupabaseError('Unable to verify your login session', userError);
  }
  if (!user) throw new Error('You are not signed in. Please log in again before saving answers.');

  await ensureSupabaseProfile(user);

  const rows = responses.map((response) => ({
    user_id: user.id,
    question_id: response.questionId,
    question_text: response.questionText,
    selected_answer: response.selectedAnswers,
    category: response.category,
    custom_answer: response.customAnswer || null,
    updated_at: new Date().toISOString(),
  }));

  const { error } = await supabase
    .from('user_question_answers')
    .upsert(rows, { onConflict: 'user_id,question_id' });

  if (error) {
    console.error('[Supabase] Knowing Me answer upsert failed:', {
      error,
      attemptedRows: rows,
      userId: user.id,
    });
    throw formatSupabaseError('Failed to save your answers', error);
  }

  const personalityProfile = derivePersonalityProfile(responses);
  const { error: profileError } = await supabase
    .from('profiles')
    .update({
      personality_profile: personalityProfile,
      onboarding_completed: true,
      updated_at: new Date().toISOString(),
    })
    .eq('user_id', user.id);

  if (profileError) {
    console.error('[Supabase] Personality profile update failed:', profileError);
    throw formatSupabaseError('Answers saved, but profile personalization failed', profileError);
  }
}
