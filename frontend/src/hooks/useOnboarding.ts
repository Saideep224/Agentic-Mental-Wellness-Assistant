'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { OnboardingResponse } from '@/types';
import { questions, getCategoryForQuestion } from '@/data/questions';
import * as api from '@/lib/api';
import { useAuth } from '@/providers/AuthProvider';
import { supabase } from '@/lib/supabase';

export function useOnboarding() {
  const { refreshUser } = useAuth();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<OnboardingResponse[]>([]);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [customText, setCustomText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [direction, setDirection] = useState(1);
  const [showCategoryTransition, setShowCategoryTransition] = useState(false);
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
  }, []);

  const saveProgress = (newIndex: number, newResponses: OnboardingResponse[]) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('esona_onboarding_index', newIndex.toString());
      localStorage.setItem('esona_onboarding_responses', JSON.stringify(newResponses));
    }
  };

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
  }, [selectedOptions, customText, currentIndex, currentQuestion, totalQuestions, currentCategory, responses]);

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

  const handleSubmit = async (allResponses: OnboardingResponse[]) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const token = api.getToken();
      if (!token) {
        setError('Not authenticated');
        setIsSubmitting(false);
        return;
      }

      await api.submitOnboarding(allResponses, token);

      // Update onboarding_completed in Supabase profiles table & user metadata
      try {
        const { data: { user: supabaseUser } } = await supabase.auth.getUser();
        if (supabaseUser) {
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
        localStorage.removeItem('esona_onboarding_index');
        localStorage.removeItem('esona_onboarding_responses');
      }

      // Update stored user and trigger reactiveness
      await refreshUser();

      setIsComplete(true);
    } catch (err: any) {
      console.error('Onboarding submission failed:', err);
      const errMsg = err instanceof Error ? err.message : '';
      if (errMsg.includes('Onboarding already completed')) {
        // Update stored user and mark complete gracefully
        await refreshUser();
        setIsComplete(true);
      } else {
        setError(errMsg || 'Failed to submit your responses. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

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
    error,
    isNewCategory,
    nextCategory,
    selectOption,
    setCustomText,
    goToNext,
    goToPrevious,
    continuePastTransition,
  };
}
