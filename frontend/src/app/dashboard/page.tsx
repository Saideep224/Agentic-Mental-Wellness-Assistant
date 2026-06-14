'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, BarChart3, Sparkles, ChevronDown, ChevronUp, Loader2, Edit2, Save, X, Heart, Trash2 } from 'lucide-react';
import Link from 'next/link';
import Navbar from '@/components/layout/Navbar';
import MoodTrendChart from '@/components/dashboard/MoodTrendChart';
import StressPatternChart from '@/components/dashboard/StressPatternChart';
import EmotionalProfileCard from '@/components/dashboard/EmotionalProfileCard';
import PersonalityInsights from '@/components/dashboard/PersonalityInsights';
import DeleteAccountModal from '@/components/dashboard/DeleteAccountModal';
import GrowthInsightsCard from '@/components/dashboard/GrowthInsightsCard';
import { useMoodData } from '@/hooks/useMoodData';
import { getToken, getStoredUser, submitOnboarding } from '@/api';
import { questions } from '@/data/questions';

// Sub-components for dynamic user-specific sections

function PersonalityCard({ profile }: { profile: any }) {
  if (!profile) return null;
  const p = profile.personalityProfile || {};
  const personalityType = p.type || profile.personalityType?.type || 'Thoughtful Explorer';
  const summary = profile.personalityType?.summary || 'Values quiet reflection and clear, low-pressure support.';
  const description = profile.personalityType?.description || 'Prefers reflecting internally and values authentic connections.';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
        ✨ Personality Card
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your core behavior and character style
      </p>
      
      <div>
        <div className="text-sm font-bold mb-2 text-sky-400">
          Type: {personalityType}
        </div>
        <p className="text-sm text-slate-300 mb-4 font-medium italic">
          &ldquo;{summary}&rdquo;
        </p>
        <p className="text-xs text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>
    </motion.div>
  );
}

function InterestsSection({ profile }: { profile: any }) {
  if (!profile) return null;
  const p = profile.personalityProfile || {};
  const interestsList = p.interests || profile.comfortPreferences?.escape_mechanisms || [];
  const safestEnv = profile.comfortPreferences?.safest_environment || 'Quiet personal space';
  const hasAnime = interestsList.some((i: string) => i.toLowerCase().includes('anime') || i.toLowerCase().includes('manga'));
  const hasEditing = interestsList.some((i: string) => i.toLowerCase().includes('edit') || i.toLowerCase().includes('creative') || i.toLowerCase().includes('design'));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
        🎯 Interests Section
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your comfort activities and safe zones
      </p>

      <div className="space-y-4">
        <div>
          <h4 className="text-xs font-semibold mb-1 text-sky-400">Safest Environment 🏠</h4>
          <p className="text-sm text-slate-300">{safestEnv}</p>
        </div>

        <div>
          <h4 className="text-xs font-semibold mb-2 text-purple-400 font-bold flex items-center gap-1">
            {hasAnime && '🌸 '}Comfort Activities & Hobbies {hasEditing && '🎬'}
          </h4>
          <div className="flex flex-wrap gap-2">
            {interestsList.length > 0 ? (
              interestsList.map((item: string, i: number) => (
                <span key={i} className="px-2.5 py-1 text-xs rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/15 capitalize">
                  {item === 'music' ? '🎵 Music' : item === 'gaming' ? '🎮 Gaming' : item === 'anime' ? '☑️ Anime' : item === 'editing' ? '☑️ Editing' : item}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500 italic">No comfort activities listed.</span>
            )}
          </div>
        </div>

        {hasAnime && (
          <p className="text-xs text-sky-300/80 bg-sky-950/10 p-2.5 rounded-lg border border-sky-500/10">
            ✨ Tip: When you feel overwhelmed, try taking a 15-minute break to listen to some chill Lo-Fi anime soundtracks!
          </p>
        )}
      </div>
    </motion.div>
  );
}

function MotivationStyleCard({ profile }: { profile: any }) {
  if (!profile) return null;
  const p = profile.personalityProfile || {};
  const motivation = p.motivation_style || 'encouragement and validation';
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.22 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
        🔥 Motivation Style
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        What keeps you driven and focused
      </p>
      
      <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10">
        <h4 className="text-sm font-bold text-amber-400 mb-1 capitalize flex items-center gap-1.5">
          ✨ {motivation}
        </h4>
        <p className="text-xs text-slate-300 leading-relaxed mt-2">
          Your motivation profile suggests you respond best to positive reinforcement, structured check-ins, and actionable steps rather than vague pressure.
        </p>
      </div>
    </motion.div>
  );
}

