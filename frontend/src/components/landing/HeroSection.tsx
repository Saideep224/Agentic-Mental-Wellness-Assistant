'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';
import InteractiveTorch from './InteractiveTorch';

export default function HeroSection() {
  const [torchState, setTorchState] = useState<'unlit' | 'lighting' | 'revealing_text' | 'revealed_cta'>('unlit');
  const router = useRouter();
  const { isAuthenticated } = useAuth();

  const handleBeginJourney = () => {
    if (isAuthenticated) {
      router.push('/onboarding');
    } else {
      router.push('/login');
    }
  };

  const handleLightTorch = () => {
    if (torchState !== 'unlit') return;
    
    setTorchState('lighting');
    
    // Wait for torch glow to expand
    setTimeout(() => {
      setTorchState('revealing_text');
      
      // Wait for text to finish reading
      setTimeout(() => {
        setTorchState('revealed_cta');
      }, 1500);
    }, 1000);
  };

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 sm:pt-0 overflow-hidden">
      {/* Atmospheric glow behind hero content */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 40%, rgba(56, 189, 248, 0.08) 0%, rgba(167, 139, 250, 0.04) 40%, transparent 70%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 text-center max-w-3xl mx-auto">
        {/* Main title */}
        <motion.h1
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: 'easeOut' as const }}
          className="text-7xl sm:text-8xl md:text-9xl font-bold mb-3"
          style={{ 
            fontFamily: 'var(--font-space-grotesk), sans-serif',
            background: 'linear-gradient(90deg, #FFFFFF 0%, #BFDFFF 50%, #8BC5FF 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}
        >
          Esona
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' as const }}
          className="text-xl sm:text-2xl mb-8 tracking-wide"
          style={{ color: '#AFC7E8', fontWeight: 500, fontFamily: 'var(--font-space-grotesk), sans-serif', textShadow: '0 2px 15px rgba(0, 0, 0, 0.4)' }}
        >
          The Sound of Understanding
        </motion.p>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: 'easeOut' as const }}
          className="text-base sm:text-lg max-w-xl mx-auto leading-relaxed"
          style={{ color: '#D6E2F2', textShadow: '0 2px 20px rgba(0, 0, 0, 0.5)' }}
        >
          An emotionally intelligent AI companion that remembers, understands, and grows with you.
        </motion.p>

        {/* Interactive Area */}
        <motion.div 
          className="mt-12 flex flex-col items-center min-h-[280px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.8 }}
        >
          {/* Torch */}
          <div className="mb-4">
            <InteractiveTorch onLight={handleLightTorch} />
          </div>

          {/* Reveal Sequence */}
          <div className="h-16 relative w-full mb-6 flex flex-col items-center justify-center">
            <AnimatePresence mode="wait">
              {torchState === 'unlit' && (
                <motion.p
                  key="unlit"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.6 }}
                  exit={{ opacity: 0, transition: { duration: 0.3 } }}
                  className="text-sm tracking-widest uppercase"
                  style={{ color: '#8B9BB8' }}
                >
                  Click to light the way
                </motion.p>
              )}

              {(torchState === 'revealing_text' || torchState === 'revealed_cta') && (
                <motion.div
                  key="revealed_text"
                  initial={{ opacity: 0, filter: 'blur(4px)', y: 10 }}
                  animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
                  transition={{ duration: 1 }}
                  className="text-center"
                >
                  <p className="text-xl font-medium" style={{ color: '#FFD166', fontFamily: 'var(--font-space-grotesk), sans-serif', textShadow: '0 0 10px rgba(255, 209, 102, 0.5)' }}>
                    Welcome back.
                  </p>
                  <p className="text-base mt-1" style={{ color: '#E2E8F0', fontFamily: 'var(--font-inter), sans-serif' }}>
                    The journey continues.
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* CTA Button */}
          <AnimatePresence>
            {torchState === 'revealed_cta' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              >
                <button
                  onClick={handleBeginJourney}
                  className="inline-flex items-center gap-2 px-8 py-4 text-lg font-semibold rounded-2xl transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(59,201,255,0.4)]"
                  style={{
                    background: 'linear-gradient(90deg, #3BC9FF, #6C8CFF)',
                    color: '#FFFFFF',
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
                  }}
                >
                  <span>Begin Your Journey</span>
                  <motion.span
                    animate={{ x: [0, 4, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    →
                  </motion.span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </section>
  );
}
