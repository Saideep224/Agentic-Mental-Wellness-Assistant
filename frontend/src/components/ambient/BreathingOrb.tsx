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
      {/* Outer glow ring */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size,
          height: size,
          background: 'radial-gradient(circle, rgba(34, 211, 238, 0.15) 0%, rgba(167, 139, 250, 0.05) 50%, transparent 70%)',
          filter: 'blur(20px)',
        }}
      />

      {/* Middle ring */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size * 0.7,
          height: size * 0.7,
          background: 'radial-gradient(circle, rgba(34, 211, 238, 0.25) 0%, rgba(59, 130, 246, 0.1) 50%, transparent 70%)',
          filter: 'blur(10px)',
          animationDelay: '0.5s',
        }}
      />

      {/* Core orb */}
      <div
        className="absolute rounded-full animate-breathe"
        style={{
          width: size * 0.35,
          height: size * 0.35,
          background: 'radial-gradient(circle, rgba(34, 211, 238, 0.6) 0%, rgba(34, 211, 238, 0.2) 50%, transparent 80%)',
          boxShadow: '0 0 40px rgba(34, 211, 238, 0.3), 0 0 80px rgba(34, 211, 238, 0.1)',
          animationDelay: '1s',
        }}
      />

      {/* Tiny bright center */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.08,
          height: size * 0.08,
          background: 'rgba(255, 255, 255, 0.8)',
          boxShadow: '0 0 10px rgba(34, 211, 238, 0.8)',
          filter: 'blur(1px)',
        }}
      />
    </div>
  );
}
