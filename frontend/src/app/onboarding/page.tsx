'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, Sparkles, Loader2, SkipForward, AlertTriangle } from 'lucide-react';
import { useOnboarding } from '@/hooks/useOnboarding';
import ProgressBar from '@/components/onboarding/ProgressBar';
import QuestionCard from '@/components/onboarding/QuestionCard';
import OptionCard from '@/components/onboarding/OptionCard';
import OtherInput from '@/components/onboarding/OtherInput';
import CategoryTransition from '@/components/onboarding/CategoryTransition';
import BreathingOrb from '@/components/ambient/BreathingOrb';
import EsonaLogo from '@/components/layout/EsonaLogo';
import { getToken, getStoredUser, setStoredUser, getOnboardingStatus } from '@/api';

export default function OnboardingPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
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
    showSkipModal,
    setShowSkipModal,
    error,
    selectOption,
    setCustomText,
    goToNext,
    skipAllQuestions,
    goToPrevious,
    continuePastTransition,
    backToLogin,
    saveAndContinueLater,
  } = useOnboarding();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Check auth and onboarding status
  useEffect(() => {
    const token = getToken();
    console.log('[LOG] [OnboardingPage StatusCheck] hasToken:', !!token);
    if (!token) {
      console.log('[LOG] [OnboardingPage StatusCheck] Redirecting to /login due to missing token');
      router.push('/login');
      return;
    }

    const checkStatus = async () => {
      // First check local storage
      const user = getStoredUser();
      if (user) {
        console.log('[LOG] [OnboardingPage StatusCheck] storedUser found:', user.email, 'onboardingCompleted:', user.onboardingCompleted);
      } else {
        console.log('[LOG] [OnboardingPage StatusCheck] no storedUser found');
      }
      if (user && user.onboardingCompleted) {
        console.log('[LOG] [OnboardingPage StatusCheck] Redirecting to /chat because onboarding is marked complete locally');
        router.push('/chat');
        return;
      }

      // Double-check with backend
      try {
        console.log('[LOG] [OnboardingPage StatusCheck] Verifying onboarding status with backend...');
        const status = await getOnboardingStatus(token);
        console.log('[LOG] [OnboardingPage StatusCheck] Backend onboarding status returned:', status);
        if (status.completed) {
          if (user) {
            user.onboardingCompleted = true;
            setStoredUser(user);
          }
          console.log('[LOG] [OnboardingPage StatusCheck] Redirecting to /chat because backend status.completed is true');
          router.push('/chat');
        }
      } catch (err) {
        console.error('[LOG] [OnboardingPage StatusCheck] Failed to check onboarding status:', err);
      }
    };

    checkStatus();
  }, [router]);

  // Redirect after completion
  useEffect(() => {
    console.log('[LOG] [OnboardingPage CompletionEffect] isComplete:', isComplete);
    if (isComplete) {
      console.log('[LOG] [OnboardingPage CompletionEffect] Setting timer for /chat redirect (4000ms)');
      const timer = setTimeout(() => {
        console.log('[LOG] [OnboardingPage CompletionEffect] Timer fired. Redirecting to /chat');
        router.push('/chat');
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [isComplete, router]);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
      </div>
    );
  }

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
          <div className="relative w-32 h-32 mx-auto mb-8 flex items-center justify-center">
            <BreathingOrb size={120} className="absolute inset-0 opacity-60" />
            <EsonaLogo
              size={64}
              showParticles={true}
              glowIntensity="medium"
              className="relative z-10 logo-float"
            />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-4"
          >
            <Sparkles
              size={36}
              className="mx-auto mb-2 text-sky-400 animate-bounce"
            />
            <h2
              className="text-3xl font-bold mb-3 glow-text"
              style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
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
                background: 'var(--gradient-primary)',
                boxShadow: '0 0 10px rgba(56, 189, 248, 0.5)',
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
      background: 'personality',
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
      {/* Back to Login at the top left */}
      <div className="max-w-2xl mx-auto w-full flex justify-start mt-2">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={backToLogin}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-all duration-300 cursor-pointer hover:bg-white/5"
        >
          <ArrowLeft size={14} />
          Back to Login
        </motion.button>
      </div>

      {/* Header and Subtext */}
      <div className="text-center mt-4 mb-4">
        <h1
          className="text-2xl sm:text-3xl font-bold text-white flex items-center justify-center gap-2 mb-2"
          style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
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
      <div className="max-w-2xl mx-auto w-full flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-8">
        <div className="flex items-center justify-between sm:justify-start gap-3 w-full sm:w-auto">
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
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          {/* Skip ALL Questions button */}
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setShowSkipModal(true)}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 cursor-pointer text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-white/5"
          >
            <SkipForward size={14} />
            Skip Questions
          </motion.button>

          {/* Save & Continue Later button */}
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={saveAndContinueLater}
            disabled={isSubmitting}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 cursor-pointer text-sky-400 hover:text-sky-200 hover:bg-sky-500/10 border border-sky-500/20"
          >
            <Sparkles size={14} />
            Save & Continue Later
          </motion.button>
        </div>

        <div className="flex items-center justify-end w-full sm:w-auto">
          <motion.button
            whileHover={{ scale: canGoNext ? 1.03 : 1 }}
            whileTap={{ scale: canGoNext ? 0.97 : 1 }}
            onClick={goToNext}
            disabled={!canGoNext || isSubmitting}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: canGoNext
                ? 'var(--gradient-primary)'
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
      </div>

      {/* ━━━ Skip Confirmation Modal ━━━ */}
      <AnimatePresence>
        {showSkipModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-[100] flex items-center justify-center px-4"
            style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(8px)' }}
            onClick={() => setShowSkipModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="w-full max-w-md rounded-2xl p-6 sm:p-8 relative overflow-hidden"
              style={{
                background: 'rgba(10, 14, 30, 0.92)',
                border: '1px solid rgba(56, 189, 248, 0.15)',
                backdropFilter: 'blur(30px)',
                boxShadow: '0 0 60px rgba(56, 189, 248, 0.08), 0 20px 50px rgba(0, 0, 0, 0.5)',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Glow accent */}
              <div
                className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-1 rounded-full"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.5), transparent)',
                }}
              />

              {/* Icon */}
              <div className="flex items-center justify-center mb-5">
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center"
                  style={{
                    background: 'rgba(251, 191, 36, 0.1)',
                    border: '1px solid rgba(251, 191, 36, 0.2)',
                  }}
                >
                  <AlertTriangle size={26} className="text-amber-400" />
                </div>
              </div>

              {/* Title */}
              <h3
                className="text-xl font-bold text-center mb-3 text-white"
                style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
              >
                Skip All Questions?
              </h3>

              {/* Message */}
              <p className="text-sm text-center leading-relaxed mb-8" style={{ color: 'rgba(203, 213, 225, 0.9)' }}>
                Are you sure you want to skip these questions? Answering them helps Esona understand your personality, emotions, and communication style better, allowing more personalized and emotionally adaptive responses.
              </p>

              {/* Buttons */}
              <div className="flex flex-col gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowSkipModal(false)}
                  className="w-full py-3 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer"
                  style={{
                    background: 'var(--gradient-primary)',
                    color: 'var(--bg-primary)',
                    boxShadow: '0 0 20px rgba(56, 189, 248, 0.25)',
                  }}
                >
                  Continue Answering
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setShowSkipModal(false);
                    skipAllQuestions();
                  }}
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-xl text-sm font-medium transition-all duration-300 cursor-pointer disabled:opacity-50"
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    color: 'rgba(203, 213, 225, 0.7)',
                  }}
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 size={14} className="animate-spin" />
                      Skipping...
                    </span>
                  ) : (
                    'Skip Anyway'
                  )}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
