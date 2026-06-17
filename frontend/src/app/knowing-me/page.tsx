'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart, ChevronDown, ChevronUp, Edit2, Save, X,
  Loader2, Check, Sparkles, AlertCircle
} from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import EsonaLoader from '@/components/layout/EsonaLoader';
import { questions } from '@/data/questions';
import { getToken, submitOnboarding, getOnboardingAnswers, upsertQuestionAnswersToSupabase, recalculateProfile } from '@/api';
import { useAuth } from '@/providers/AuthProvider';

const CATEGORIES = [
  { id: 'background', label: 'About You', emoji: '👤', color: 'blue', range: [1, 5] },
  { id: 'personality', label: 'Personality & Behavior', emoji: '🧠', color: 'cyan', range: [6, 10] },
  { id: 'emotion', label: 'Emotional State & Stress', emoji: '💭', color: 'purple', range: [11, 15] },
  { id: 'hobbies', label: 'Hobbies & Comfort Zone', emoji: '🌿', color: 'emerald', range: [16, 20] },
  { id: 'communication', label: 'Communication & Preferences', emoji: '💬', color: 'pink', range: [21, 25] },
];

const COLOR_MAP: Record<string, { border: string; glow: string; bg: string; text: string }> = {
  blue: {
    border: 'rgba(59, 130, 246, 0.25)',
    glow: '0 0 20px rgba(59, 130, 246, 0.1)',
    bg: 'rgba(59, 130, 246, 0.04)',
    text: 'rgb(59, 130, 246)',
  },
  cyan: {
    border: 'rgba(56, 189, 248, 0.25)',
    glow: '0 0 20px rgba(56, 189, 248, 0.1)',
    bg: 'rgba(56, 189, 248, 0.04)',
    text: 'rgb(56, 189, 248)',
  },
  purple: {
    border: 'rgba(167, 139, 250, 0.25)',
    glow: '0 0 20px rgba(167, 139, 250, 0.1)',
    bg: 'rgba(167, 139, 250, 0.04)',
    text: 'rgb(167, 139, 250)',
  },
  emerald: {
    border: 'rgba(52, 211, 153, 0.25)',
    glow: '0 0 20px rgba(52, 211, 153, 0.1)',
    bg: 'rgba(52, 211, 153, 0.04)',
    text: 'rgb(52, 211, 153)',
  },
  pink: {
    border: 'rgba(244, 114, 182, 0.25)',
    glow: '0 0 20px rgba(244, 114, 182, 0.1)',
    bg: 'rgba(244, 114, 182, 0.04)',
    text: 'rgb(244, 114, 182)',
  },
};

