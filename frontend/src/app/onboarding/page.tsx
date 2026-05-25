'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, Sparkles, Loader2 } from 'lucide-react';
import { useOnboarding } from '@/hooks/useOnboarding';
import ProgressBar from '@/components/onboarding/ProgressBar';
import QuestionCard from '@/components/onboarding/QuestionCard';
import OptionCard from '@/components/onboarding/OptionCard';
import OtherInput from '@/components/onboarding/OtherInput';
import CategoryTransition from '@/components/onboarding/CategoryTransition';
import BreathingOrb from '@/components/ambient/BreathingOrb';
import { getToken, getStoredUser, setStoredUser, getOnboardingStatus } from '@/lib/api';

export default function OnboardingPage() {
  const router = useRouter();
  const {
    currentQuestion,
    currentIndex,
    totalQuestions,
    currentCategory,
    selectedOptions,
    customText,
    isSubmitting,
    isComplete,
    direction,
    showCategoryTransition,
    error,
    selectOption,
    setCustomText,
    goToNext,
    goToPrevious,
    continuePastTransition,
  } = useOnboarding();

  // Check auth and onboarding status
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }

    const checkStatus = async () => {
      // First check local storage
      const user = getStoredUser();
      if (user && user.onboardingCompleted) {
        router.push('/dashboard');
        return;
      }

      // Double-check with backend
      try {
        const status = await getOnboardingStatus(token);
        if (status.completed) {
          if (user) {
            user.onboardingCompleted = true;
            setStoredUser(user);
          }
          router.push('/dashboard');
        }
      } catch (err) {
        console.error('Failed to check onboarding status:', err);
      }
    };

    checkStatus();
  }, [router]);

  // Redirect after completion
  useEffect(() => {
    if (isComplete) {
      const timer = setTimeout(() => {
        router.push('/dashboard');
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [isComplete, router]);

  // Completion screen
  if (isComplete) {
    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="text-center max-w-md w-full"
        >
          <BreathingOrb size={120} className="mx-auto mb-8 animate-pulse" />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-4"
          >
            <Sparkles
              size={36}
              className="mx-auto mb-2 text-cyan-400 animate-bounce"
            />
            <h2
              className="text-3xl font-bold mb-3 glow-text"
              style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
            >
              Analyzing your answers...
            </h2>
            <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
              🧠 Building your personalized wellness space...
            </p>
            <p className="text-xs text-slate-500 italic mt-2">
              Generating personality type, insights, and coping recommendations.
            </p>
          </motion.div>

          {/* Loading bar */}
          <div className="mt-8 max-w-xs mx-auto h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: '100%' }}
              transition={{ duration: 3.5, ease: 'easeInOut' }}
              className="h-full"
              style={{
                background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))',
                boxShadow: '0 0 10px rgba(34, 211, 238, 0.5)',
              }}
            />
          </div>
        </motion.div>
      </main>
    );
  }

  // Category transition screen
  if (showCategoryTransition) {
    const catMap: Record<string, string> = {
      personality: 'emotion',
      emotion: 'hobbies',
      hobbies: 'communication',
    };
    const upcomingCategory = catMap[currentCategory] || 'communication';

    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <CategoryTransition
          category={upcomingCategory}
          onContinue={continuePastTransition}
        />
      </main>
    );
  }

  if (!currentQuestion) return null;

  const canGoNext = selectedOptions.length > 0 || customText.trim().length > 0;
  const isLastQuestion = currentIndex === totalQuestions - 1;

  return (
    <main className="min-h-screen flex flex-col px-4 pt-4 pb-20">
      {/* Header and Subtext */}
      <div className="text-center mt-6 mb-4">
        <h1
          className="text-2xl sm:text-3xl font-bold text-white flex items-center justify-center gap-2 mb-2"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          🧠 Help Esona understand you better
        </h1>
        <p className="text-xs sm:text-sm max-w-lg mx-auto" style={{ color: 'var(--text-muted)' }}>
          These questions personalize your emotional insights, personality analysis, and AI responses.
        </p>
      </div>

      {/* Progress */}
      <div className="max-w-2xl mx-auto w-full mb-6">
        <ProgressBar
          currentQuestion={currentIndex}
          totalQuestions={totalQuestions}
          currentCategory={currentCategory}
        />
      </div>

      {/* Question */}
      <div className="flex-1 flex flex-col justify-center max-w-2xl mx-auto w-full">
        <AnimatePresence mode="wait">
          <QuestionCard
            key={currentQuestion.id}
            question={currentQuestion}
            direction={direction}
          />
        </AnimatePresence>

        {/* Small Helper Text */}
        <p className="text-xs text-slate-400 mb-3 text-center italic">
          Select one or more choices or type your own answer for personalized responses.
        </p>

        {/* Options */}
        <div className="space-y-3 mb-4">
          {currentQuestion.options.map((option, i) => (
            <OptionCard
              key={option.value}
              option={option}
              index={i}
              isSelected={selectedOptions.includes(option.value)}
              onSelect={() => selectOption(option.value)}
            />
          ))}

          {/* Other option */}
          {currentQuestion.allowOther && (
            <OptionCard
              option={{ label: "Something else...", value: "other", emoji: "✏️" }}
              index={currentQuestion.options.length}
              isSelected={selectedOptions.includes('other')}
              onSelect={() => selectOption('other')}
            />
          )}
        </div>

        {/* Custom text input */}
        <OtherInput
          isVisible={selectedOptions.includes('other')}
          value={customText}
          onChange={setCustomText}
        />

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4 px-4 py-3 rounded-xl text-sm text-center"
              style={{
                background: 'rgba(244, 114, 182, 0.1)',
                border: '1px solid rgba(244, 114, 182, 0.2)',
                color: 'var(--accent-pink)',
              }}
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation buttons */}
      <div className="max-w-2xl mx-auto w-full flex items-center justify-between mt-8">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={goToPrevious}
          disabled={currentIndex === 0}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--glass-border)',
            color: 'var(--text-secondary)',
          }}
        >
          <ArrowLeft size={16} />
          Back
        </motion.button>

        <motion.button
          whileHover={{ scale: canGoNext ? 1.03 : 1 }}
          whileTap={{ scale: canGoNext ? 0.97 : 1 }}
          onClick={goToNext}
          disabled={!canGoNext || isSubmitting}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: canGoNext
              ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))'
              : 'rgba(255, 255, 255, 0.03)',
            color: canGoNext ? 'var(--bg-primary)' : 'var(--text-muted)',
            boxShadow: canGoNext ? 'var(--glow-cyan)' : 'none',
          }}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Submitting...
            </>
          ) : isLastQuestion ? (
            <>
              <Sparkles size={16} />
              Complete
            </>
          ) : (
            <>
              Next
              <ArrowRight size={16} />
            </>
          )}
        </motion.button>
      </div>
    </main>
  );
}
