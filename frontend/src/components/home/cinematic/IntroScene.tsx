'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import Link from 'next/link';
import EsonaLogo from '@/components/layout/EsonaLogo';
import { useAuth } from '@/providers/AuthProvider';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function IntroScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();
  const { isAuthenticated } = useAuth();

  // Opacity: fully visible at load, fades out as we scroll to Scene 2
  const opacity = useTransform(progress, [0, 0.08, 0.12, 1], [1, 1, 0, 0], { clamp: true });
  const y = useTransform(progress, [0, 0.12], [0, shouldReduceMotion ? 0 : -35]);
  const scale = useTransform(progress, [0, 0.12], [1, shouldReduceMotion ? 1 : 0.98]);

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center select-none"
      style={{
        opacity,
        y,
        scale,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* Main Composition */}
      <div className="flex flex-col items-center max-w-2xl mx-auto mt-12">
        {/* Glow Logo */}
        <div className="mb-6">
          <EsonaLogo size={72} showParticles={true} glowIntensity="high" />
        </div>

        {/* Introduction Visual Sentence */}
        <div className="relative inline-block mb-6 pt-2">
          <span 
            className="block sm:absolute sm:-top-5 sm:left-0 text-sm sm:text-base font-medium tracking-[0.15em] text-[#C2DBFF]/80 select-none"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans), sans-serif' }}
          >
            I am
          </span>
          <h1 
            className="text-6xl sm:text-7xl md:text-8xl font-semibold leading-none select-none tracking-[-0.04em]"
            style={{ 
              fontFamily: 'var(--font-plus-jakarta-sans), sans-serif',
              background: 'linear-gradient(135deg, #FFFFFF 0%, #D4E8FF 50%, #9BCBFF 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 2px 10px rgba(191, 223, 255, 0.15))'
            }}
          >
            Esona
          </h1>
          <span 
            className="block sm:absolute sm:-bottom-4 sm:right-0 text-base sm:text-lg font-normal text-[#86D2F9]/90 italic pt-1 sm:pt-0"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans), sans-serif' }}
          >
            your supportive buddy.
          </span>
        </div>

        {/* Quiet Reassurance */}
        <div className="flex flex-col items-center space-y-1 mb-10 pt-4">
          <p className="text-xs sm:text-sm text-[#8598B3] tracking-wide">
            don't worry about anything.
          </p>
          <p className="text-base sm:text-lg text-[#E6F0FF] font-medium tracking-wide" style={{ textShadow: '0 0 10px rgba(230, 240, 255, 0.2)' }}>
            I'm here for you.
          </p>
        </div>

        {/* Scroll Indicator */}
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute bottom-12 flex flex-col items-center gap-2 pointer-events-auto cursor-pointer"
          onClick={() => {
            if (typeof window !== 'undefined') {
              const globalLenis = (window as any).lenis;
              if (globalLenis) {
                globalLenis.scrollTo(window.innerHeight, { duration: 1.5 });
              } else {
                window.scrollTo({ top: window.innerHeight, behavior: 'smooth' });
              }
            }
          }}
        >
          <span className="text-[10px] uppercase tracking-[0.25em] text-[#8B9BB8]/50 font-semibold">
            Enter the quiet
          </span>
          <div className="w-[1px] h-8 bg-white/20 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1/2 bg-cyan-400 animate-scroll-line" />
          </div>
        </motion.div>
      </div>

      <style jsx global>{`
        @keyframes scroll-line {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(200%); }
        }
        .animate-scroll-line {
          animation: scroll-line 2s infinite linear;
        }
      `}</style>
    </motion.div>
  );
}
