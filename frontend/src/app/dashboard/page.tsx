'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { RefreshCw, BarChart3, Sparkles } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import MoodTrendChart from '@/components/dashboard/MoodTrendChart';
import StressPatternChart from '@/components/dashboard/StressPatternChart';
import EmotionalProfileCard from '@/components/dashboard/EmotionalProfileCard';
import PersonalityInsights from '@/components/dashboard/PersonalityInsights';
import CommunicationStyle from '@/components/dashboard/CommunicationStyle';
import { useMoodData } from '@/hooks/useMoodData';
import { getToken, getStoredUser } from '@/lib/api';

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
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
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
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
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
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
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
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
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
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
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

export default function DashboardPage() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const {
    moodTrends,
    emotionalProfile,
    stressPatterns,
    insights,
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

  return (
    <div className="min-h-screen">
      <Navbar />

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
                  fontFamily: 'var(--font-outfit), sans-serif',
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mood Journey - Full width */}
          <div className="lg:col-span-2">
            <MoodTrendChart data={moodTrends} title="📈 Mood Journey" />
          </div>

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

          {/* Communication Style 🗣️ */}
          <CommunicationStyle preferences={communicationPrefs} />

          {/* Emotional Growth Tracker 🌱 */}
          <GrowthTrackerCard profile={emotionalProfile} />

          {/* AI Insights / Personalized Suggestions */}
          <PersonalizedSuggestionsCard profile={emotionalProfile} />
          
          <PersonalityInsights insights={insights} />
        </div>

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
