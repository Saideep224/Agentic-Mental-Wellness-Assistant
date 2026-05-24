'use client';

import { ReactNode } from 'react';
import { getEmotionColor, getEmotionGlow } from '@/lib/utils';

interface EmotionalAuraProps {
  emotion: string;
  children: ReactNode;
}

export default function EmotionalAura({ emotion, children }: EmotionalAuraProps) {
  const color = getEmotionColor(emotion);
  const glow = getEmotionGlow(emotion);

  return (
    <div className="relative">
      {/* Outer aura glow */}
      <div
        className="absolute inset-0 rounded-full animate-pulse-glow"
        style={{
          boxShadow: glow,
          transform: 'scale(1.3)',
          background: `radial-gradient(circle, ${color}20 0%, transparent 70%)`,
        }}
      />

      {/* Inner ring */}
      <div
        className="relative rounded-full"
        style={{
          boxShadow: `0 0 12px ${color}40`,
          border: `2px solid ${color}30`,
        }}
      >
        {children}
      </div>
    </div>
  );
}
