'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, ArrowRight, X, Check, Loader2,
  MessageCircle, AlertCircle, Sparkles,
} from 'lucide-react';
import { questions } from '@/data/questions';
import { Question } from '@/types';
import {
  getToken, saveOnboardingAnswer, recalculateProfile,
} from '@/api';
import { upsertSingleAnswerToSupabase } from '@/api/supabaseSync';

// ─── Types ──────────────────────────────────────────────────────────
interface SavedAnswer {
  question_id: number;
  category: string;
  selected_answers: string[];
  custom_answer: string | null;
}

interface SequentialQuestionnaireProps {
  initialAnswers: SavedAnswer[];
  startIndex: number;
  onClose: (didSave: boolean) => void;
}

// ─── Color helpers (same palette as Knowing Me page) ────────────────
const CATEGORY_COLORS: Record<string, { accent: string; glow: string; bg: string }> = {
  background: { accent: 'rgb(59, 130, 246)', glow: 'rgba(59, 130, 246, 0.15)', bg: 'rgba(59, 130, 246, 0.06)' },
  personality: { accent: 'rgb(56, 189, 248)', glow: 'rgba(56, 189, 248, 0.15)', bg: 'rgba(56, 189, 248, 0.06)' },
  emotion: { accent: 'rgb(167, 139, 250)', glow: 'rgba(167, 139, 250, 0.15)', bg: 'rgba(167, 139, 250, 0.06)' },
  hobbies: { accent: 'rgb(52, 211, 153)', glow: 'rgba(52, 211, 153, 0.15)', bg: 'rgba(52, 211, 153, 0.06)' },
  communication: { accent: 'rgb(244, 114, 182)', glow: 'rgba(244, 114, 182, 0.15)', bg: 'rgba(244, 114, 182, 0.06)' },
};

const CATEGORY_LABELS: Record<string, string> = {
  background: 'About You',
  personality: 'Personality & Behavior',
  emotion: 'Emotional State & Stress',
  hobbies: 'Hobbies & Comfort Zone',
  communication: 'Communication & Preferences',
};

