'use client';

import { motion } from 'framer-motion';
import { getCategoryInfo } from '@/data/questions';

interface CategoryTransitionProps {
  category: string;
  onContinue: () => void;
}

export default function CategoryTransition({ category, onContinue }: CategoryTransitionProps) {
  const info = getCategoryInfo(category);
  if (!info) return null;

  const colorMap: Record<string, string> = {
    cyan: 'var(--accent-cyan)',
    purple: 'var(--accent-purple)',
    emerald: 'var(--accent-emerald)',
    pink: 'var(--accent-pink)',
  };

  const glowMap: Record<string, string> = {
    cyan: '0 0 40px rgba(56, 189, 248, 0.2)',
    purple: '0 0 40px rgba(167, 139, 250, 0.2)',
    emerald: '0 0 40px rgba(52, 211, 153, 0.2)',
    pink: '0 0 40px rgba(244, 114, 182, 0.2)',
  };

  const accentColor = colorMap[info.color] ?? 'var(--accent-cyan)';
  const glow = glowMap[info.color] ?? 'none';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="flex flex-col items-center justify-center text-center py-20"
      onClick={onContinue}
      style={{ cursor: 'pointer' }}
    >
      {/* Category emoji */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 200, damping: 15 }}
        className="text-6xl mb-6"
      >
        {info.emoji}
      </motion.div>

      {/* Category label */}
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="text-3xl sm:text-4xl font-bold mb-4"
        style={{
          color: accentColor,
          fontFamily: 'var(--font-outfit), sans-serif',
          textShadow: glow,
        }}
      >
        {info.label}
      </motion.h2>

      {/* Description */}
      <motion.p
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.5 }}
        className="text-base max-w-md"
        style={{ color: 'var(--text-secondary)' }}
      >
        {info.description}
      </motion.p>

      {/* Tap to continue */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.5 }}
        className="mt-8 text-xs"
        style={{ color: 'var(--text-muted)' }}
      >
        tap anywhere to continue
      </motion.p>
    </motion.div>
  );
}
