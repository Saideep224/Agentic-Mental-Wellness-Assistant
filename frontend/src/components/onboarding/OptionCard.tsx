'use client';

import { motion } from 'framer-motion';
import { cn } from '@/utils';
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
        duration: 0.3,
        delay: index * 0.05,
        ease: 'easeOut',
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onSelect}
      className={cn(
        'w-full text-center sm:text-left rounded-xl transition-all duration-300 cursor-pointer relative overflow-hidden group',
        'flex flex-col sm:flex-row items-center sm:items-center',
        'p-3 sm:py-3.5 sm:px-4 gap-2 sm:gap-4 select-none',
        'min-h-[76px] sm:min-h-[64px]', // Mobile: ~76px, Desktop: ~64px
        isSelected
          ? 'bg-sky-500/10 border-sky-500/40 shadow-[0_0_12px_rgba(56,189,248,0.2)]'
          : 'bg-white/5 border-white/10 hover:border-white/20'
      )}
      style={{
        borderWidth: '1px',
        borderStyle: 'solid',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      {/* Emoji */}
      <span className="text-xl sm:text-2xl flex-shrink-0 transition-transform duration-300 group-hover:scale-110">
        {option.emoji}
      </span>

      {/* Label */}
      <span
        className="text-xs sm:text-sm font-medium transition-colors duration-300 text-center sm:text-left line-clamp-2 max-w-[85%] sm:max-w-none"
        style={{
          color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)',
          lineHeight: '1.25',
        }}
      >
        {option.label}
      </span>

      {/* Selection indicator */}
      <div className="absolute top-2.5 right-2.5 sm:relative sm:top-auto sm:right-auto sm:ml-auto flex-shrink-0">
        <div
          className="w-4 h-4 sm:w-5 sm:h-5 rounded-full flex items-center justify-center transition-all duration-300"
          style={{
            border: isSelected
              ? '2px solid var(--accent-cyan)'
              : '1.5px solid var(--text-muted)',
            background: isSelected ? 'var(--accent-cyan)' : 'transparent',
          }}
        >
          {isSelected && (
            <motion.svg
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
              width="8"
              height="8"
              viewBox="0 0 10 10"
              className="sm:w-2.5 sm:h-2.5"
            >
              <path
                d="M2 5 L4 7 L8 3"
                stroke="var(--bg-primary)"
                strokeWidth="2.5"
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