export default function KnowingMePage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [showLoader, setShowLoader] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [answers, setAnswers] = useState<any[]>([]);
  const [editedAnswers, setEditedAnswers] = useState<any[]>([]);
  const [editingCategory, setEditingCategory] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(CATEGORIES.map(c => c.id)));
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnswers = useCallback(async (token: string) => {
    setIsLoading(true);
    setShowLoader(true);
    const startTime = Date.now();
    try {
      const [rawAnswers] = await Promise.all([
        getOnboardingAnswers(token),
        recalculateProfile(token).catch(err => {
          console.warn('[KnowingMe] Profile recalculation failed:', err);
          return null;
        })
      ]);
      setAnswers(rawAnswers);
      setEditedAnswers(JSON.parse(JSON.stringify(rawAnswers)));
    } catch (err: any) {
      console.warn('[KnowingMe] Profile fetch failed, starting fresh:', err);
      // If no profile exists yet (404), initialize with empty answers for all questions
      const emptyAnswers = questions.map(q => ({
        question_id: q.id,
        category: q.category,
        selected_answers: [],
        custom_answer: null,
      }));
      setAnswers(emptyAnswers);
      setEditedAnswers(JSON.parse(JSON.stringify(emptyAnswers)));
    } finally {
      setIsLoading(false);
      const elapsed = Date.now() - startTime;
      const remainingDelay = Math.max(0, 1500 - elapsed);
      setTimeout(() => {
        setShowLoader(false);
      }, remainingDelay);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
      return;
    }
    fetchAnswers(token);
  }, [router, fetchAnswers]);

  const toggleCategory = (catId: string) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(catId)) {
        next.delete(catId);
      } else {
        next.add(catId);
      }
      return next;
    });
  };

  const startEditing = (catId: string) => {
    setEditingCategory(catId);
    setError(null);
    setSaveSuccess(false);
    // Ensure category is expanded
    setExpandedCategories(prev => new Set([...prev, catId]));
  };

  const cancelEditing = () => {
    setEditedAnswers(JSON.parse(JSON.stringify(answers)));
    setEditingCategory(null);
    setError(null);
  };

  const handleToggleOption = (questionId: number, optionValue: string) => {
    setEditedAnswers(prev => {
      const copy = [...prev];
      let ans = copy.find(a => a.question_id === questionId);
      if (!ans) {
        const q = questions.find(qu => qu.id === questionId);
        ans = {
          question_id: questionId,
          category: q?.category || 'personality',
          selected_answers: [],
          custom_answer: null,
        };
        copy.push(ans);
      }
      const selected = ans.selected_answers || [];
      if (selected.includes(optionValue)) {
        ans.selected_answers = selected.filter((v: string) => v !== optionValue);
      } else {
        ans.selected_answers = [...selected, optionValue];
      }
      return copy;
    });
  };

  const handleCustomTextChange = (questionId: number, text: string) => {
    setEditedAnswers(prev => {
      const copy = [...prev];
      let ans = copy.find(a => a.question_id === questionId);
      if (!ans) {
        const q = questions.find(qu => qu.id === questionId);
        ans = {
          question_id: questionId,
          category: q?.category || 'personality',
          selected_answers: [],
          custom_answer: null,
        };
        copy.push(ans);
      }
      ans.custom_answer = text;
      if (text.trim() && !ans.selected_answers.includes('other')) {
        ans.selected_answers = [...ans.selected_answers, 'other'];
      }
      return copy;
    });
  };

  const handleSave = async () => {
    const token = getToken();
    if (!token) return;

    setIsSaving(true);
    setError(null);
    setShowLoader(true);
    const startTime = Date.now();

    try {
      const completeAnswers = questions.map(q => {
        const edited = editedAnswers.find(a => a.question_id === q.id);
        if (edited) {
          return {
            questionId: q.id,
            category: q.category,
            selectedAnswers: edited.selected_answers || [],
            customAnswer: edited.custom_answer || undefined,
          };
        }
        const original = answers.find((a: any) => a.question_id === q.id);
        return {
          questionId: q.id,
          category: q.category,
          selectedAnswers: original?.selected_answers || [],
          customAnswer: original?.custom_answer || undefined,
        };
      });

      await upsertQuestionAnswersToSupabase(
        completeAnswers.map(answer => ({
          ...answer,
          questionText: questions.find(q => q.id === answer.questionId)?.text || '',
        }))
      );
      await submitOnboarding(completeAnswers, token);

      // Recalculate profile synchronously
      try {
        await recalculateProfile(token);
      } catch (err) {
        console.warn('[KnowingMe] Profile recalculation failed on save:', err);
      }

      // Refresh data
      const rawAnswers = await getOnboardingAnswers(token);
      setAnswers(rawAnswers);
      setEditedAnswers(JSON.parse(JSON.stringify(rawAnswers)));
      await refreshUser();

      setEditingCategory(null);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      console.error('[KnowingMe] Save failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to save your answers. Please try again.');
    } finally {
      setIsSaving(false);
      const elapsed = Date.now() - startTime;
      const remainingDelay = Math.max(0, 1500 - elapsed);
      setTimeout(() => {
        setShowLoader(false);
      }, remainingDelay);
    }
  };

  // Calculate progress
  const totalAnswered = questions.filter(q => {
    const ans = editedAnswers.find(a => a.question_id === q.id);
    return ans && ((ans.selected_answers && ans.selected_answers.length > 0) || Boolean(ans.custom_answer?.trim()));
  }).length;
  const totalQuestions = questions.length;
  const progressPercent = Math.round((totalAnswered / totalQuestions) * 100);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#040614] flex items-center justify-center" />
    );
  }

  if (showLoader) {
    return <EsonaLoader force={true} duration={1500} />;
  }

  return (
    <div className="min-h-screen">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-2">
            <Heart size={24} style={{ color: 'var(--accent-pink)' }} />
            <h1
              className="text-2xl sm:text-3xl font-bold"
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-space-grotesk), sans-serif',
              }}
            >
              Knowing Me
            </h1>
          </div>
          <p className="text-sm text-slate-400 max-w-xl">
            Answer or update these questions to help Esona understand your personality, emotional patterns, and communication preferences for deeply personalized responses.
          </p>
        </motion.div>

        {/* Progress bar */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="mb-8 glass-card p-5 rounded-2xl"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-300">
              Completion Progress
            </span>
            <span className="text-sm font-bold" style={{ color: 'var(--accent-cyan)' }}>
              {totalAnswered}/{totalQuestions} answered
            </span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="h-full rounded-full"
              style={{
                background: 'var(--gradient-primary)',
                boxShadow: '0 0 10px rgba(56, 189, 248, 0.4)',
              }}
            />
          </div>
          {progressPercent < 100 && (
            <p className="text-xs text-slate-500 mt-2 italic">
              Complete all questions to unlock full personality insights and adaptive AI conversations.
            </p>
          )}
          {progressPercent === 100 && (
            <p className="text-xs text-emerald-400 mt-2 flex items-center gap-1">
              <Check size={12} /> All questions answered! Your AI experience is fully personalized.
            </p>
          )}
        </motion.div>

        {/* Success banner */}
        <AnimatePresence>
          {saveSuccess && (
            <motion.div
              initial={{ opacity: 0, y: -10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -10, height: 0 }}
              className="mb-6 p-4 rounded-xl flex items-center gap-3"
              style={{
                background: 'rgba(52, 211, 153, 0.08)',
                border: '1px solid rgba(52, 211, 153, 0.2)',
              }}
            >
              <Sparkles size={18} className="text-emerald-400 shrink-0" />
              <div>
                <p className="text-sm font-medium text-emerald-400">Answers saved successfully!</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Your personality insights, emotional profile, and chatbot behavior have been updated.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mb-6 p-4 rounded-xl flex items-center gap-3"
              style={{
                background: 'rgba(244, 114, 182, 0.08)',
                border: '1px solid rgba(244, 114, 182, 0.2)',
              }}
            >
              <AlertCircle size={18} className="text-pink-400 shrink-0" />
              <p className="text-sm text-pink-400">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading state */}
        {isLoading && (
          <div className="text-center py-12">
            <Loader2 size={28} className="animate-spin mx-auto mb-3" style={{ color: 'var(--accent-cyan)' }} />
            <p className="text-sm text-slate-400">Loading your answers...</p>
          </div>
        )}

        {/* Categories */}
        {!isLoading && (
          <div className="space-y-6">
            {CATEGORIES.map((cat, catIdx) => {
              const colorSet = COLOR_MAP[cat.color];
              const isExpanded = expandedCategories.has(cat.id);
              const isEditing = editingCategory === cat.id;
              const catQuestions = questions.filter(q => q.id >= cat.range[0] && q.id <= cat.range[1]);
                const catAnswered = catQuestions.filter(q => {
                  const ans = editedAnswers.find(a => a.question_id === q.id);
                  return ans && ((ans.selected_answers && ans.selected_answers.length > 0) || Boolean(ans.custom_answer?.trim()));
                }).length;

              return (
                <motion.div
                  key={cat.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: catIdx * 0.08 }}
                  className="glass-card rounded-2xl overflow-hidden transition-all duration-300"
                  style={{
                    borderColor: isEditing ? colorSet.border : undefined,
                    boxShadow: isEditing ? colorSet.glow : undefined,
                  }}
                >
                  {/* Category header */}
                  <div
                    className="flex items-center justify-between p-5 cursor-pointer transition-colors hover:bg-white/[0.02]"
                    onClick={() => toggleCategory(cat.id)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{cat.emoji}</span>
                      <div>
                        <h3
                          className="text-base font-bold"
                          style={{ color: colorSet.text, fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                        >
                          {cat.label}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {catAnswered}/{catQuestions.length} answered
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {!editingCategory && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(cat.id);
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer"
                          style={{
                            background: `${colorSet.bg}`,
                            border: `1px solid ${colorSet.border}`,
                            color: colorSet.text,
                          }}
                        >
                          <Edit2 size={12} />
                          Edit
                        </button>
                      )}
                      <button
                        className="p-1.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer text-slate-400 hover:text-white"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCategory(cat.id);
                        }}
                      >
                        {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </button>
                    </div>
                  </div>

                  {/* Category content */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                      >
                        <div className="px-5 pb-5 pt-1 border-t border-white/5 space-y-5">
                          {catQuestions.map(q => {
                            const userAns = editedAnswers.find(a => a.question_id === q.id);
                            const selectedVals = userAns?.selected_answers || [];
                            const customVal = userAns?.custom_answer || '';

                            // Map values to labels for read-only display
                            const selectedLabels = q.options
                              .filter(opt => selectedVals.includes(opt.value))
                              .map(opt => `${opt.emoji} ${opt.label}`);
                            if (selectedVals.includes('other') && customVal) {
                              selectedLabels.push(`✏️ ${customVal}`);
                            }

                            return (
                              <div key={q.id} className="space-y-2 pb-4 border-b border-white/[0.03] last:border-0 last:pb-0">
                                <p className="text-sm font-semibold text-slate-200">
                                  <span className="text-xs font-bold mr-2 px-1.5 py-0.5 rounded" style={{ background: colorSet.bg, color: colorSet.text }}>
                                    Q{q.id}
                                  </span>
                                  {q.text}
                                </p>

                                {isEditing ? (
                                  <div className="space-y-2 pt-1">
                                    <div className="grid grid-cols-1 gap-1.5">
                                      {q.options.map(opt => {
                                        const isSelected = selectedVals.includes(opt.value);
                                        return (
                                          <label
                                            key={opt.value}
                                            onClick={() => handleToggleOption(q.id, opt.value)}
                                            className="flex items-center gap-2.5 p-2.5 rounded-xl cursor-pointer transition-all duration-200 group"
                                            style={{
                                              background: isSelected ? colorSet.bg : 'rgba(255, 255, 255, 0.02)',
                                              border: `1px solid ${isSelected ? colorSet.border : 'rgba(255, 255, 255, 0.04)'}`,
                                            }}
                                          >
                                            <div
                                              className="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition-all duration-200"
                                              style={{
                                                borderColor: isSelected ? colorSet.text : 'rgba(255, 255, 255, 0.15)',
                                                background: isSelected ? colorSet.text : 'transparent',
                                              }}
                                            >
                                              {isSelected && <Check size={10} className="text-white" />}
                                            </div>
                                            <span className="text-sm">{opt.emoji}</span>
                                            <span
                                              className="text-xs font-medium"
                                              style={{ color: isSelected ? colorSet.text : 'var(--text-secondary)' }}
                                            >
                                              {opt.label}
                                            </span>
                                          </label>
                                        );
                                      })}

                                      {q.allowOther && (
                                        <div className="space-y-1.5">
                                          <label
                                            onClick={() => handleToggleOption(q.id, 'other')}
                                            className="flex items-center gap-2.5 p-2.5 rounded-xl cursor-pointer transition-all duration-200"
                                            style={{
                                              background: selectedVals.includes('other') ? colorSet.bg : 'rgba(255, 255, 255, 0.02)',
                                              border: `1px solid ${selectedVals.includes('other') ? colorSet.border : 'rgba(255, 255, 255, 0.04)'}`,
                                            }}
                                          >
                                            <div
                                              className="w-4 h-4 rounded-md border flex items-center justify-center shrink-0 transition-all duration-200"
                                              style={{
                                                borderColor: selectedVals.includes('other') ? colorSet.text : 'rgba(255, 255, 255, 0.15)',
                                                background: selectedVals.includes('other') ? colorSet.text : 'transparent',
                                              }}
                                            >
                                              {selectedVals.includes('other') && <Check size={10} className="text-white" />}
                                            </div>
                                            <span className="text-sm">✏️</span>
                                            <span className="text-xs font-medium" style={{ color: selectedVals.includes('other') ? colorSet.text : 'var(--text-secondary)' }}>
                                              Something else...
                                            </span>
                                          </label>

                                          {selectedVals.includes('other') && (
                                            <motion.div
                                              initial={{ opacity: 0, height: 0 }}
                                              animate={{ opacity: 1, height: 'auto' }}
                                              className="pl-9"
                                            >
                                              <input
                                                type="text"
                                                value={customVal}
                                                onChange={(e) => handleCustomTextChange(q.id, e.target.value)}
                                                placeholder="Type your own answer..."
                                                className="w-full px-3 py-2 text-xs rounded-lg glass-input"
                                              />
                                            </motion.div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                ) : (
                                  <div className="flex flex-wrap gap-1.5 pt-1 pl-1">
                                    {selectedLabels.length > 0 ? (
                                      selectedLabels.map((lbl, i) => (
                                        <span
                                          key={i}
                                          className="px-2.5 py-1 rounded-lg text-[11px] font-medium"
                                          style={{
                                            background: 'rgba(255, 255, 255, 0.04)',
                                            border: '1px solid rgba(255, 255, 255, 0.06)',
                                            color: 'var(--text-secondary)',
                                          }}
                                        >
                                          {lbl}
                                        </span>
                                      ))
                                    ) : (
                                      <span className="text-xs text-slate-500 italic flex items-center gap-1">
                                        <AlertCircle size={11} />
                                        Not answered yet
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}

                          {/* Save / Cancel buttons when editing */}
                          {isEditing && (
                            <div className="flex items-center gap-3 pt-4 border-t border-white/5 justify-end">
                              <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={cancelEditing}
                                disabled={isSaving}
                                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold hover:bg-white/5 text-slate-400 cursor-pointer disabled:opacity-50 transition-colors"
                              >
                                <X size={14} />
                                Cancel
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-bold cursor-pointer disabled:opacity-50 transition-all duration-200"
                                style={{
                                  background: colorSet.text,
                                  color: 'var(--bg-primary)',
                                  boxShadow: colorSet.glow,
                                }}
                              >
                                {isSaving ? (
                                  <Loader2 size={14} className="animate-spin" />
                                ) : (
                                  <Save size={14} />
                                )}
                                Save & Update Profile
                              </motion.button>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Footer note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-center mt-12 text-xs"
          style={{ color: 'var(--text-muted)' }}
        >
          Your answers shape your personality insights, emotional profile, and how Esona talks to you. 💙
        </motion.p>
      </main>
    </div>
  );
}
