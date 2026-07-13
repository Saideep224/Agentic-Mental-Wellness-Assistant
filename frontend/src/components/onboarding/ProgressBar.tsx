'use client';

import { motion } from 'framer-motion';
import { categories, getCategoryForQuestion } from '@/data/questions';

interface ProgressBarProps {
  currentQuestion: number;
  totalQuestions: number;
  currentCategory: string;
  saveStatus?: 'idle' | 'saving' | 'saved' | 'error';
}

export default function ProgressBar({
  currentQuestion,
  totalQuestions,
  currentCategory,
  saveStatus = 'idle',
}: ProgressBarProps) {
  const progress = ((currentQuestion + 1) / totalQuestions) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      {/* Question counter */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
            Question{' '}
            <span style={{ color: 'var(--accent-cyan)' }}>{currentQuestion + 1}</span>/{totalQuestions}
          </span>

          {/* Subtle live save state indicator */}
          {saveStatus !== 'idle' && (
            <motion.span
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="text-[10px] sm:text-xs font-semibold px-2 py-0.5 rounded-full select-none"
              style={{
                color: saveStatus === 'saving'
                  ? 'var(--text-secondary)'
                  : saveStatus === 'saved'
                  ? '#10b981'
                  : '#f43f5e',
                background: saveStatus === 'saving'
                  ? 'rgba(255, 255, 255, 0.03)'
                  : saveStatus === 'saved'
                  ? 'rgba(16, 185, 129, 0.08)'
                  : 'rgba(244, 63, 94, 0.08)',
                border: '1px solid',
                borderColor: saveStatus === 'saving'
                  ? 'rgba(255, 255, 255, 0.08)'
                  : saveStatus === 'saved'
                  ? 'rgba(16, 185, 129, 0.2)'
                  : 'rgba(244, 63, 94, 0.2)',
              }}
            >
              {saveStatus === 'saving' && 'Saving...'}
              {saveStatus === 'saved' && 'Saved'}
              {saveStatus === 'error' && 'Saved locally'}
            </motion.span>
          )}
        </div>
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
          animate={{ width: `${progress}%` }}
          transition={{ type: 'spring', stiffness: 80, damping: 15 }}
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