// ─── Component ──────────────────────────────────────────────────────
export default function SequentialQuestionnaire({
  initialAnswers,
  startIndex,
  onClose,
}: SequentialQuestionnaireProps) {
  const router = useRouter();
  const [currentIndex, setCurrentIndex] = useState(startIndex);
  const [direction, setDirection] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  // Per-question local answer state
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [customText, setCustomText] = useState('');

  // Track which questions have been saved (by question_id)
  const [savedIds, setSavedIds] = useState<Set<number>>(() => {
    const set = new Set<number>();
    for (const ans of initialAnswers) {
      const hasAnswer = (ans.selected_answers && ans.selected_answers.length > 0) ||
        (ans.custom_answer && ans.custom_answer.trim().length > 0);
      if (hasAnswer) set.add(ans.question_id);
    }
    return set;
  });

  // Store all answers locally for back-navigation
  const [localAnswers, setLocalAnswers] = useState<Map<number, { selected: string[]; custom: string }>>(() => {
    const map = new Map<number, { selected: string[]; custom: string }>();
    for (const ans of initialAnswers) {
      map.set(ans.question_id, {
        selected: ans.selected_answers || [],
        custom: ans.custom_answer || '',
      });
    }
    return map;
  });

  const currentQuestion = questions[currentIndex];
  const totalQuestions = questions.length;
  const colors = CATEGORY_COLORS[currentQuestion?.category] || CATEGORY_COLORS.background;

  // Load saved answer when navigating to a question
  useEffect(() => {
    if (!currentQuestion) return;
    const saved = localAnswers.get(currentQuestion.id);
    if (saved) {
      setSelectedOptions(saved.selected);
      setCustomText(saved.custom);
    } else {
      setSelectedOptions([]);
      setCustomText('');
    }
    setError(null);
  }, [currentIndex, currentQuestion, localAnswers]);

  // Lock body scroll on mount, restore on unmount
  useEffect(() => {
    const prevBodyOverflow = document.body.style.overflow;
    const prevHtmlOverflow = document.documentElement.style.overflow;

    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = prevBodyOverflow;
      document.documentElement.style.overflow = prevHtmlOverflow;
    };
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isComplete || isSaving) return;
      if (e.key === 'Escape') {
        handleSaveAndExit();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isComplete, isSaving, currentIndex, selectedOptions, customText]);

  // ─── Answer handlers ────────────────────────────────────
  const toggleOption = (value: string) => {
    setSelectedOptions(prev => {
      if (prev.includes(value)) return prev.filter(v => v !== value);
      return [...prev, value];
    });
    setError(null);
  };

  const handleCustomTextChange = (text: string) => {
    setCustomText(text);
    // Auto-select 'other' when typing custom text
    if (text.trim() && !selectedOptions.includes('other') && currentQuestion?.allowOther) {
      setSelectedOptions(prev => [...prev, 'other']);
    }
    setError(null);
  };

  // ─── Validation ─────────────────────────────────────────
  const validateCurrentAnswer = (): string | null => {
    const q = currentQuestion;
    if (!q) return 'Invalid question';

    // Age question (Q27) — special validation
    if (q.id === 27) {
      const ageStr = customText.trim();
      if (!ageStr) return 'Please enter your age.';
      if (!/^\d+$/.test(ageStr)) return 'Please enter a valid age as a whole number.';
      const ageVal = parseInt(ageStr, 10);
      if (ageVal < 1) return 'Age must be at least 1.';
      if (ageVal > 120) return 'Please enter a valid age (1–120).';
      return null;
    }

    // All other questions — need at least one selection or custom text
    const hasSelection = selectedOptions.length > 0;
    const hasCustom = customText.trim().length > 0;
    if (!hasSelection && !hasCustom) return null; // Allow skipping — it's not an error, we just don't save
    return null;
  };

  const hasAnswerContent = (): boolean => {
    if (currentQuestion?.id === 27) return customText.trim().length > 0;
    return selectedOptions.length > 0 || customText.trim().length > 0;
  };

  // ─── Save current answer ────────────────────────────────
  const saveCurrentAnswer = useCallback(async (): Promise<boolean> => {
    const token = getToken();
    if (!token) {
      setError('Authentication expired. Please log in again.');
      return false;
    }

    const q = currentQuestion;
    if (!q) return false;

    // Validate
    const validationError = validateCurrentAnswer();
    if (validationError) {
      setError(validationError);
      return false;
    }

    // If no answer content, skip save (not an error)
    if (!hasAnswerContent()) return true;

    setIsSaving(true);
    setError(null);

    try {
      const answerPayload = {
        questionId: q.id,
        category: q.category,
        selectedAnswers: q.id === 27 ? [] : selectedOptions,
        customAnswer: q.id === 27 ? customText.trim() : (customText.trim() || undefined),
      };

      // Save to backend (handles upsert + profile field sync)
      await saveOnboardingAnswer(answerPayload, token);

      // Save to Supabase directly
      await upsertSingleAnswerToSupabase({
        questionId: q.id,
        questionText: q.text,
        category: q.category,
        selectedAnswers: answerPayload.selectedAnswers,
        customAnswer: answerPayload.customAnswer,
      });

      // Update local tracking
      setSavedIds(prev => new Set([...prev, q.id]));
      setLocalAnswers(prev => {
        const next = new Map(prev);
        next.set(q.id, { selected: answerPayload.selectedAnswers, custom: answerPayload.customAnswer || '' });
        return next;
      });

      return true;
    } catch (err: any) {
      console.error('[SequentialQ] Save failed:', err);
      setError(err?.message || 'Failed to save. Please try again.');
      return false;
    } finally {
      setIsSaving(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentQuestion, selectedOptions, customText]);

  // ─── Navigation ─────────────────────────────────────────
  const goNext = async () => {
    const success = await saveCurrentAnswer();
    if (!success && hasAnswerContent()) return; // Block if save failed with content

    if (currentIndex >= totalQuestions - 1) {
      // Last question — trigger recalculation and show completion
      const token = getToken();
      if (token) {
        try { await recalculateProfile(token); } catch { /* non-critical */ }
      }
      setIsComplete(true);
      return;
    }

    setDirection(1);
    setCurrentIndex(prev => prev + 1);
  };

  const goBack = () => {
    if (currentIndex <= 0) return;
    // Store current unsaved state before navigating
    if (currentQuestion) {
      setLocalAnswers(prev => {
        const next = new Map(prev);
        next.set(currentQuestion.id, { selected: selectedOptions, custom: customText });
        return next;
      });
    }
    setDirection(-1);
    setCurrentIndex(prev => prev - 1);
    setError(null);
  };

  const handleSaveAndExit = async () => {
    // If there's content, save it first
    if (hasAnswerContent()) {
      const success = await saveCurrentAnswer();
      if (!success) return; // Don't close if save failed
    }
    // Recalculate profile on exit
    const token = getToken();
    if (token) {
      try { await recalculateProfile(token); } catch { /* non-critical */ }
    }
    onClose(true);
  };

  // Count how many are now saved
  const totalSaved = savedIds.size;

  // ─── Slide animation variants ───────────────────────────
  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 300 : -300, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -300 : 300, opacity: 0 }),
  };

  // ─── Completion Screen ──────────────────────────────────
  if (isComplete) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center"
        style={{ background: '#040614' }}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="max-w-md w-full mx-4 text-center"
        >
          {/* Celebration glow */}
          <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            className="w-32 h-32 mx-auto mb-8 rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(56, 189, 248, 0.3), transparent 70%)',
            }}
          />

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Sparkles size={40} className="mx-auto mb-4" style={{ color: 'var(--accent-cyan)' }} />
            <h2
              className="text-2xl font-bold mb-3"
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-space-grotesk), sans-serif',
              }}
            >
              That&apos;s it — Buddy knows you a little better now.
            </h2>

            <div className="flex items-center justify-center gap-2 mb-4">
              <span
                className="text-lg font-bold"
                style={{ color: 'var(--accent-cyan)' }}
              >
                {totalQuestions}/{totalQuestions} answered
              </span>
              <Check size={20} className="text-emerald-400" />
            </div>

            <p className="text-sm text-slate-400 mb-10 max-w-sm mx-auto">
              Your answers will help Buddy respond in a way that feels more natural to you.
            </p>
          </motion.div>

          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            <button
              onClick={() => onClose(true)}
              className="w-full sm:w-auto px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer"
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: 'var(--text-secondary)',
              }}
            >
              Done
            </button>
            <button
              onClick={() => router.push('/chat')}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-sm font-bold transition-all duration-200 cursor-pointer"
              style={{
                background: 'var(--gradient-primary)',
                color: 'var(--bg-primary)',
                boxShadow: '0 0 20px rgba(56, 189, 248, 0.3)',
              }}
            >
              <MessageCircle size={16} />
              Start Chatting
            </button>
          </motion.div>
        </motion.div>
      </motion.div>
    );
  }

  // ─── Main questionnaire UI ──────────────────────────────
  const q = currentQuestion;
  if (!q) return null;

  const positionProgress = ((currentIndex + 1) / totalQuestions) * 100;
  const categoryLabel = CATEGORY_LABELS[q.category] || q.categoryLabel;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] h-dvh overflow-hidden flex flex-col bg-[#040614]"
      style={{ background: '#040614' }}
    >
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 sm:px-6 pt-4 pb-3 border-b border-white/5 bg-[#040614]">
        <div>
          <h2
            className="text-lg font-bold"
            style={{
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-space-grotesk), sans-serif',
            }}
          >
            Knowing You Better
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {categoryLabel}
          </p>
        </div>
        <button
          onClick={handleSaveAndExit}
          disabled={isSaving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer disabled:opacity-50"
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: 'var(--text-secondary)',
          }}
        >
          <X size={14} />
          Save & Exit
        </button>
      </div>

      {/* ── Position Progress Bar ──────────────────────── */}
      <div className="flex-shrink-0 px-4 sm:px-6 pt-3 pb-3 bg-[#040614]">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-500">
            Question {currentIndex + 1} of {totalQuestions}
          </span>
          <span className="text-xs font-medium" style={{ color: colors.accent }}>
            {totalSaved}/{totalQuestions} saved
          </span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <motion.div
            initial={false}
            animate={{ width: `${positionProgress}%` }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
            className="h-full rounded-full"
            style={{
              background: `linear-gradient(90deg, ${colors.accent}, ${colors.accent}dd)`,
              boxShadow: `0 0 8px ${colors.glow}`,
            }}
          />
        </div>
      </div>

      {/* ── Question Content ───────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-6 sm:py-10 overscroll-contain bg-[#040614]">
        <div className="max-w-lg mx-auto">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={q.id}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              {/* Question badge + text */}
              <div className="mb-6">
                <span
                  className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-md mb-3"
                  style={{ background: colors.bg, color: colors.accent }}
                >
                  Q{currentIndex + 1}
                </span>
                <h3
                  className="text-xl sm:text-2xl font-bold leading-snug"
                  style={{
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-space-grotesk), sans-serif',
                  }}
                >
                  {q.text}
                </h3>
              </div>

              {/* Answer input */}
              {q.id === 27 ? (
                /* ── Age: numeric input ── */
                <div className="space-y-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="\d*"
                    value={customText}
                    onChange={e => handleCustomTextChange(e.target.value)}
                    placeholder="Enter your age (e.g. 21)"
                    autoFocus
                    className="w-full px-4 py-3 text-sm rounded-xl text-white placeholder-slate-500 focus:outline-none transition-all duration-200"
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: `1px solid ${customText ? colors.accent + '60' : 'rgba(255, 255, 255, 0.08)'}`,
                      boxShadow: customText ? `0 0 12px ${colors.glow}` : 'none',
                    }}
                  />
                  <p className="text-[11px] text-slate-500">Whole number between 1 and 120</p>
                </div>
              ) : (
                /* ── Option selection ── */
                <div className="space-y-2">
                  {q.options.map(opt => {
                    const isSelected = selectedOptions.includes(opt.value);
                    return (
                      <motion.button
                        key={opt.value}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={() => toggleOption(opt.value)}
                        className="w-full flex items-center gap-3 p-3.5 rounded-xl text-left cursor-pointer transition-all duration-200"
                        style={{
                          background: isSelected ? colors.bg : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${isSelected ? colors.accent + '50' : 'rgba(255, 255, 255, 0.05)'}`,
                          boxShadow: isSelected ? `0 0 12px ${colors.glow}` : 'none',
                        }}
                      >
                        <div
                          className="w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-all duration-200"
                          style={{
                            borderColor: isSelected ? colors.accent : 'rgba(255, 255, 255, 0.15)',
                            background: isSelected ? colors.accent : 'transparent',
                          }}
                        >
                          {isSelected && <Check size={12} className="text-white" />}
                        </div>
                        <span className="text-base">{opt.emoji}</span>
                        <span
                          className="text-sm font-medium"
                          style={{ color: isSelected ? colors.accent : 'var(--text-secondary)' }}
                        >
                          {opt.label}
                        </span>
                      </motion.button>
                    );
                  })}

                  {/* "Other" option */}
                  {q.allowOther && (
                    <div className="space-y-2">
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={() => toggleOption('other')}
                        className="w-full flex items-center gap-3 p-3.5 rounded-xl text-left cursor-pointer transition-all duration-200"
                        style={{
                          background: selectedOptions.includes('other') ? colors.bg : 'rgba(255, 255, 255, 0.02)',
                          border: `1px solid ${selectedOptions.includes('other') ? colors.accent + '50' : 'rgba(255, 255, 255, 0.05)'}`,
                        }}
                      >
                        <div
                          className="w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-all duration-200"
                          style={{
                            borderColor: selectedOptions.includes('other') ? colors.accent : 'rgba(255, 255, 255, 0.15)',
                            background: selectedOptions.includes('other') ? colors.accent : 'transparent',
                          }}
                        >
                          {selectedOptions.includes('other') && <Check size={12} className="text-white" />}
                        </div>
                        <span className="text-base">✏️</span>
                        <span
                          className="text-sm font-medium"
                          style={{ color: selectedOptions.includes('other') ? colors.accent : 'var(--text-secondary)' }}
                        >
                          Something else...
                        </span>
                      </motion.button>

                      {selectedOptions.includes('other') && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          className="pl-11"
                        >
                          <input
                            type="text"
                            value={customText}
                            onChange={e => handleCustomTextChange(e.target.value)}
                            placeholder="Type your own answer..."
                            autoFocus
                            className="w-full px-3 py-2.5 text-sm rounded-lg text-white placeholder-slate-500 focus:outline-none"
                            style={{
                              background: 'rgba(255, 255, 255, 0.04)',
                              border: '1px solid rgba(255, 255, 255, 0.08)',
                            }}
                          />
                        </motion.div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* ── Error banner ──────────────────────────── */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 p-3 rounded-xl flex items-center gap-2.5"
                style={{
                  background: 'rgba(244, 114, 182, 0.08)',
                  border: '1px solid rgba(244, 114, 182, 0.2)',
                }}
              >
                <AlertCircle size={16} className="text-pink-400 shrink-0" />
                <p className="text-xs text-pink-400 flex-1">{error}</p>
                <button
                  onClick={() => saveCurrentAnswer()}
                  className="text-xs font-semibold text-pink-300 hover:text-pink-200 cursor-pointer shrink-0"
                >
                  Retry
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── Bottom Navigation ──────────────────────────── */}
      <div className="flex-shrink-0 px-4 sm:px-6 py-4 border-t border-white/5 bg-[#040614]" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <button
            onClick={goBack}
            disabled={currentIndex === 0 || isSaving}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              color: 'var(--text-secondary)',
            }}
          >
            <ArrowLeft size={16} />
            Back
          </button>

          <motion.button
            whileHover={{ scale: isSaving ? 1 : 1.02 }}
            whileTap={{ scale: isSaving ? 1 : 0.98 }}
            onClick={goNext}
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 cursor-pointer disabled:opacity-60"
            style={{
              background: `linear-gradient(135deg, ${colors.accent}, ${colors.accent}cc)`,
              color: 'var(--bg-primary)',
              boxShadow: `0 0 16px ${colors.glow}`,
            }}
          >
            {isSaving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving...
              </>
            ) : currentIndex >= totalQuestions - 1 ? (
              <>
                <Check size={16} />
                Finish
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
    </motion.div>
  );
}
