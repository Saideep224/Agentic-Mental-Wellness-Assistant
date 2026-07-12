'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';
import EsonaLogo from '@/components/layout/EsonaLogo';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function FinalScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  // Scene visible range: [0.875, 1.0]
  const opacity = useTransform(progress, [0, 0.875, 0.895, 1.0], [0, 0, 1, 1], { clamp: true });
  const y = useTransform(progress, [0.875, 1.0], [20, 0], { clamp: true });

  // Phase 1: "You don't need the perfect words." (0.875 to 0.925)
  // Fades in: 0.875 -> 0.895 | Holds: 0.895 -> 0.915 | Exits: 0.915 -> 0.925
  const text1Opacity = useTransform(progress, [0, 0.875, 0.895, 0.915, 0.925, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 2: "Just talk." (0.925 to 0.965)
  // Fades in: 0.925 -> 0.94 | Holds: 0.94 -> 0.955 | Exits: 0.955 -> 0.965
  const text2Opacity = useTransform(progress, [0, 0.925, 0.94, 0.955, 0.965, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 3: Final Call To Action (0.960 to 1.0)
  // Fades in: 0.96 -> 0.975 | Holds: 0.975 -> 1.0
  const ctaOpacity = useTransform(progress, [0, 0.96, 0.975, 1.0], [0, 0, 1, 1], { clamp: true });
  const ctaY = useTransform(progress, [0.96, 0.975], [25, 0], { clamp: true });

  const handleBeginJourney = () => {
    if (isAuthenticated) {
      router.push('/chat');
    } else {
      router.push('/login');
    }
  };

  const handleLearnMore = () => {
    if (typeof window === 'undefined') return;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    // Map to Scene 4 (Listening deeper / Emotion understanding)
    // Index 3 of the 8 scenes (indices 0..7), so 3/7 of scroll range
    const targetScroll = docHeight * (3 / 7);
    window.scrollTo({
      top: targetScroll,
      behavior: 'smooth'
    });
  };

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        y: shouldReduceMotion ? 0 : y,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* 1. You don't need the perfect words */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{ opacity: text1Opacity }}
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-300 leading-snug">
          You don't need <br />
          <span className="font-semibold text-white">the perfect words.</span>
        </h2>
      </motion.div>

      {/* 2. Just talk */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{ opacity: text2Opacity }}
      >
        <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[0.1em] text-cyan-400" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif', textShadow: '0 0 12px rgba(34,211,238,0.2)' }}>
          Just talk.
        </h2>
      </motion.div>

      {/* 3. Final Call to Action */}
      <motion.div
        className="absolute text-center max-w-2xl mx-auto flex flex-col items-center gap-6"
        style={{
          opacity: ctaOpacity,
          y: shouldReduceMotion ? 0 : ctaY,
        }}
      >
        {/* Glow Logo */}
        <div className="mb-4 pointer-events-auto cursor-pointer" onClick={handleBeginJourney}>
          <EsonaLogo size={64} showParticles={true} glowIntensity="high" />
        </div>

        {/* Diagonal Visual Sentence */}
        <div className="relative inline-block mb-4 pt-1">
          <span 
            className="block sm:absolute sm:-top-5 sm:left-0 text-sm font-medium tracking-[0.15em] text-[#C2DBFF]/80"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans), sans-serif' }}
          >
            I am
          </span>
          <h1 
            className="text-5xl sm:text-6xl md:text-7xl font-semibold leading-none tracking-[-0.04em]"
            style={{ 
              fontFamily: 'var(--font-plus-jakarta-sans), sans-serif',
              background: 'linear-gradient(135deg, #FFFFFF 0%, #D4E8FF 50%, #9BCBFF 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 2px 10px rgba(191, 223, 255, 0.12))'
            }}
          >
            Esona
          </h1>
          <span 
            className="block sm:absolute sm:-bottom-4 sm:right-0 text-base font-normal text-[#86D2F9]/90 italic pt-1 sm:pt-0"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans), sans-serif' }}
          >
            your supportive buddy.
          </span>
        </div>

        <p className="text-sm text-[#8BA0B8] mb-4">
          I'm here for you.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 pointer-events-auto">
          <button
            onClick={handleBeginJourney}
            className="gradient-btn px-8 py-3.5 text-sm rounded-xl flex items-center gap-2 cursor-pointer shadow-[0_4px_20px_rgba(123,140,255,0.2)] hover:shadow-[0_4px_25px_rgba(123,140,255,0.35)] transition-all duration-300 font-semibold"
          >
            Talk to Esona →
          </button>
          
          <button
            onClick={handleLearnMore}
            className="px-6 py-3.5 text-sm rounded-xl border border-white/10 hover:border-cyan-400/20 text-[#8B9BB8] hover:text-white transition-all duration-300 cursor-pointer bg-white/[0.02]"
            style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
          >
            Know how Esona understands you
          </button>
        </div>
      </motion.div>

      {/* Disclaimer / Footer */}
      <div className="absolute bottom-6 left-6 right-6 text-center max-w-2xl mx-auto opacity-50 pointer-events-none select-none">
        <p className="text-[9px] sm:text-[10px] leading-relaxed mb-2 text-[#8B9BB8]">
          Note: Esona is an AI wellness companion, not a licensed therapist or crisis counselor. If you are in distress or danger, please contact professional emergency services or helplines.
        </p>
        <p className="text-[9px] text-[#8B9BB8]/60">
          © {new Date().getFullYear()} Esona — Your AI Wellness Companion. Built with care. 💙
        </p>
      </div>
    </motion.div>
  );
}
