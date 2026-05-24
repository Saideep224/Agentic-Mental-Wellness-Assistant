'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { QuestionOption } from '@/types';

interface OptionCardProps {
  option: QuestionOption;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}

export default function OptionCard({ option, index, isSelected, onSelect }: OptionCardProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.4,
        delay: index * 0.08,
        ease: 'easeOut',
      }}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.98 }}
      onClick={onSelect}
      className={cn(
        'w-full text-left p-4 rounded-xl transition-all duration-300 cursor-pointer',
        'flex items-center gap-4 group'
      )}
      style={{
        background: isSelected
          ? 'rgba(34, 211, 238, 0.1)'
          : 'var(--glass-bg)',
        border: isSelected
          ? '1px solid rgba(34, 211, 238, 0.4)'
          : '1px solid var(--glass-border)',
        boxShadow: isSelected ? 'var(--glow-cyan)' : 'none',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      {/* Emoji */}
      <span className="text-2xl flex-shrink-0 transition-transform duration-300 group-hover:scale-110">
        {option.emoji}
      </span>

      {/* Label */}
      <span
        className="text-sm sm:text-base font-medium transition-colors duration-300"
        style={{
          color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)',
        }}
      >
        {option.label}
      </span>

      {/* Selection indicator */}
      <div className="ml-auto flex-shrink-0">
        <div
          className="w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300"
          style={{
            border: isSelected
              ? '2px solid var(--accent-cyan)'
              : '2px solid var(--text-muted)',
            background: isSelected ? 'var(--accent-cyan)' : 'transparent',
          }}
        >
          {isSelected && (
            <motion.svg
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
              width="10"
              height="10"
              viewBox="0 0 10 10"
            >
              <path
                d="M2 5 L4 7 L8 3"
                stroke="var(--bg-primary)"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </motion.svg>
          )}
        </div>
      </div>
    </motion.button>
  );
}
