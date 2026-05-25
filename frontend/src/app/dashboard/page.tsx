'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { RefreshCw, BarChart3 } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import MoodTrendChart from '@/components/dashboard/MoodTrendChart';
import StressPatternChart from '@/components/dashboard/StressPatternChart';
import EmotionalProfileCard from '@/components/dashboard/EmotionalProfileCard';
import PersonalityInsights from '@/components/dashboard/PersonalityInsights';
import CommunicationStyle from '@/components/dashboard/CommunicationStyle';
import { useMoodData } from '@/hooks/useMoodData';
import { getToken } from '@/lib/api';

// Sub-components for dynamic user-specific sections

function PersonalityProfileCard({ profile }: { profile: any }) {
  if (!profile) return null;
  const personality = profile.personalityType || {};
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.15 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
        Personality Profile 🧠
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your core behavior and character style
      </p>
      
      {personality.type ? (
        <div>
          <div className="text-sm font-semibold mb-2" style={{ color: 'var(--accent-cyan)' }}>
            Type: {personality.type}
          </div>
          <p className="text-sm text-slate-300 mb-4 font-medium italic">
            &ldquo;{personality.summary}&rdquo;
          </p>
          <p className="text-xs text-slate-400 leading-relaxed">
            {personality.description}
          </p>
        </div>
      ) : (
        <p className="text-sm text-slate-400">
          Complete onboarding to see your personality type.
        </p>
      )}
    </motion.div>
  );
}

function InterestsCard({ interests }: { interests: any }) {
  if (!interests) return null;
  const escapeMechanisms = interests.escape_mechanisms || interests.escapeMechanisms || [];
  const moodBoosters = interests.mood_boosters || interests.moodBoosters || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-outfit), sans-serif' }}>
        Interests & Hobbies 🎨
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your safe environments and comfort activities
      </p>

      <div className="space-y-4">
        {interests.safest_environment && (
          <div>
            <h4 className="text-xs font-semibold mb-1" style={{ color: 'var(--accent-cyan)' }}>Safest Environment 🏠</h4>
            <p className="text-sm text-slate-300">{interests.safest_environment}</p>
          </div>
        )}

        {escapeMechanisms.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--accent-purple)' }}>Escape Mechanisms 🚪</h4>
            <div className="flex flex-wrap gap-2">
              {escapeMechanisms.map((item: string, i: number) => (
                <span key={i} className="px-2.5 py-1 text-xs rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/15">
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}

        {moodBoosters.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--accent-emerald)' }}>Mood Boosters ☀️</h4>
            <div className="flex flex-wrap gap-2">
              {moodBoosters.map((item: string, i: number) => (
                <span key={i} className="px-2.5 py-1 text-xs rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/15">
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
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
          <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--accent-emerald)' }}>Current Strengths ✨</h4>
          <ul className="space-y-2">
            {strengths.length > 0 ? (
              strengths.map((item: string, i: number) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span style={{ color: 'var(--accent-emerald)' }}>✓</span> {item}
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-500 italic">No strengths defined yet</li>
            )}
          </ul>
        </div>

        <div>
          <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--accent-pink)' }}>Growth Focus Areas 🚀</h4>
          <ul className="space-y-2">
            {weaknesses.length > 0 ? (
              weaknesses.map((item: string, i: number) => (
                <li key={i} className="text-sm text-slate-300 flex items-center gap-2">
                  <span style={{ color: 'var(--accent-pink)' }}>→</span> {item}
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
  const {
    moodTrends,
    emotionalProfile,
    stressPatterns,
    insights,
    communicationPrefs,
    isLoading,
    refresh,
  } = useMoodData();
 
  // Auth check
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push('/login');
    }
  }, [router]);
 
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
                Your Dashboard
              </h1>
            </div>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Insights from your conversations and emotional journey
            </p>
          </div>
 
          <motion.button
            whileHover={{ scale: 1.05, rotate: 90 }}
            whileTap={{ scale: 0.95 }}
            onClick={refresh}
            disabled={isLoading}
            className="p-3 rounded-xl glass-card cursor-pointer transition-all duration-300 hover:border-[rgba(34,211,238,0.3)]"
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
              borderColor: 'rgba(34, 211, 238, 0.15)',
              background: 'rgba(34, 211, 238, 0.03)',
            }}
          >
            <p className="text-lg font-semibold text-cyan-400 flex items-center justify-center gap-2">
              Start chatting to generate insights 🌱
            </p>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Esona will analyze your emotional tendencies, stress triggers, and mood trends as you talk.
            </p>
          </motion.div>
        )}

        {/* Dashboard grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mood Trends - Full width */}
          <div className="lg:col-span-2">
            <MoodTrendChart data={moodTrends} />
          </div>
 
          {/* Personality Profile 🧠 */}
          <PersonalityProfileCard profile={emotionalProfile} />
 
          {/* Emotional Style 💭 */}
          <EmotionalProfileCard profile={emotionalProfile} />
 
          {/* Interests & Hobbies 🎨 */}
          <InterestsCard interests={emotionalProfile?.comfortPreferences} />
 
          {/* Stress Pattern Analysis 📊 */}
          <StressPatternChart data={stressPatterns} />
 
          {/* Communication Style 🗣️ */}
          <CommunicationStyle preferences={communicationPrefs} />
 
          {/* Emotional Growth Tracker 🌱 */}
          <GrowthTrackerCard profile={emotionalProfile} />
 
          {/* AI Insights ✨ */}
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
