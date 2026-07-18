'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
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
import FullPageTransition from '@/components/layout/FullPageTransition';
import { cn } from '@/utils';

// Category colors for atmospheric focus glows
const CATEGORY_COLORS: Record<string, { accent: string; glow: string; bg: string }> = {
  background: { accent: '#3b82f6', glow: 'rgba(59, 130, 246, 0.20)', bg: 'rgba(59, 130, 246, 0.08)' },
  personality: { accent: '#38bdf8', glow: 'rgba(56, 189, 248, 0.20)', bg: 'rgba(56, 189, 248, 0.08)' },
  emotion: { accent: '#a78bfa', glow: 'rgba(167, 139, 250, 0.20)', bg: 'rgba(167, 139, 250, 0.08)' },
  hobbies: { accent: '#34d399', glow: 'rgba(52, 211, 153, 0.20)', bg: 'rgba(52, 211, 153, 0.08)' },
  communication: { accent: '#f472b6', glow: 'rgba(244, 114, 182, 0.20)', bg: 'rgba(244, 114, 182, 0.08)' },
};

const DEFAULT_COLORS = { accent: '#38bdf8', glow: 'rgba(56, 189, 248, 0.25)', bg: 'rgba(56, 189, 248, 0.08)' };

// Helper text based on question type / configuration
const getHelperText = (q: any) => {
  if (q.inputType === 'age') {
    return 'Enter your age.';
  }
  if (q.inputType === 'text') {
    return "Share as much or as little as you'd like.";
  }
  
  // Single select questions
  const singleSelectIds = [4, 7, 24, 26];
  if (singleSelectIds.includes(q.id)) {
    return 'Choose the option that feels closest to you.';
  }
  
  if (q.allowOther) {
    return 'Select one or more choices, or add your own answer.';
  }
  
  return 'Select one or more choices.';
};

