'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import EsonaLogo from '@/components/layout/EsonaLogo';

interface FullPageTransitionProps {
  /** Custom message to show. Falls back to cycling phrases if not set. */
  message?: string;
}

const CYCLING_MESSAGES = [
  'Preparing your experience...',
  'Loading your safe space...',
  'Almost ready...',
];

/**
 * Lightweight full-screen transition loader.
 * Shown for 800–1000ms minimum (enforced by usePageTransition).
 * Used for all in-app page transitions after initial boot.
 */
export default function FullPageTransition({ message }: FullPageTransitionProps) {
  const [msgIndex, setMsgIndex] = useState(0);
  const [dotCount, setDotCount] = useState(1);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Cycle dots every 400ms
    const dotTimer = setInterval(() => {
      setDotCount((d) => (d % 3) + 1);
    }, 400);

    // Cycle messages every 1200ms
    const msgTimer = setInterval(() => {
      setMsgIndex((i) => (i + 1) % CYCLING_MESSAGES.length);
    }, 1200);

    return () => {
      clearInterval(dotTimer);
      clearInterval(msgTimer);
    };
  }, []);

  if (!mounted) return null;

  const displayMessage = message ?? CYCLING_MESSAGES[msgIndex];
  const dots = '.'.repeat(dotCount);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center select-none"
      style={{
        background: 'radial-gradient(circle at 50% 40%, #0B0E23 0%, #040614 100%)',
      }}
    >
      {/* Subtle CSS animation keyframes */}
      <style>{`
        @keyframes fpt-breathe {
          0%, 100% { opacity: 0.55; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.06); }
        }
        @keyframes fpt-shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
        @keyframes fpt-pulse-ring {
          0% { transform: scale(0.8); opacity: 0.6; }
          70% { transform: scale(1.4); opacity: 0; }
          100% { transform: scale(1.4); opacity: 0; }
        }
      `}</style>

      {/* Outer pulse ring */}
      <div className="relative mb-8 flex items-center justify-center" style={{ width: 96, height: 96 }}>
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: '1px solid rgba(56, 189, 248, 0.25)',
            animation: 'fpt-pulse-ring 2s ease-out infinite',
          }}
        />
        <div
          className="absolute inset-0 rounded-full"
          style={{
            border: '1px solid rgba(56, 189, 248, 0.15)',
            animation: 'fpt-pulse-ring 2s ease-out infinite 0.5s',
          }}
        />

        {/* Logo with breathing glow */}
        <div
          style={{
            animation: 'fpt-breathe 2.4s ease-in-out infinite',
          }}
        >
          <EsonaLogo
            size={52}
            showParticles={false}
            glowIntensity="medium"
            aiState="listening"
          />
        </div>
      </div>

      {/* Progress shimmer bar */}
      <div
        className="relative overflow-hidden rounded-full mb-6"
        style={{
          width: 200,
          height: 2,
          background: 'rgba(255,255,255,0.06)',
        }}
      >
        <div
          className="absolute top-0 h-full rounded-full"
          style={{
            width: '40%',
            background: 'linear-gradient(90deg, transparent, #38BDF8, #7DD3FC, transparent)',
            animation: 'fpt-shimmer 1.4s ease-in-out infinite',
          }}
        />
      </div>

      {/* Cycling message */}
      <AnimatePresence mode="wait">
        <motion.p
          key={displayMessage}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.3 }}
          className="text-sm font-medium tracking-wide"
          style={{ color: 'rgba(191, 223, 255, 0.85)' }}
        >
          {displayMessage}
          <span style={{ color: 'rgba(56, 189, 248, 0.9)' }}>{dots}</span>
        </motion.p>
      </AnimatePresence>

      {/* Brand tag */}
      <p
        className="mt-3 text-[10px] uppercase tracking-[0.22em] font-medium"
        style={{ color: 'rgba(148, 163, 184, 0.4)' }}
      >
        Esona Wellness
      </p>
    </motion.div>
  );
}
