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
    selectedOption,
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
        router.push('/chat');
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
          router.push('/chat');
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
        router.push('/chat');
      }, 3000);
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
          className="text-center"
        >
          <BreathingOrb size={150} className="mx-auto mb-8" />

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Sparkles
              size={32}
              className="mx-auto mb-4"
              style={{ color: 'var(--accent-cyan)' }}
            />
            <h2
              className="text-3xl font-bold mb-3 glow-text"
              style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
            >
              You&apos;re all set!
            </h2>
            <p className="text-base mb-2" style={{ color: 'var(--text-secondary)' }}>
              Esona now understands you a little better.
            </p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Taking you to your first conversation...
            </p>
          </motion.div>

          {/* Loading dots */}
          <div className="flex items-center justify-center gap-1.5 mt-8">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full typing-dot"
                style={{
                  backgroundColor: 'var(--accent-cyan)',
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </div>
        </motion.div>
      </main>
    );
  }

  // Category transition screen
  if (showCategoryTransition) {
    const nextCat =
      currentIndex < totalQuestions - 1
        ? currentCategory
        : 'communication';
    // Get the next category
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

  const canGoNext = selectedOption !== null || customText.trim().length > 0;
  const isLastQuestion = currentIndex === totalQuestions - 1;

  return (
    <main className="min-h-screen flex flex-col px-4 pt-8 pb-20">
      {/* Progress */}
      <div className="pt-4">
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

        {/* Options */}
        <div className="space-y-3 mb-4">
          {currentQuestion.options.map((option, i) => (
            <OptionCard
              key={option.value}
              option={option}
              index={i}
              isSelected={selectedOption === option.value}
              onSelect={() => selectOption(option.value)}
            />
          ))}

          {/* Other option */}
          {currentQuestion.allowOther && (
            <OptionCard
              option={{ label: "Something else...", value: "other", emoji: "✏️" }}
              index={currentQuestion.options.length}
              isSelected={selectedOption === 'other'}
              onSelect={() => selectOption('other')}
            />
          )}
        </div>

        {/* Custom text input */}
        <OtherInput
          isVisible={selectedOption === 'other'}
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
