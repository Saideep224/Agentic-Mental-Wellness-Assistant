'use client';

import { Question } from '@/types';

interface QuestionCardProps {
  question: Question;
  displayNumber: number;
}

export default function QuestionCard({ question, displayNumber }: QuestionCardProps) {
  return (
    <div className="w-full max-w-2xl mx-auto mb-4 sm:mb-5">
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
    </div>
  );
}
