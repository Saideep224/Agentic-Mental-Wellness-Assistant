'use client';

import { useState, useCallback, useEffect } from 'react';
import { OnboardingResponse } from '@/types';
import { questions, getCategoryForQuestion } from '@/data/questions';
import * as api from '@/api';
import { useAuth } from '@/providers/AuthProvider';
import { supabase } from '@/database/supabase';

export function useOnboarding() {
  const { refreshUser, logout } = useAuth();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<OnboardingResponse[]>([]);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [customText, setCustomText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [direction, setDirection] = useState(1);
  const [showCategoryTransition, setShowCategoryTransition] = useState(false);
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentQuestion = questions[currentIndex];
  const totalQuestions = questions.length;
  const currentCategory = getCategoryForQuestion(currentIndex);
  const progress = ((currentIndex + 1) / totalQuestions) * 100;

  // Check if we're transitioning to a new category
  const nextCategory = currentIndex < totalQuestions - 1
    ? getCategoryForQuestion(currentIndex + 1)
    : null;

  const isNewCategory = nextCategory !== null && nextCategory !== currentCategory;

  const saveProgress = useCallback((newIndex: number, newResponses: OnboardingResponse[]) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('esona_onboarding_index', newIndex.toString());
      localStorage.setItem('esona_onboarding_responses', JSON.stringify(newResponses));
    }
  }, []);

  // Load initial progress on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedIndex = localStorage.getItem('esona_onboarding_index');
      const storedResponses = localStorage.getItem('esona_onboarding_responses');
      
      let initialIdx = 0;
      let initialResponses: OnboardingResponse[] = [];

      if (storedIndex) {
        initialIdx = parseInt(storedIndex, 10);
        setCurrentIndex(initialIdx);
      }
      if (storedResponses) {
        initialResponses = JSON.parse(storedResponses);
        setResponses(initialResponses);
      }

      // Restore selections for the current index
      const currQ = questions[initialIdx];
      if (currQ) {
        const existing = initialResponses.find((r) => r.questionId === currQ.id);
        if (existing) {
          setSelectedOptions(existing.selectedAnswers || []);
          setCustomText(existing.customAnswer || '');
        }
      }
    }

    const loadSavedAnswers = async () => {
      const token = api.getToken();
      if (!token) return;

      try {
        const saved = await api.getOnboardingAnswers(token);
        const savedResponses: OnboardingResponse[] = saved.map((answer: {
          question_id: number;
          category: string;
          selected_answers?: string[];
          custom_answer?: string | null;
        }) => ({
          questionId: answer.question_id,
          category: answer.category,
          selectedAnswers: answer.selected_answers || [],
          customAnswer: answer.custom_answer || undefined,
        }));

        setResponses(savedResponses);

        const firstUnansweredIndex = questions.findIndex((question) => {
          const savedAnswer = savedResponses.find((item) => item.questionId === question.id);
          return !savedAnswer || (savedAnswer.selectedAnswers.length === 0 && !savedAnswer.customAnswer);
        });
        const unansweredIdx = firstUnansweredIndex >= 0 ? firstUnansweredIndex : Math.max(0, questions.length - 1);

        // Fetch onboarding step from backend status
        let nextIndex = unansweredIdx;
        try {
          const savedStatus = await api.getOnboardingStatus(token);
          const savedStep = savedStatus.onboarding_step || 1;
          const savedStepIdx = savedStep - 1;
          if (savedStepIdx > 0 && savedStepIdx < questions.length) {
            nextIndex = savedStepIdx;
          }
        } catch (statusErr) {
          console.warn('[Onboarding] Could not load onboarding status, falling back to unanswered index:', statusErr);
        }

        setCurrentIndex(nextIndex);

        const currentSaved = savedResponses.find((item) => item.questionId === questions[nextIndex]?.id);
        setSelectedOptions(currentSaved?.selectedAnswers || []);
        setCustomText(currentSaved?.customAnswer || '');
        saveProgress(nextIndex, savedResponses);
      } catch (err) {
        console.warn('[Onboarding] Could not load saved answers:', err);
      }
    };

    loadSavedAnswers();
  }, [saveProgress]);

  const handleSubmit = useCallback(async (allResponses: OnboardingResponse[]) => {
    console.log('[LOG] Onboarding completed clicked (handleSubmit started), responses count:', allResponses.length);
    setIsSubmitting(true);
    setError(null);

    try {
      const token = api.getToken();
      if (!token) {
        console.warn('[LOG] Onboarding submit failed: no token found');
        setError('Not authenticated');
        setIsSubmitting(false);
        return;
      }

      console.log('[LOG] Saving onboarding answers directly to Supabase...');
      await api.upsertQuestionAnswersToSupabase(
        allResponses.map((response) => ({
          ...response,
          questionText: questions.find((question) => question.id === response.questionId)?.text || '',
        }))
      );
      console.log('[LOG] Profile & answers successfully saved in Supabase');

      console.log('[LOG] Submitting onboarding answers to backend...');
      await api.submitOnboarding(allResponses, token);
      console.log('[LOG] Backend onboarding submit request succeeded');

      // Update onboarding_completed in Supabase profiles table & user metadata
      try {
        console.log('[LOG] Fetching Supabase user for metadata update...');
        const { data: { user: supabaseUser } } = await supabase.auth.getUser();
        if (supabaseUser) {
          console.log('[LOG] Updating onboarding_completed to true in Supabase profiles table for:', supabaseUser.id);
          // Update profiles table
          const { error: updateErr } = await supabase
            .from('profiles')
            .update({ onboarding_completed: true })
            .eq('id', supabaseUser.id);
          if (updateErr) {
            console.error('[Onboarding] Supabase profile update failed:', updateErr);
          } else {
            console.log('[Onboarding] Updated onboarding_completed to true in Supabase profiles table');
          }

          // Update user auth metadata
          const { error: metaErr } = await supabase.auth.updateUser({
            data: { onboarding_completed: true }
          });
          if (metaErr) {
            console.error('[Onboarding] Supabase metadata update failed:', metaErr);
          } else {
            console.log('[Onboarding] Updated onboarding_completed to true in Supabase user metadata');
          }
        }
      } catch (sbErr) {
        console.error('[Onboarding] Failed to update onboarding status in Supabase:', sbErr);
      }

      // Clear onboarding progress from local storage
      if (typeof window !== 'undefined') {
        console.log('[LOG] Clearing onboarding progress from localStorage...');
        localStorage.removeItem('esona_onboarding_index');
        localStorage.removeItem('esona_onboarding_responses');
      }

      // Update stored user and trigger reactiveness
      console.log('[LOG] Refreshing user details in Auth context...');
      await refreshUser();
      console.log('[LOG] refreshUser successfully finished in handleSubmit');

      console.log('[LOG] Setting isComplete to true (triggering success screen)');
      setIsComplete(true);
    } catch (err: any) {
      console.error('[LOG] Onboarding submission failed with exception:', err);
      const errMsg = err instanceof Error ? err.message : '';
      const isUserNotFound = 
        errMsg.includes('user_not_found') || 
        errMsg.includes('sub claim') || 
        errMsg.includes('does not exist') ||
        errMsg.includes('403');

      if (isUserNotFound) {
        console.warn('[LOG] User not found or invalid session (403/user_not_found). Clearing auth and redirecting...');
        api.clearAuth();
        if (typeof window !== 'undefined') {
          console.log('[LOG] Redirecting to /login due to stale session');
          window.location.href = '/login';
        }
        return;
      }

      if (errMsg.includes('Onboarding already completed')) {
        console.log('[LOG] Onboarding already completed. Grabbing fresh user and marking complete...');
        // Update stored user and mark complete gracefully
        await refreshUser();
        setIsComplete(true);
      } else {
        setError(errMsg || 'Failed to submit your responses. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [refreshUser]);


  const selectOption = useCallback((value: string) => {
    setSelectedOptions((prev) => {
      if (prev.includes(value)) {
        return prev.filter((v) => v !== value);
      } else {
        return [...prev, value];
      }
    });
  }, []);

  const goToNext = useCallback(() => {
    const hasCustomText = customText.trim().length > 0;
    if (selectedOptions.length === 0 && !hasCustomText) return;

    const response: OnboardingResponse = {
      questionId: currentQuestion.id,
      category: currentQuestion.category,
      selectedAnswers: selectedOptions,
      customAnswer: hasCustomText ? customText.trim() : undefined,
    };

    // Save live to database
    const token = api.getToken();
    if (token) {
      api.saveOnboardingAnswer(response, token).catch((err) => {
        console.warn('[Onboarding] Live answer saving failed:', err);
      });
      // Save next onboarding step live
      const nextIdx = currentIndex + 1;
      if (nextIdx < totalQuestions) {
        api.saveOnboardingStep(questions[nextIdx].id, token).catch((err) => {
          console.warn('[Onboarding] Live step saving failed:', err);
        });
      }
    }

    // Update or add response
    const updatedResponses = [...responses];
    const existingIdx = responses.findIndex((r) => r.questionId === currentQuestion.id);
    if (existingIdx >= 0) {
      updatedResponses[existingIdx] = response;
    } else {
      updatedResponses.push(response);
    }
    setResponses(updatedResponses);

    if (currentIndex < totalQuestions - 1) {
      const nextIdx = currentIndex + 1;
      const nextCat = getCategoryForQuestion(nextIdx);
      if (nextCat !== currentCategory) {
        setShowCategoryTransition(true);
        saveProgress(nextIdx, updatedResponses);
      } else {
        setDirection(1);
        setCurrentIndex(nextIdx);
        
        // Restore next question's answers if they exist
        const nextResponse = updatedResponses.find(
          (r) => r.questionId === questions[nextIdx].id
        );
        setSelectedOptions(nextResponse?.selectedAnswers || []);
        setCustomText(nextResponse?.customAnswer || '');
        saveProgress(nextIdx, updatedResponses);
      }
    } else {
      // Last question - submit all
      handleSubmit(updatedResponses);
    }
  }, [selectedOptions, customText, currentIndex, currentQuestion, totalQuestions, currentCategory, responses, handleSubmit]);

  const skipAllQuestions = useCallback(() => {
    // Build empty responses for all 20 questions
    const emptyResponses: OnboardingResponse[] = questions.map((q) => ({
      questionId: q.id,
      category: q.category,
      selectedAnswers: [],
      customAnswer: undefined,
    }));

    // Submit all with empty answers — marks onboarding as completed
    handleSubmit(emptyResponses);
  }, [questions, handleSubmit]);

  const continuePastTransition = useCallback(() => {
    setShowCategoryTransition(false);
    setDirection(1);
    const nextIdx = currentIndex + 1;
    setCurrentIndex(nextIdx);
    
    // Restore next question's answers if they exist
    const nextResponse = responses.find(
      (r) => r.questionId === questions[nextIdx].id
    );
    setSelectedOptions(nextResponse?.selectedAnswers || []);
    setCustomText(nextResponse?.customAnswer || '');
    saveProgress(nextIdx, responses);
  }, [currentIndex, responses]);

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      const prevIdx = currentIndex - 1;
      setDirection(-1);
      setCurrentIndex(prevIdx);
      const prevResponse = responses.find(
        (r) => r.questionId === questions[prevIdx].id
      );
      setSelectedOptions(prevResponse?.selectedAnswers || []);
      setCustomText(prevResponse?.customAnswer || '');
      
      if (typeof window !== 'undefined') {
        localStorage.setItem('esona_onboarding_index', prevIdx.toString());
      }
    }
  }, [currentIndex, responses]);

  const saveCurrentStepProgress = useCallback(async () => {
    const token = api.getToken();
    if (!token) return;

    // 1. Save current question's response if there is one
    const hasCustomText = customText.trim().length > 0;
    if (selectedOptions.length > 0 || hasCustomText) {
      const response: OnboardingResponse = {
        questionId: currentQuestion.id,
        category: currentQuestion.category,
        selectedAnswers: selectedOptions,
        customAnswer: hasCustomText ? customText.trim() : undefined,
      };
      
      try {
        await api.saveOnboardingAnswer(response, token);
      } catch (err) {
        console.warn('[Onboarding] Failed to save current answer:', err);
      }
    }

    // 2. Save the current step (1-indexed question ID)
    try {
      await api.saveOnboardingStep(currentQuestion.id, token);
    } catch (err) {
      console.warn('[Onboarding] Failed to save onboarding step:', err);
    }
  }, [currentQuestion, selectedOptions, customText]);

  const backToLogin = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await saveCurrentStepProgress();
      if (typeof window !== 'undefined') {
        localStorage.removeItem('esona_onboarding_index');
        localStorage.removeItem('esona_onboarding_responses');
      }
      await logout();
    } catch (err) {
      console.error('[Onboarding] Back to Login failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  }, [saveCurrentStepProgress, logout]);

  const saveAndContinueLater = useCallback(async () => {
    setIsSubmitting(true);
    try {
      await saveCurrentStepProgress();
      if (typeof window !== 'undefined') {
        localStorage.removeItem('esona_onboarding_index');
        localStorage.removeItem('esona_onboarding_responses');
      }
      await logout();
    } catch (err) {
      console.error('[Onboarding] Save & Continue Later failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  }, [saveCurrentStepProgress, logout]);


  return {
    currentQuestion,
    currentIndex,
    totalQuestions,
    currentCategory,
    progress,
    selectedOptions,
    customText,
    isSubmitting,
    isComplete,
    direction,
    showCategoryTransition,
    showSkipModal,
    setShowSkipModal,
    error,
    isNewCategory,
    nextCategory,
    selectOption,
    setCustomText,
    goToNext,
    skipAllQuestions,
    goToPrevious,
    continuePastTransition,
    backToLogin,
    saveAndContinueLater,
  };
}
