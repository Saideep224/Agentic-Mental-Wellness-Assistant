'use client';

import { motion } from 'framer-motion';
import { EmotionalProfile } from '@/types';

interface EmotionalProfileCardProps {
  profile: EmotionalProfile | null;
}

export default function EmotionalProfileCard({ profile }: EmotionalProfileCardProps) {
  const defaultEmotions = [
    { emotion: 'Calm', percentage: 35, color: '#22d3ee' },
    { emotion: 'Reflective', percentage: 25, color: '#a78bfa' },
    { emotion: 'Hopeful', percentage: 20, color: '#34d399' },
    { emotion: 'Anxious', percentage: 12, color: '#f472b6' },
    { emotion: 'Neutral', percentage: 8, color: '#94a3b8' },
  ];

  const emotions = profile?.dominantEmotions || defaultEmotions;
  const overallMood = profile?.overallMood ?? 7.2;
  const commStyle = profile?.communicationStyleLabel ?? 'Empathetic Listener';
  const personalityLabel = profile?.personalityLabel ?? 'Thoughtful Introvert';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <h3
        className="text-lg font-semibold mb-1"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-outfit), sans-serif',
        }}
      >
        Emotional Profile
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Your emotional landscape summary
      </p>

      {/* Overall mood indicator */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
            Overall Mood
          </p>
          <div className="flex items-baseline gap-1">
            <span
              className="text-3xl font-bold"
              style={{ color: 'var(--accent-cyan)' }}
            >
              {overallMood}
            </span>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              /10
            </span>
          </div>
        </div>

        <div className="text-right">
          <div
            className="px-3 py-1.5 rounded-full text-xs font-medium mb-2"
            style={{
              background: 'rgba(167, 139, 250, 0.1)',
              color: 'var(--accent-purple)',
              border: '1px solid rgba(167, 139, 250, 0.2)',
            }}
          >
            {personalityLabel}
          </div>
          <div
            className="px-3 py-1.5 rounded-full text-xs font-medium"
            style={{
              background: 'rgba(56, 189, 248, 0.1)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
            }}
          >
            {commStyle}
          </div>
        </div>
      </div>

      {/* Emotion breakdown */}
      <div className="space-y-3">
        {emotions.map((item, i) => (
          <div key={item.emotion}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                {item.emotion}
              </span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {item.percentage}%
              </span>
            </div>
            <div
              className="w-full h-2 rounded-full overflow-hidden"
              style={{ background: 'rgba(255, 255, 255, 0.05)' }}
            >
              <motion.div
                className="h-full rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${item.percentage}%` }}
                transition={{ duration: 0.8, delay: 0.3 + i * 0.1, ease: 'easeOut' }}
                style={{
                  background: item.color,
                  boxShadow: `0 0 8px ${item.color}40`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
