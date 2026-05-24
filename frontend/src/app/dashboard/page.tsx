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

// Demo data for when API hasn't returned data yet
const demoMoodData = [
  { date: 'May 1', score: 6.5, emotion: 'neutral' },
  { date: 'May 3', score: 5.8, emotion: 'anxious' },
  { date: 'May 5', score: 7.2, emotion: 'calm' },
  { date: 'May 7', score: 4.5, emotion: 'sad' },
  { date: 'May 9', score: 6.0, emotion: 'neutral' },
  { date: 'May 11', score: 7.8, emotion: 'happy' },
  { date: 'May 13', score: 6.2, emotion: 'calm' },
  { date: 'May 15', score: 5.0, emotion: 'anxious' },
  { date: 'May 17', score: 7.5, emotion: 'happy' },
  { date: 'May 19', score: 8.0, emotion: 'happy' },
  { date: 'May 21', score: 6.8, emotion: 'calm' },
  { date: 'May 23', score: 7.2, emotion: 'calm' },
];

const demoStressData = [
  { category: 'Social', value: 65, fullMark: 100 },
  { category: 'Work', value: 78, fullMark: 100 },
  { category: 'Emotional', value: 55, fullMark: 100 },
  { category: 'Physical', value: 40, fullMark: 100 },
  { category: 'Mental', value: 70, fullMark: 100 },
];

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

  const displayMoodData = moodTrends.length > 0 ? moodTrends : demoMoodData;
  const displayStressData = stressPatterns.length > 0 ? stressPatterns : demoStressData;

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

        {/* Dashboard grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mood Trends - Full width */}
          <div className="lg:col-span-2">
            <MoodTrendChart data={displayMoodData} />
          </div>

          {/* Emotional Profile */}
          <EmotionalProfileCard profile={emotionalProfile} />

          {/* Stress Patterns */}
          <StressPatternChart data={displayStressData} />

          {/* Personality Insights */}
          <PersonalityInsights insights={insights} />

          {/* Communication Style */}
          <CommunicationStyle preferences={communicationPrefs} />
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
