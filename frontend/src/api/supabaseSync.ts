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
  console.log('[LOG] upsertQuestionAnswersToSupabase called, responses count:', responses.length);
  try {
    const { data: { user }, error: userError } = await supabase.auth.getUser();
    if (userError) {
      console.error('[LOG] [SupabaseSync] Auth user lookup failed:', userError);
      throw formatSupabaseError('Unable to verify your login session', userError);
    }
    if (!user) {
      console.warn('[LOG] [SupabaseSync] No user session found');
      throw new Error('You are not signed in. Please log in again before saving answers.');
    }
    console.log('[LOG] [SupabaseSync] User found in Supabase Auth:', user.id, user.email);

    console.log('[LOG] [SupabaseSync] Ensuring profile exists in Supabase database...');
    await ensureSupabaseProfile(user);
    console.log('[LOG] [SupabaseSync] ensureSupabaseProfile completed successfully');

    const rows = responses.map((response) => ({
      user_id: user.id,
      question_id: response.questionId,
      question_text: response.questionText,
      selected_answer: response.selectedAnswers,
      category: response.category,
      custom_answer: response.customAnswer || null,
      updated_at: new Date().toISOString(),
    }));

    console.log('[LOG] [SupabaseSync] Upserting user_question_answers in Supabase...');
    const { error } = await supabase
      .from('user_question_answers')
      .upsert(rows, { onConflict: 'user_id,question_id' });

    if (error) {
      console.error('[LOG] [SupabaseSync] Knowing Me answer upsert failed:', {
        error,
        attemptedRows: rows,
        userId: user.id,
      });
      throw formatSupabaseError('Failed to save your answers', error);
    }
    console.log('[LOG] [SupabaseSync] user_question_answers upsert succeeded');

    const personalityProfile = derivePersonalityProfile(responses);
    console.log('[LOG] [SupabaseSync] Derived personality profile:', personalityProfile);

    console.log('[LOG] [SupabaseSync] Updating personality_profile and onboarding_completed in profiles table...');
    const { error: profileError } = await supabase
      .from('profiles')
      .update({
        personality_profile: personalityProfile,
        onboarding_completed: true,
        updated_at: new Date().toISOString(),
      })
      .eq('user_id', user.id);

    if (profileError) {
      console.error('[LOG] [SupabaseSync] Personality profile update failed:', profileError);
      throw formatSupabaseError('Answers saved, but profile personalization failed', profileError);
    }
    console.log('[LOG] [SupabaseSync] Profiles update (personality profile + onboarding completed) succeeded');
  } catch (err: any) {
    const errMsg = err instanceof Error ? err.message : String(err);
    console.error('[LOG] [SupabaseSync] Exception caught in upsertQuestionAnswersToSupabase:', errMsg);
    
    const isSessionError = 
      errMsg.includes('Unable to verify your login session') ||
      errMsg.includes('You are not signed in') ||
      errMsg.includes('user_not_found') || 
      errMsg.includes('sub claim') || 
      errMsg.includes('does not exist') ||
      errMsg.includes('403') ||
      errMsg.includes('401') ||
      errMsg.includes('JWT');
    
    if (isSessionError) {
      console.warn('[LOG] [SupabaseSync] Critical session error. Clearing auth and redirecting...', errMsg);
      if (typeof window !== 'undefined') {
        const { clearAuth } = await import('./client');
        clearAuth();
        console.log('[LOG] [SupabaseSync] Redirecting to /login due to session error');
        window.location.href = '/login';
      }
      throw err;
    } else {
      console.warn('[LOG] [SupabaseSync] Non-blocking database sync warning (e.g. Supabase DB not configured). Continuing...', errMsg);
      // Do not throw the error, let the save continue successfully to backend SQLite
    }
  }
}
