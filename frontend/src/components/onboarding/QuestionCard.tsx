'use client';

import { motion } from 'framer-motion';
import { Question } from '@/types';

interface QuestionCardProps {
  question: Question;
  direction: number;
  displayNumber: number;
}

export default function QuestionCard({ question, direction, displayNumber }: QuestionCardProps) {
  return (
    <motion.div
      key={question.id}
      initial={{ opacity: 0, x: direction > 0 ? 80 : -80 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: direction > 0 ? -80 : 80 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="w-full max-w-2xl mx-auto mb-8"
    >
      {/* Category badge */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className="px-3 py-1 rounded-full text-xs font-medium"
          style={{
            background: 'rgba(34, 211, 238, 0.1)',
            color: 'var(--accent-cyan)',
            border: '1px solid rgba(34, 211, 238, 0.2)',
          }}
        >
          {question.categoryLabel}
        </div>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Q{displayNumber}
        </span>
      </div>

      {/* Question text */}
      <h2
        className="text-2xl sm:text-3xl font-semibold leading-snug"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-space-grotesk), sans-serif',
        }}
      >
        {question.text}
      </h2>
    </motion.div>
  );
}
