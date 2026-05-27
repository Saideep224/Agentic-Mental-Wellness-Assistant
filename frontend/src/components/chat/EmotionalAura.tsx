'use client';

import { ReactNode } from 'react';
import { getEmotionColor, getEmotionGlow } from '@/utils';

interface EmotionalAuraProps {
  emotion: string;
  children: ReactNode;
}

export default function EmotionalAura({ emotion, children }: EmotionalAuraProps) {
  const color = getEmotionColor(emotion);
  const glow = getEmotionGlow(emotion);

  return (
    <div className="relative">
      {/* Subtle soft backdrop reflection (no heavy glow or animation) */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none"
        style={{
          transform: 'scale(1.05)',
          background: `radial-gradient(circle, ${color}15 0%, transparent 80%)`,
        }}
      />

      {/* Clean border and extremely soft shadow */}
      <div
        className="relative rounded-full"
        style={{
          boxShadow: `0 2px 8px ${color}15`,
          border: `1px solid ${color}25`,
        }}
      >
        {children}
      </div>
    </div>
  );
}
