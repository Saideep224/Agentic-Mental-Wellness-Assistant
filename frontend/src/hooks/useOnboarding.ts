'use client';

import { useState, useCallback, useMemo } from 'react';
import { OnboardingResponse } from '@/types';
import { questions, getCategoryForQuestion } from '@/data/questions';
import * as api from '@/lib/api';

export function useOnboarding() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [responses, setResponses] = useState<OnboardingResponse[]>([]);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
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

  // Check if an answer exists for the current question
  const existingResponse = useMemo(
    () => responses.find((r) => r.questionId === currentQuestion?.id),
    [responses, currentQuestion]
  );

  // Restore selected option if going back
  useState(() => {
    if (existingResponse) {
      setSelectedOption(existingResponse.selectedOption);
      setCustomText(existingResponse.customText || '');
    }
  });

  const selectOption = useCallback((value: string) => {
    setSelectedOption(value);
    setCustomText('');
  }, []);

  const goToNext = useCallback(() => {
    if (!selectedOption && !customText) return;

    const response: OnboardingResponse = {
      questionId: currentQuestion.id,
      category: currentQuestion.category,
      selectedOption: selectedOption === 'other' ? 'other' : (selectedOption || ''),
      customText: selectedOption === 'other' ? customText : undefined,
    };

    // Update or add response
    setResponses((prev) => {
      const existing = prev.findIndex((r) => r.questionId === currentQuestion.id);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = response;
        return updated;
      }
      return [...prev, response];
    });

    if (currentIndex < totalQuestions - 1) {
      // Check if next question is a new category
      const nextCat = getCategoryForQuestion(currentIndex + 1);
      if (nextCat !== currentCategory) {
        setShowCategoryTransition(true);
      } else {
        setDirection(1);
        setCurrentIndex((prev) => prev + 1);
        setSelectedOption(null);
        setCustomText('');
      }
    } else {
      // Last question - submit all
      handleSubmit([...responses.filter((r) => r.questionId !== currentQuestion.id), response]);
    }
  }, [selectedOption, customText, currentIndex, currentQuestion, totalQuestions, currentCategory, responses]);

  const continuePastTransition = useCallback(() => {
    setShowCategoryTransition(false);
    setDirection(1);
    setCurrentIndex((prev) => prev + 1);
    setSelectedOption(null);
    setCustomText('');
  }, []);

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setDirection(-1);
      setCurrentIndex((prev) => prev - 1);
      const prevResponse = responses.find(
        (r) => r.questionId === questions[currentIndex - 1].id
      );
      setSelectedOption(prevResponse?.selectedOption || null);
      setCustomText(prevResponse?.customText || '');
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

      // Update stored user
      const user = api.getStoredUser();
      if (user) {
        user.onboardingCompleted = true;
        api.setStoredUser(user);
      }

      setIsComplete(true);
    } catch (err: any) {
      console.error('Onboarding submission failed:', err);
      const errMsg = err instanceof Error ? err.message : '';
      if (errMsg.includes('Onboarding already completed')) {
        // Update stored user and mark complete gracefully
        const user = api.getStoredUser();
        if (user) {
          user.onboardingCompleted = true;
          api.setStoredUser(user);
        }
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
    selectedOption,
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
