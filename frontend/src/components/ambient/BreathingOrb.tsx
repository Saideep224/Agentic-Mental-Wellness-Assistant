'use client';

import { cn } from '@/lib/utils';

interface BreathingOrbProps {
  size?: number;
  className?: string;
}

export default function BreathingOrb({ size = 200, className }: BreathingOrbProps) {
  return (
    <div
      className={cn('relative flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      {/* Outer glow ring - Optimized with feathered gradient, no blur filter */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size,
          height: size,
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.12) 0%, rgba(167, 139, 250, 0.04) 50%, transparent 100%)',
        }}
      />

      {/* Middle ring - Optimized gradient, no blur filter */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size * 0.75,
          height: size * 0.75,
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.22) 0%, rgba(59, 130, 246, 0.08) 60%, transparent 100%)',
          animationDelay: '0.5s',
        }}
      />

      {/* Core orb - Optimized radial gradient replacing box-shadows */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size * 0.45,
          height: size * 0.45,
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.45) 0%, rgba(56, 189, 248, 0.1) 70%, transparent 100%)',
          animationDelay: '1s',
        }}
      />

      {/* Tiny bright center - Optimized gradient, no filter/box-shadow */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.1,
          height: size * 0.1,
          background: 'radial-gradient(circle, rgba(255, 255, 255, 0.95) 0%, rgba(56, 189, 248, 0.5) 50%, transparent 100%)',
        }}
      />
    </div>
  );
}
