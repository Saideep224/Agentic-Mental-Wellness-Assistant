'use client';

import { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';
import InteractiveTorch from './InteractiveTorch';
import EsonaGetStartedButton from './EsonaGetStartedButton';

export default function HeroSection() {
  const [torchState, setTorchState] = useState<'unlit' | 'lighting' | 'revealing_text' | 'revealed_cta'>('unlit');
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const shouldReduceMotion = useReducedMotion();

  const handleBeginJourney = () => {
    if (isAuthenticated) {
      router.push('/chat');
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
      <div className="relative z-10 text-center max-w-3xl mx-auto flex flex-col items-center">
        {/* Title container for "I am" and "Esona" */}
        <div className="relative inline-block mb-3 sm:mb-4">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.9 }}
            transition={{ duration: 1.0, ease: 'easeOut', delay: 0.1 }}
            className="block sm:absolute sm:-top-6 sm:left-1 text-sm sm:text-base md:text-lg font-medium tracking-[0.2em] text-[#C2DBFF] opacity-90 pb-1 sm:pb-0"
            style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
          >
            I am
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 25, scale: shouldReduceMotion ? 1 : 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.9, ease: 'easeOut', delay: 0.3 }}
            className="text-6xl sm:text-8xl md:text-9xl font-bold leading-none select-none pt-1"
            style={{ 
              fontFamily: 'var(--font-space-grotesk), sans-serif',
              background: 'linear-gradient(135deg, #FFFFFF 0%, #D4E8FF 50%, #9BCBFF 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 4px 12px rgba(191, 223, 255, 0.2))'
            }}
          >
            Esona
          </motion.h1>
        </div>

        {/* your supportive buddy. */}
        <motion.p
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.6 }}
          className="text-xl sm:text-2xl md:text-3xl font-medium tracking-wide mb-6 sm:mb-8"
          style={{ 
            color: '#AFC7E8', 
            fontFamily: 'var(--font-space-grotesk), sans-serif', 
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.4)' 
          }}
        >
          your supportive buddy.
        </motion.p>

        {/* Don't worry, I'm here with you. */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.95 }}
          transition={{ duration: 1.0, ease: 'easeOut', delay: 0.9 }}
          className="text-base sm:text-lg md:text-xl font-light tracking-wide mb-5 sm:mb-6"
          style={{ 
            color: '#F0F4FA', 
            textShadow: '0 0 15px rgba(191, 223, 255, 0.3)' 
          }}
        >
          Don't worry, I'm here with you.
        </motion.p>

        {/* Personal Description */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.0, ease: 'easeOut', delay: 1.2 }}
          className="text-sm sm:text-base md:text-lg max-w-[650px] md:max-w-[720px] mx-auto leading-relaxed"
          style={{ 
            color: '#A8BDD6', 
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.5)' 
          }}
        >
          I remember, understand, and grow with you — so you never have to feel like you're talking to a stranger.
        </motion.p>

        {/* Interactive Area */}
        <motion.div 
          className="mt-8 sm:mt-10 md:mt-12 flex flex-col items-center min-h-[240px] sm:min-h-[260px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.5 }}
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
                <EsonaGetStartedButton onClick={handleBeginJourney} />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </section>
  );
}
