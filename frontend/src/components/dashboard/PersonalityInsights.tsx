'use client';

import { motion } from 'framer-motion';
import { PersonalityInsight } from '@/types';

interface PersonalityInsightsProps {
  insights: PersonalityInsight[];
}

const defaultInsights: PersonalityInsight[] = [
  {
    trait: 'Empathy',
    description: 'You tend to deeply understand and share the feelings of others.',
    strength: 85,
    icon: '💗',
  },
  {
    trait: 'Introspection',
    description: 'You frequently reflect on your own thoughts, feelings, and motivations.',
    strength: 78,
    icon: '🔍',
  },
  {
    trait: 'Resilience',
    description: 'You show capacity to recover quickly from difficult situations.',
    strength: 65,
    icon: '🌱',
  },
  {
    trait: 'Creativity',
    description: 'You express yourself through creative outlets and original thinking.',
    strength: 72,
    icon: '🎨',
  },
  {
    trait: 'Adaptability',
    description: 'You adjust well to changing circumstances and environments.',
    strength: 60,
    icon: '🌊',
  },
];

export default function PersonalityInsights({ insights }: PersonalityInsightsProps) {
  const displayInsights = insights.length > 0 ? insights : defaultInsights;

  const getStrengthColor = (strength: number): string => {
    if (strength >= 80) return 'var(--accent-emerald)';
    if (strength >= 60) return 'var(--accent-cyan)';
    if (strength >= 40) return 'var(--accent-purple)';
    return 'var(--accent-pink)';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card p-6"
    >
      <h3
        className="text-lg font-semibold mb-1"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-outfit), sans-serif',
        }}
      >
        Personality Insights
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        Key traits that define your emotional profile
      </p>

      <div className="space-y-4">
        {displayInsights.map((insight, i) => (
          <motion.div
            key={insight.trait}
            initial={{ opacity: 0, x: -15 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.4 + i * 0.1 }}
            className="flex items-start gap-3 p-3 rounded-xl"
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--glass-border)',
            }}
          >
            <span className="text-xl flex-shrink-0 mt-0.5">{insight.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span
                  className="text-sm font-medium"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {insight.trait}
                </span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: getStrengthColor(insight.strength) }}
                >
                  {insight.strength}%
                </span>
              </div>
              <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
                {insight.description}
              </p>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: 'rgba(255, 255, 255, 0.05)' }}
              >
                <motion.div
                  className="h-full rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${insight.strength}%` }}
                  transition={{ duration: 0.8, delay: 0.5 + i * 0.1, ease: 'easeOut' }}
                  style={{
                    background: getStrengthColor(insight.strength),
                  }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