export default function OnboardingPage() {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  // showLoader is reserved for onboarding-complete redirect sequence (not used for status check)
  const [showLoader, setShowLoader] = useState(false);
  const [isVerifyingStatus, setIsVerifyingStatus] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
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
    isLoadingData,
    saveStatus,
  } = useOnboarding();

  const canGoNext = selectedOptions.length > 0 || customText.trim().length > 0;

  const mountTimeRef = useRef<number>(0);
  const hasLoggedTimingRef = useRef<boolean>(false);

  useEffect(() => {
    mountTimeRef.current = performance.now();
    setMounted(true);
  }, []);

  // Performance logging for question loading
  useEffect(() => {
    if (!isLoadingData && mountTimeRef.current > 0 && !hasLoggedTimingRef.current) {
      const duration = performance.now() - mountTimeRef.current;
      console.log(`[PERF] getOnboardingAnswers (question data loading) duration: ${duration.toFixed(2)} ms`);
    }
  }, [isLoadingData]);

  // Check auth and onboarding status with timeout budget
  useEffect(() => {
    const token = getToken();
    console.log('[LOG] [OnboardingPage StatusCheck] hasToken:', !!token);
    if (!token) {
      console.log('[LOG] [OnboardingPage StatusCheck] Redirecting to /login due to missing token');
      router.push('/login');
      return;
    }

    const checkStatus = async () => {
      const user = getStoredUser();
      if (user && user.onboardingCompleted) {
        console.log('[LOG] [OnboardingPage StatusCheck] Redirecting to /chat because onboarding is marked complete locally');
        router.push('/chat');
        return;
      }

      let hasTimedOut = false;
      const budgetTimeout = setTimeout(() => {
        hasTimedOut = true;
        const totalBlockingTime = performance.now() - mountTimeRef.current;
        console.log(`[PERF] [onboarding] Status check exceeded 2000ms budget. Unblocking UI. Total blocking loader duration: ${totalBlockingTime.toFixed(2)} ms`);
        setIsVerifyingStatus(false);
      }, 2000);

      try {
        console.log('[LOG] [OnboardingPage StatusCheck] Verifying onboarding status with backend...');
        const statusStartTime = performance.now();
        const status = await getOnboardingStatus(token);
        const statusDuration = performance.now() - statusStartTime;
        console.log(`[PERF] getOnboardingStatus API duration: ${statusDuration.toFixed(2)} ms`);

        clearTimeout(budgetTimeout);

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
      } finally {
        clearTimeout(budgetTimeout);
        if (!hasTimedOut) {
          const totalBlockingTime = performance.now() - mountTimeRef.current;
          console.log(`[PERF] [onboarding] Status check completed within budget. Total blocking loader duration: ${totalBlockingTime.toFixed(2)} ms`);
          setIsVerifyingStatus(false);
        }
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

  const handleNext = async () => {
    if (isTransitioning || !canGoNext || isSubmitting) return;
    setIsTransitioning(true);
    await goToNext();
    setTimeout(() => setIsTransitioning(false), 500);
  };

  const handlePrevious = async () => {
    if (isTransitioning || currentIndex === 0) return;
    setIsTransitioning(true);
    await goToPrevious();
    setTimeout(() => setIsTransitioning(false), 500);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (typeof window !== 'undefined' && window.innerWidth < 768) {
        return;
      }

      const activeEl = document.activeElement;
      if (activeEl) {
        const tagName = activeEl.tagName.toLowerCase();
        if (tagName === 'input' || tagName === 'textarea' || activeEl.hasAttribute('contenteditable')) {
          if (e.key === 'Enter') {
            const isAgeInput = activeEl.getAttribute('placeholder')?.includes('age') || activeEl.id === 'age-input';
            if (isAgeInput && canGoNext && !isSubmitting && !isTransitioning) {
              e.preventDefault();
              handleNext();
            }
          }
          return;
        }
      }

      if (e.key === 'Enter') {
        if (canGoNext && !isSubmitting && !isTransitioning) {
          e.preventDefault();
          handleNext();
        }
      } else if (e.key === 'ArrowLeft') {
        if (currentIndex > 0 && !isTransitioning) {
          e.preventDefault();
          handlePrevious();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [canGoNext, currentIndex, isSubmitting, isTransitioning]);

  const questionContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (questionContainerRef.current) {
      const rect = questionContainerRef.current.getBoundingClientRect();
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const targetY = rect.top + scrollTop - 80;
      window.scrollTo({
        top: Math.max(0, targetY),
        behavior: 'smooth',
      });
    }
  }, [currentIndex]);

  if (!mounted || isVerifyingStatus) {
    return (
      <AnimatePresence>
        <FullPageTransition
          message="Checking your progress..."
        />
      </AnimatePresence>
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

  const isLastQuestion = currentIndex === totalQuestions - 1;

  const colors = CATEGORY_COLORS[currentCategory] || DEFAULT_COLORS;

  // Development runtime inspection logging
  console.log('Question ID:', currentQuestion.id);
  console.log('Question Text:', currentQuestion.text);
  console.log('Question Type:', currentQuestion.inputType || 'select');
  console.log('Current Index:', currentIndex);
  console.log('Display Number:', currentIndex + 1);

  // Grid layout selector based on option characteristics
  const totalOptions = currentQuestion.options.length + (currentQuestion.allowOther ? 1 : 0);
  const hasLongOptions = currentQuestion.options.some((opt: any) => opt.label.length > 25);
  
  // Decide grid columns class
  let gridColsClass = "grid-cols-1";
  if (currentQuestion.inputType === 'age') {
    gridColsClass = "grid-cols-1";
  } else if (hasLongOptions) {
    gridColsClass = "grid-cols-1";
  } else if (totalOptions <= 3) {
    gridColsClass = "grid-cols-1 sm:grid-cols-2 md:grid-cols-3";
  } else {
    gridColsClass = "grid-cols-2";
  }

  // Question variants for animation
  const questionVariants = {
    enter: (dir: number) => ({
      x: shouldReduceMotion ? 0 : (dir > 0 ? 30 : -30),
      opacity: 0,
      filter: shouldReduceMotion ? 'none' : 'blur(4px)',
    }),
    center: {
      x: 0,
      opacity: 1,
      filter: 'none',
    },
    exit: (dir: number) => ({
      x: shouldReduceMotion ? 0 : (dir > 0 ? -30 : 30),
      opacity: 0,
      filter: shouldReduceMotion ? 'none' : 'blur(4px)',
    }),
  };

  return (
    <main className="min-h-screen flex flex-col px-4 pt-2 sm:pt-4 pb-40 sm:pb-12 relative z-10">
      {/* Background Overlay Treatments */}
      <div className="absolute inset-0 -z-10 pointer-events-none">
        {/* Layer 1: Dark overlay for overall readability */}
        <div
          className="absolute inset-0"
          style={{
            background: 'linear-gradient(180deg, rgba(4, 6, 20, 0.75) 0%, rgba(4, 6, 20, 0.55) 40%, rgba(4, 6, 20, 0.60) 70%, rgba(4, 6, 20, 0.85) 100%)',
          }}
        />
        {/* Layer 2: Center-focused radial gradient for question focus */}
        <div
          className="absolute inset-0"
          style={{
            background: 'radial-gradient(ellipse at center, rgba(3, 7, 20, 0.70) 0%, rgba(3, 7, 20, 0.40) 45%, rgba(3, 7, 20, 0.05) 80%)',
          }}
        />
        {/* Layer 3: Atmospheric category glow */}
        <div
          className="absolute inset-0"
          style={{
            background: `radial-gradient(ellipse at center 40%, ${colors.glow} 0%, transparent 60%)`,
            opacity: 0.5,
          }}
        />
      </div>

      {/* Back to Login at the top left */}
      <div className="max-w-2xl mx-auto w-full flex justify-start mt-1">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={backToLogin}
          className="flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-all duration-300 cursor-pointer hover:bg-white/5"
        >
          <ArrowLeft size={14} />
          Back to Login
        </motion.button>
      </div>

      {/* Header and Subtext */}
      <div className="text-center mt-2 mb-2 sm:mb-4">
        <h1
          className="text-xl sm:text-2xl font-bold text-white flex items-center justify-center gap-2 mb-1"
          style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          🧠 Help Esona understand you better
        </h1>
        <p className="text-[11px] sm:text-xs max-w-lg mx-auto" style={{ color: 'var(--text-muted)' }}>
          These questions personalize your emotional insights, personality analysis, and AI responses.
        </p>
      </div>

      {/* Progress */}
      <div className="max-w-2xl mx-auto w-full mb-3 sm:mb-4">
        <ProgressBar
          currentQuestion={currentIndex}
          totalQuestions={totalQuestions}
          currentCategory={currentCategory}
          saveStatus={saveStatus}
        />
      </div>

      {/* Question */}
      <div ref={questionContainerRef} className="flex-1 flex flex-col justify-center max-w-2xl mx-auto w-full min-h-[260px] sm:min-h-[300px]">
        {isLoadingData ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-400">
            <Loader2 className="animate-spin text-sky-400" size={32} />
            <p className="text-sm font-medium">Syncing your progress...</p>
          </div>
        ) : (
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentQuestion.id}
              custom={direction}
              variants={questionVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                x: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.35 },
                filter: { duration: 0.35 }
              }}
              className="w-full flex-1 flex flex-col justify-center"
            >
              <QuestionCard
                question={currentQuestion}
                displayNumber={currentIndex + 1}
              />

              {/* Small Helper Text */}
              <p className="text-xs text-slate-400 mb-2 sm:mb-3 text-center italic">
                {getHelperText(currentQuestion)}
              </p>

              {/* Options */}
              <div className={cn("grid gap-2 sm:gap-3 mb-4", gridColsClass)}>
                {currentQuestion.inputType === 'age' || currentQuestion.id === 27 ? (
                  <div className="flex flex-col gap-2 col-span-full">
                    <input
                      id="age-input"
                      type="text"
                      pattern="\d*"
                      inputMode="numeric"
                      value={customText}
                      onFocus={() => setIsInputFocused(true)}
                      onBlur={() => setIsInputFocused(false)}
                      onChange={(e) => {
                        setCustomText(e.target.value);
                      }}
                      placeholder="Enter your age (e.g. 21)"
                      className="w-full px-4 py-3 rounded-xl text-center text-base font-semibold focus:outline-none transition-all duration-200 placeholder-slate-400"
                      style={{
                        background: 'rgba(8, 15, 35, 0.70)',
                        border: isInputFocused 
                          ? '1px solid rgba(34, 211, 238, 0.7)' 
                          : customText 
                          ? '1px solid rgba(34, 211, 238, 0.4)' 
                          : '1px solid rgba(148, 163, 184, 0.25)',
                        boxShadow: isInputFocused 
                          ? '0 0 16px rgba(34, 211, 238, 0.3)' 
                          : customText 
                          ? '0 0 10px rgba(34, 211, 238, 0.15)' 
                          : '0 2px 4px rgba(0, 0, 0, 0.2)',
                        backdropFilter: 'blur(8px)',
                        color: '#f8fafc',
                        caretColor: 'var(--accent-cyan)',
                      }}
                    />
                  </div>
                ) : (
                  currentQuestion.options.map((option, i) => (
                    <OptionCard
                      key={option.value}
                      option={option}
                      index={i}
                      isSelected={selectedOptions.includes(option.value)}
                      onSelect={() => selectOption(option.value)}
                    />
                  ))
                )}

                {/* Other option */}
                {(currentQuestion.inputType !== 'age' && currentQuestion.id !== 27) && currentQuestion.allowOther && (
                  <OptionCard
                    option={{ label: "Something else...", value: "other", emoji: "✏️" }}
                    index={currentQuestion.options.length}
                    isSelected={selectedOptions.includes('other')}
                    onSelect={() => selectOption('other')}
                  />
                )}
              </div>

              {/* Custom text input */}
              {(currentQuestion.inputType !== 'age' && currentQuestion.id !== 27) && (
                <OtherInput
                  isVisible={selectedOptions.includes('other')}
                  value={customText}
                  onChange={setCustomText}
                />
              )}

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
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Bottom gradient for navigation readability */}
      <div
        className="absolute bottom-0 left-0 right-0 h-28 pointer-events-none -z-10"
        style={{
          background: 'linear-gradient(to top, rgba(4, 6, 20, 0.90) 0%, rgba(4, 6, 20, 0.60) 50%, transparent 100%)',
        }}
      />

      {/* Navigation buttons */}
      <div className="max-w-2xl mx-auto w-full mt-6 sm:mt-8 relative z-10">
        {/* Mobile Layout: Fixed bottom bar */}
        <div className="sm:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/80 backdrop-blur-md border-t border-white/5 px-4 pt-3" style={{ paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))' }}>
          <div className="max-w-2xl mx-auto flex flex-col gap-3">
            {/* Top Row: Back and Save & Continue Later */}
            <div className="flex items-center gap-2">
              <motion.button
                whileHover={{ scale: (currentIndex === 0 || isLoadingData || isTransitioning) ? 1 : 1.02 }}
                whileTap={{ scale: (currentIndex === 0 || isLoadingData || isTransitioning) ? 1 : 0.98 }}
                onClick={handlePrevious}
                disabled={currentIndex === 0 || isLoadingData || isTransitioning}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-semibold border border-white/10 text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed"
                style={{ background: 'rgba(8, 15, 35, 0.60)' }}
              >
                <ArrowLeft size={14} />
                Back
              </motion.button>
              <motion.button
                whileHover={{ scale: (isSubmitting || isLoadingData) ? 1 : 1.02 }}
                whileTap={{ scale: (isSubmitting || isLoadingData) ? 1 : 0.98 }}
                onClick={saveAndContinueLater}
                disabled={isSubmitting || isLoadingData}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-semibold border border-sky-500/30 text-sky-400 disabled:opacity-30"
                style={{ background: 'rgba(8, 15, 35, 0.60)' }}
              >
                <Sparkles size={12} />
                Save Later
              </motion.button>
            </div>

            {/* Primary Next Action */}
            <motion.button
              whileHover={{ scale: (canGoNext && !isSubmitting && !isLoadingData && !isTransitioning) ? 1.02 : 1 }}
              whileTap={{ scale: (canGoNext && !isSubmitting && !isLoadingData && !isTransitioning) ? 0.98 : 1 }}
              onClick={handleNext}
              disabled={!canGoNext || isSubmitting || isLoadingData || isTransitioning}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold transition-all duration-300 disabled:cursor-not-allowed"
              style={{
                background: (canGoNext && !isLoadingData)
                  ? 'var(--gradient-primary)'
                  : 'rgba(30, 40, 60, 0.6)',
                color: (canGoNext && !isLoadingData) ? 'var(--bg-primary)' : 'rgba(148, 163, 184, 0.6)',
                border: (canGoNext && !isLoadingData) ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
                opacity: (canGoNext && !isLoadingData) ? 1 : 0.55,
              }}
              animate={canGoNext && !isSubmitting && !isLoadingData && !isTransitioning ? {
                scale: [1, 1.02, 1],
                boxShadow: '0 0 15px rgba(56, 189, 248, 0.35)',
              } : {
                scale: 1,
                boxShadow: 'none',
              }}
              transition={{ duration: 0.3 }}
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

            {/* Subtle Skip Questions link */}
            <button
              onClick={() => setShowSkipModal(true)}
              disabled={isSubmitting || isLoadingData}
              className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors py-1 disabled:opacity-30 text-center font-medium"
            >
              Skip Questions
            </button>
          </div>
        </div>

        {/* Desktop/Tablet Layout: Single horizontal row */}
        <div className="hidden sm:flex items-center justify-between gap-4">
          <div className="flex items-center justify-start gap-3">
            <motion.button
              whileHover={{ scale: (currentIndex === 0 || isLoadingData || isTransitioning) ? 1 : 1.03 }}
              whileTap={{ scale: (currentIndex === 0 || isLoadingData || isTransitioning) ? 1 : 0.97 }}
              onClick={handlePrevious}
              disabled={currentIndex === 0 || isLoadingData || isTransitioning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                background: 'rgba(8, 15, 35, 0.60)',
                border: '1px solid rgba(148, 163, 184, 0.20)',
                color: 'var(--text-secondary)',
              }}
            >
              <ArrowLeft size={16} />
              Back
            </motion.button>
          </div>

          <div className="flex items-center gap-3">
            {/* Skip ALL Questions button */}
            <motion.button
              whileHover={{ scale: (isSubmitting || isLoadingData) ? 1 : 1.03 }}
              whileTap={{ scale: (isSubmitting || isLoadingData) ? 1 : 0.97 }}
              onClick={() => setShowSkipModal(true)}
              disabled={isSubmitting || isLoadingData}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                background: 'rgba(8, 15, 35, 0.60)',
                border: '1px solid rgba(148, 163, 184, 0.20)',
                color: 'rgba(203, 213, 225, 0.8)',
              }}
            >
              <SkipForward size={14} />
              Skip Questions
            </motion.button>

            {/* Save & Continue Later button */}
            <motion.button
              whileHover={{ scale: (isSubmitting || isLoadingData) ? 1 : 1.03 }}
              whileTap={{ scale: (isSubmitting || isLoadingData) ? 1 : 0.97 }}
              onClick={saveAndContinueLater}
              disabled={isSubmitting || isLoadingData}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                background: 'rgba(8, 15, 35, 0.60)',
                border: '1px solid rgba(34, 211, 238, 0.4)',
                color: 'var(--accent-cyan)',
              }}
            >
              <Sparkles size={14} />
              Save & Continue Later
            </motion.button>
          </div>

          <div className="flex items-center justify-end">
            <motion.button
              whileHover={{ scale: (canGoNext && !isSubmitting && !isLoadingData && !isTransitioning) ? 1.03 : 1 }}
              whileTap={{ scale: (canGoNext && !isSubmitting && !isLoadingData && !isTransitioning) ? 0.97 : 1 }}
              onClick={handleNext}
              disabled={!canGoNext || isSubmitting || isLoadingData || isTransitioning}
              className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 cursor-pointer disabled:cursor-not-allowed"
              style={{
                background: (canGoNext && !isLoadingData)
                  ? 'var(--gradient-primary)'
                  : 'rgba(30, 40, 60, 0.6)',
                color: (canGoNext && !isLoadingData) ? 'var(--bg-primary)' : 'rgba(148, 163, 184, 0.6)',
                border: (canGoNext && !isLoadingData) ? 'none' : '1px solid rgba(255, 255, 255, 0.08)',
                opacity: (canGoNext && !isLoadingData) ? 1 : 0.55,
              }}
              animate={canGoNext && !isSubmitting && !isLoadingData && !isTransitioning ? {
                scale: [1, 1.02, 1],
                boxShadow: '0 0 15px rgba(56, 189, 248, 0.35)',
              } : {
                scale: 1,
                boxShadow: 'none',
              }}
              transition={{ duration: 0.3 }}
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