function PersonalizedSuggestionsCard({ profile }: { profile: any }) {
  if (!profile) return null;
  const p = profile.personalityProfile || {};
  const interestsList = p.interests || [];
  const type = (p.type || '').toLowerCase();
  
  const hasAnime = interestsList.some((i: string) => i.toLowerCase().includes('anime') || i.toLowerCase().includes('manga'));
  const hasEditing = interestsList.some((i: string) => i.toLowerCase().includes('edit') || i.toLowerCase().includes('creative') || i.toLowerCase().includes('design'));
  
  const suggestions = [
    "Take a 5-minute deep breathing exercise when feeling under pressure.",
    "Journal your thoughts before going to bed to prevent late-night overthinking.",
    "Reach out to a close friend for a short, low-pressure conversation."
  ];

  if (hasAnime) {
    suggestions.unshift("Binge a comfort episode of your favorite slice-of-life anime.");
  }
  if (hasEditing) {
    suggestions.unshift("Set a 25-minute Pomodoro timer for creative work, then take a full screen break.");
  }
  if (type.includes('introvert')) {
    suggestions.push("Schedule at least 1 hour of quiet alone time to recharge your social battery.");
  }
  if (type.includes('extrovert')) {
    suggestions.push("Plan a group activity or text a friend to share your energy!");
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
        💡 Personalized Suggestions
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Actions customized to your personality and interests
      </p>
      
      <ul className="space-y-3">
        {suggestions.slice(0, 4).map((s, idx) => (
          <li key={idx} className="text-xs sm:text-sm text-slate-300 flex items-start gap-2 bg-white/2 p-2.5 rounded-lg border border-white/5">
            <span className="text-sky-400 select-none">✨</span>
            <span>{s}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  );
}

function GrowthTrackerCard({ profile }: { profile: any }) {
  if (!profile) return null;
  const strengths = profile.strengths?.strengths || profile.strengths || [];
  const weaknesses = profile.weaknesses?.weaknesses || profile.weaknesses || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.25 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
        Emotional Growth Tracker 🌱
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your personal strengths and areas of growth
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-xs font-semibold mb-2 text-emerald-400">Current Strengths ✨</h4>
          <ul className="space-y-2">
            {strengths.length > 0 ? (
              strengths.map((item: string, i: number) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-emerald-400">✓</span> {item}
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-500 italic">No strengths defined yet</li>
            )}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-semibold mb-2 text-pink-400">Growth Focus Areas 🚀</h4>
          <ul className="space-y-2">
            {weaknesses.length > 0 ? (
              weaknesses.map((item: string, i: number) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span className="text-pink-400">→</span> {item}
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-500 italic">No growth areas defined yet</li>
            )}
          </ul>
        </div>
      </div>
    </motion.div>
  );
}

function YourAnswersCard({ profile, onUpdate }: { profile: any; onUpdate: () => void }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null); // editing category
  const [editedAnswers, setEditedAnswers] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize editedAnswers from profile
  const originalAnswers = profile?.onboardingAnswers || [];

  useEffect(() => {
    if (originalAnswers.length > 0) {
      setEditedAnswers(JSON.parse(JSON.stringify(originalAnswers)));
    }
  }, [profile]);

  if (!profile) return null;

  const categories = [
    { id: 'personality', label: '🧠 Personality & Behavior', range: [1, 5] },
    { id: 'emotion', label: '💭 Emotional Habits', range: [6, 10] },
    { id: 'hobbies', label: '🌿 Stress Patterns & Hobbies', range: [11, 15] },
    { id: 'communication', label: '💬 Communication Style', range: [16, 20] },
  ];

  const handleToggleOption = (questionId: number, optionValue: string, isMulti: boolean) => {
    setEditedAnswers(prev => {
      const copy = [...prev];
      let ans = copy.find(a => a.question_id === questionId);
      if (!ans) {
        // Find category for question
        const q = questions.find(qu => qu.id === questionId);
        ans = {
          question_id: questionId,
          category: q?.category || 'personality',
          selected_answers: [],
          custom_answer: null
        };
        copy.push(ans);
      }

      const selected = ans.selected_answers || [];
      if (selected.includes(optionValue)) {
        ans.selected_answers = selected.filter((v: string) => v !== optionValue);
      } else {
        if (isMulti) {
          ans.selected_answers = [...selected, optionValue];
        } else {
          ans.selected_answers = [optionValue];
        }
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
          custom_answer: null
        };
        copy.push(ans);
      }
      ans.custom_answer = text;
      // Also ensure "other" is in selected_answers if they type custom text
      if (text.trim() && !ans.selected_answers.includes('other')) {
        ans.selected_answers = [...ans.selected_answers, 'other'];
      }
      return copy;
    });
  };

  const handleSave = async (categoryId: string) => {
    const token = getToken();
    if (!token) return;

    setIsSaving(true);
    setError(null);

    try {
      // Construct a complete list of 20 answers
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
        const original = originalAnswers.find((a: any) => a.question_id === q.id);
        return {
          questionId: q.id,
          category: q.category,
          selectedAnswers: original?.selected_answers || [],
          customAnswer: original?.custom_answer || undefined,
        };
      });

      await submitOnboarding(completeAnswers, token);
      
      // Stop editing
      setActiveCategory(null);
      
      // Trigger dashboard reload
      onUpdate();
    } catch (err: any) {
      console.error('[YourAnswers] Failed to update onboarding responses:', err);
      setError(err instanceof Error ? err.message : 'Failed to update answers');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original answers
    setEditedAnswers(JSON.parse(JSON.stringify(originalAnswers)));
    setActiveCategory(null);
    setError(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.35 }}
      className="glass-card p-6 lg:col-span-2 overflow-hidden"
    >
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div>
          <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
            📝 Your Answers
          </h3>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Review and update your onboarding responses to personalize Esona's adaptation
          </p>
        </div>
        <button className="p-1.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer text-slate-400 hover:text-white">
          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-6 space-y-6 pt-4 border-t border-white/5"
          >
            {error && (
              <div className="p-3 rounded-xl text-xs bg-red-500/10 border border-red-500/15 text-red-400">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {categories.map(cat => {
                const isEditing = activeCategory === cat.id;
                const catQuestions = questions.filter(q => q.id >= cat.range[0] && q.id <= cat.range[1]);

                return (
                  <div 
                    key={cat.id} 
                    className="p-5 rounded-xl border transition-all duration-300"
                    style={{
                      background: isEditing ? 'rgba(56, 189, 248, 0.02)' : 'rgba(255, 255, 255, 0.01)',
                      borderColor: isEditing ? 'rgba(56, 189, 248, 0.25)' : 'var(--glass-border)',
                      boxShadow: isEditing ? 'var(--glow-cyan)' : 'none',
                    }}
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-sm font-bold text-white">{cat.label}</h4>
                      {!activeCategory && (
                        <button
                          onClick={() => setActiveCategory(cat.id)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10 text-sky-400 cursor-pointer transition-all duration-200"
                        >
                          <Edit2 size={12} />
                          Edit
                        </button>
                      )}
                    </div>

                    <div className="space-y-4">
                      {catQuestions.map(q => {
                        const userAns = editedAnswers.find(a => a.question_id === q.id);
                        const selectedVals = userAns?.selected_answers || [];
                        const customVal = userAns?.custom_answer || '';
                        
                        // Map values to labels for display
                        const selectedLabels = q.options
                          .filter(opt => selectedVals.includes(opt.value))
                          .map(opt => `${opt.emoji} ${opt.label}`);
                        
                        if (selectedVals.includes('other') && customVal) {
                          selectedLabels.push(`✏️ ${customVal}`);
                        }

                        return (
                          <div key={q.id} className="text-xs space-y-1.5 pb-3 border-b border-white/2 last:border-0 last:pb-0">
                            <p className="font-semibold text-slate-300">Q{q.id}. {q.text}</p>
                            
                            {isEditing ? (
                              <div className="space-y-2 pt-1.5">
                                <div className="grid grid-cols-1 gap-1.5">
                                  {q.options.map(opt => {
                                    const isSelected = selectedVals.includes(opt.value);
                                    return (
                                      <label
                                        key={opt.value}
                                        onClick={() => handleToggleOption(q.id, opt.value, true)}
                                        className="flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors bg-white/3 hover:bg-white/5 border text-slate-300"
                                        style={{
                                          borderColor: isSelected ? 'rgba(56, 189, 248, 0.3)' : 'transparent',
                                          color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)'
                                        }}
                                      >
                                        <span className="text-sm">{opt.emoji}</span>
                                        <span>{opt.label}</span>
                                      </label>
                                    );
                                  })}

                                  {q.allowOther && (
                                    <div className="space-y-1.5 mt-1">
                                      <label
                                        onClick={() => handleToggleOption(q.id, 'other', true)}
                                        className="flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors bg-white/3 hover:bg-white/5 border text-slate-300"
                                        style={{
                                          borderColor: selectedVals.includes('other') ? 'rgba(56, 189, 248, 0.3)' : 'transparent',
                                          color: selectedVals.includes('other') ? 'var(--accent-cyan)' : 'var(--text-secondary)'
                                        }}
                                      >
                                        <span>✏️</span>
                                        <span>Something else...</span>
                                      </label>

                                      {selectedVals.includes('other') && (
                                        <input
                                          type="text"
                                          value={customVal}
                                          onChange={(e) => handleCustomTextChange(q.id, e.target.value)}
                                          placeholder="Type your own answer..."
                                          className="w-full px-3 py-2 text-xs glass-input"
                                        />
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <div className="flex flex-wrap gap-1.5 pt-1">
                                {selectedLabels.length > 0 ? (
                                  selectedLabels.map((lbl, i) => (
                                    <span key={i} className="px-2 py-0.5 rounded bg-white/5 border border-white/5 text-[10px] text-slate-400">
                                      {lbl}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-[10px] text-slate-500 italic">Skipped</span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {isEditing && (
                      <div className="flex items-center gap-2 mt-5 pt-3 border-t border-white/5 justify-end">
                        <button
                          onClick={handleCancel}
                          disabled={isSaving}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-white/5 text-slate-400 cursor-pointer disabled:opacity-50 transition-colors"
                        >
                          <X size={12} />
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSave(cat.id)}
                          disabled={isSaving}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-400 text-bg-primary hover:bg-sky-300 cursor-pointer disabled:opacity-50 transition-colors"
                        >
                          {isSaving ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : (
                            <Save size={12} />
                          )}
                          Save Updates
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const {
    moodTrends,
    emotionalProfile,
    stressPatterns,
    insights,
    growthInsights,
    communicationPrefs,
    isLoading,
    refresh,
  } = useMoodData();

  useEffect(() => {
    setMounted(true);
    const token = getToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);

  const user = mounted ? getStoredUser() : null;

  const getPersonalizedGreeting = () => {
    const name = user?.name || 'Sai';
    if (!emotionalProfile) return `Welcome back ${name} 👋`;
    
    const p = (emotionalProfile as any).personalityProfile || {};
    const interestsList = p.interests || [];
    const type = (p.type || '').toLowerCase();
    
    if (interestsList.some((i: string) => i.toLowerCase().includes('anime') || i.toLowerCase().includes('manga'))) {
      return `Welcome back ${name} 👋 Your anime list might be waiting, but let's check in!`;
    }
    if (interestsList.some((i: string) => i.toLowerCase().includes('edit') || i.toLowerCase().includes('creative') || i.toLowerCase().includes('design'))) {
      return `Welcome back ${name} 👋 Your creative energy looks strong today.`;
    }
    if (type.includes('introvert')) {
      return `Welcome back ${name} 👋 Take a quiet breath. You are in a safe, peaceful space.`;
    }
    if (type.includes('extrovert')) {
      return `Welcome back ${name}! 👋 Ready to conquer the day? Let's check in!`;
    }
    return `Welcome back ${name} 👋`;
  };

  const getSubtext = () => {
    if (!emotionalProfile) return 'Insights from your conversations and emotional journey';
    const p = (emotionalProfile as any).personalityProfile || {};
    const type = (p.type || '').toLowerCase();
    if (type.includes('introvert')) {
      return 'A quiet, calm overview of your emotional journey and reflections.';
    }
    if (type.includes('extrovert')) {
      return 'Your active highlights, emotional patterns, and social metrics!';
    }
    return 'Insights from your conversations and emotional journey';
  };

  if (!mounted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-sky-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* Account Deletion Modal */}
      {showDeleteModal && (
        <DeleteAccountModal
          userEmail={user?.email}
          onClose={() => setShowDeleteModal(false)}
        />
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 size={24} style={{ color: 'var(--accent-cyan)' }} />
              <h1
                className="text-2xl sm:text-3xl font-bold"
                style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-space-grotesk), sans-serif',
                }}
              >
                {getPersonalizedGreeting()}
              </h1>
            </div>
            <p className="text-sm text-slate-400">
              {getSubtext()}
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.05, rotate: 90 }}
            whileTap={{ scale: 0.95 }}
            onClick={refresh}
            disabled={isLoading}
            className="p-3 rounded-xl glass-card cursor-pointer transition-all duration-300 hover:border-[rgba(56,189,248,0.3)]"
            title="Refresh data"
          >
            <RefreshCw
              size={18}
              className={isLoading ? 'animate-spin' : ''}
              style={{ color: 'var(--accent-cyan)' }}
            />
          </motion.button>
        </motion.div>

        {/* Loading indicator */}
        {isLoading && (
          <div className="text-center py-4 mb-6">
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--accent-cyan)' }} />
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading your insights...</span>
            </div>
          </div>
        )}

        {/* Banner for new users */}
        {!isLoading && moodTrends.length === 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-8 p-6 rounded-2xl border text-center glass-card"
            style={{
              borderColor: 'rgba(56, 189, 248, 0.15)',
              background: 'rgba(56, 189, 248, 0.03)',
            }}
          >
            <p className="text-lg font-semibold text-sky-400 flex items-center justify-center gap-2">
              Start chatting to generate insights 🌱
            </p>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Esona will analyze your emotional tendencies, stress triggers, and mood trends as you talk.
            </p>
          </motion.div>
        )}

        {/* Dashboard grid */}
        {(() => {
          // Check if user has actual onboarding answers (non-empty selections)
          const onboardingAnswers = (emotionalProfile as any)?.onboardingAnswers || [];
          const hasOnboardingAnswers = onboardingAnswers.length > 0 &&
            onboardingAnswers.some((a: any) => a.selected_answers && a.selected_answers.length > 0);

          return (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Mood Journey - Full width */}
              <div className="lg:col-span-2">
                <MoodTrendChart data={moodTrends} title="📈 Mood Journey" />
              </div>

              {/* Knowing Me link card - Full width */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="glass-card p-5 lg:col-span-2"
              >
                <Link
                  href="/knowing-me"
                  className="flex items-center justify-between group cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                      style={{
                        background: 'rgba(244, 114, 182, 0.1)',
                        border: '1px solid rgba(244, 114, 182, 0.15)',
                      }}
                    >
                      <Heart size={18} className="text-pink-400" />
                    </div>
                    <div>
                      <h3
                        className="text-base font-semibold text-white group-hover:text-pink-300 transition-colors"
                        style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                      >
                        Knowing Me
                      </h3>
                      <p className="text-xs text-slate-400">
                        {hasOnboardingAnswers
                          ? 'Review and update your personality answers'
                          : 'Answer questions to personalize your experience'
                        }
                      </p>
                    </div>
                  </div>
                  <span className="text-slate-500 group-hover:text-pink-400 transition-colors text-lg">→</span>
                </Link>
              </motion.div>

              {hasOnboardingAnswers ? (
                <>
                  {/* Personality Card */}
                  <PersonalityCard profile={emotionalProfile} />

                  {/* Emotional Style 💭 */}
                  <EmotionalProfileCard profile={emotionalProfile} />

                  {/* Interests Section */}
                  <InterestsSection profile={emotionalProfile} />

                  {/* Emotional Pattern Analysis 🧠 */}
                  <StressPatternChart data={stressPatterns} title="🧠 Emotional Pattern Analysis" />

                  {/* Motivation Style Card */}
                  <MotivationStyleCard profile={emotionalProfile} />

                  {/* Emotional Growth Tracker 🌱 */}
                  <GrowthTrackerCard profile={emotionalProfile} />

                  {/* AI Insights / Personalized Suggestions */}
                  <PersonalizedSuggestionsCard profile={emotionalProfile} />
                  
                  <PersonalityInsights insights={insights} />

                  {/* Personal Growth Insights — full width */}
                  <GrowthInsightsCard
                    insights={growthInsights?.insights ?? []}
                    totalLogs={growthInsights?.total_logs}
                    totalMemories={growthInsights?.total_memories}
                  />
                </>
              ) : (
                /* CTA when no onboarding answers */
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.15 }}
                  className="lg:col-span-2 p-8 rounded-2xl text-center relative overflow-hidden"
                  style={{
                    background: 'rgba(56, 189, 248, 0.03)',
                    border: '1px solid rgba(56, 189, 248, 0.12)',
                  }}
                >
                  {/* Glow accent */}
                  <div
                    className="absolute top-0 left-1/2 -translate-x-1/2 w-60 h-1 rounded-full"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.4), rgba(167, 139, 250, 0.4), transparent)',
                    }}
                  />
                  <div className="mb-4">
                    <div
                      className="w-16 h-16 rounded-2xl mx-auto flex items-center justify-center mb-4"
                      style={{
                        background: 'rgba(56, 189, 248, 0.08)',
                        border: '1px solid rgba(56, 189, 248, 0.15)',
                      }}
                    >
                      <Sparkles size={28} className="text-sky-400" />
                    </div>
                    <h3
                      className="text-xl font-bold text-white mb-2"
                      style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                    >
                      Unlock Your Emotional Insights
                    </h3>
                    <p className="text-sm text-slate-400 max-w-md mx-auto leading-relaxed">
                      Complete your &ldquo;Knowing Me&rdquo; section to unlock personalized emotional insights and adaptive AI conversations.
                    </p>
                  </div>
                  <Link
                    href="/knowing-me"
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-300"
                    style={{
                      background: 'var(--gradient-primary)',
                      color: 'var(--bg-primary)',
                      boxShadow: '0 0 20px rgba(56, 189, 248, 0.25)',
                    }}
                  >
                    <Heart size={16} />
                    Complete Knowing Me
                  </Link>
                </motion.div>
              )}
            </div>
          );
        })()}

        {/* Account & Privacy — always visible */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-6 rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(239, 68, 68, 0.02)',
            border: '1px solid rgba(239, 68, 68, 0.1)',
          }}
        >
          {/* Top accent line */}
          <div
            className="h-px w-full"
            style={{
              background: 'linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.3), transparent)',
            }}
          />
          <div className="p-6">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <h3
                  className="text-base font-semibold text-white mb-1"
                  style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
                >
                  🔐 Account &amp; Privacy
                </h3>
                <p className="text-xs text-slate-500 max-w-sm leading-relaxed">
                  Manage your account data. Deletion is permanent and cannot be undone.
                  All memories, chat history, and preferences will be erased.
                </p>
              </div>
              <motion.button
                id="open-delete-account-btn"
                onClick={() => setShowDeleteModal(true)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer shrink-0"
                style={{
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  color: 'rgb(248, 113, 113)',
                }}
              >
                <Trash2 size={14} />
                Delete Account
              </motion.button>
            </div>
          </div>
        </motion.div>

        {/* Footer note */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-center mt-12 text-xs"
          style={{ color: 'var(--text-muted)' }}
        >
          These insights are based on your conversations and are updated regularly. 💙
        </motion.p>
      </main>
    </div>
  );
}
