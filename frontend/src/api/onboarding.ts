/**
 * Onboarding API — personality quiz submission and status.
 */

import { ApiResponse } from '@/types';
import { apiPost, apiGet } from './client';

export async function submitOnboarding(
  responses: Array<{ questionId: number; category: string; selectedAnswers: string[]; customAnswer?: string }>,
  token: string
): Promise<ApiResponse> {
  const answers = responses.map((r) => ({
    question_id: r.questionId,
    category: r.category,
    selected_answers: r.selectedAnswers,
    custom_answer: r.customAnswer || null,
  }));
  return apiPost<ApiResponse>('/api/onboarding/submit', { answers }, token);
}

export async function saveOnboardingAnswer(
  response: { questionId: number; category: string; selectedAnswers: string[]; customAnswer?: string },
  token: string
): Promise<ApiResponse> {
  const answer = {
    question_id: response.questionId,
    category: response.category,
    selected_answers: response.selectedAnswers,
    custom_answer: response.customAnswer || null,
  };
  return apiPost<ApiResponse>('/api/onboarding/answer', answer, token);
}

export async function getOnboardingAnswers(token: string): Promise<any[]> {
  return apiGet<any[]>('/api/onboarding/answers', token);
}

export async function getOnboardingStatus(token: string): Promise<{ completed: boolean; onboarding_step?: number }> {
  const data = await apiGet<any>('/api/onboarding/status', token);
  return {
    completed: data.onboarding_completed ?? data.completed ?? false,
    onboarding_step: data.onboarding_step,
  };
}

export async function saveOnboardingStep(
  step: number,
  token: string
): Promise<ApiResponse> {
  return apiPost<ApiResponse>('/api/onboarding/step', { step }, token);
}
