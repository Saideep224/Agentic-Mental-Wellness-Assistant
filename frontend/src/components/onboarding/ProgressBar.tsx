'use client';

import { motion } from 'framer-motion';
import { categories, getCategoryForQuestion } from '@/data/questions';

interface ProgressBarProps {
  currentQuestion: number;
  totalQuestions: number;
  currentCategory: string;
}

export default function ProgressBar({
  currentQuestion,
  totalQuestions,
  currentCategory,
}: ProgressBarProps) {
  const progress = ((currentQuestion + 1) / totalQuestions) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      {/* Question counter */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          Question{' '}
          <span style={{ color: 'var(--accent-cyan)' }}>{currentQuestion + 1}</span>/{totalQuestions}
        </span>
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          {categories.find((c) => c.id === currentCategory)?.label || ''}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className="w-full h-2 rounded-full overflow-hidden"
        style={{ background: 'rgba(255, 255, 255, 0.05)' }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{
            background: 'var(--gradient-primary)',
            boxShadow: '0 0 10px rgba(34, 211, 238, 0.3)',
          }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Category dots */}
      <div className="flex items-center justify-center gap-3 mt-4">
        {categories.map((category) => {
          const isActive = category.id === currentCategory;
          const categoryQuestions = Array.from(
            { length: totalQuestions },
            (_, i) => i
          ).filter((i) => {
            return getCategoryForQuestion(i) === category.id;
          });
          const isPast = categoryQuestions.every((qi) => qi < currentQuestion);

          return (
            <div key={category.id} className="flex items-center gap-2">
              <div
                className="w-2.5 h-2.5 rounded-full transition-all duration-300"
                style={{
                  background: isActive
                    ? 'var(--accent-cyan)'
                    : isPast
                    ? 'var(--accent-purple)'
                    : 'rgba(255, 255, 255, 0.1)',
                  boxShadow: isActive ? 'var(--glow-cyan)' : 'none',
                }}
              />
              <span
                className="text-xs hidden sm:inline"
                style={{
                  color: isActive
                    ? 'var(--accent-cyan)'
                    : isPast
                    ? 'var(--text-secondary)'
                    : 'var(--text-muted)',
                }}
              >
                {category.emoji}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
