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

  const yOffset = shouldReduceMotion ? 0 : 10;

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 pt-24 sm:pt-0 overflow-hidden">
      {/* Atmospheric glow behind hero content */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 40%, rgba(56, 189, 248, 0.06) 0%, rgba(167, 139, 250, 0.03) 45%, transparent 70%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 text-center max-w-4xl mx-auto flex flex-col items-center">
        
        {/* ZONE 1: Connected Identity Composition */}
        <div className="relative inline-block mb-10 sm:mb-12 select-none px-6">
          {/* "I am" */}
          <motion.span
            initial={{ opacity: 0, y: yOffset }}
            animate={{ opacity: 0.8, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
            className="block text-center sm:absolute sm:-top-5 sm:-left-3 text-xs sm:text-[1.15rem] font-medium tracking-[0.12em] text-[#C8E1FF] opacity-80 uppercase sm:normal-case pb-2 sm:pb-0 whitespace-nowrap"
            style={{ fontFamily: 'var(--font-plus-jakarta-sans), var(--font-inter), sans-serif' }}
          >
            I am
          </motion.span>

          {/* "Esona" */}
          <motion.h1
            initial={{ opacity: 0, y: yOffset, scale: shouldReduceMotion ? 1 : 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.9, ease: 'easeOut', delay: 0.3 }}
            className="font-semibold leading-none select-none tracking-[-0.04em] px-4 py-1"
            style={{ 
              fontFamily: 'var(--font-plus-jakarta-sans), var(--font-space-grotesk), sans-serif',
              fontSize: 'clamp(3.5rem, 8vw, 8.5rem)',
              background: 'linear-gradient(135deg, #E0F0FF 0%, #FFFFFF 50%, #A9C7FA 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              filter: 'drop-shadow(0 2px 10px rgba(191, 223, 255, 0.12))'
            }}
          >
            Esona
          </motion.h1>

          {/* "your supportive buddy." */}
          <motion.span
            initial={{ opacity: 0, y: yOffset }}
            animate={{ opacity: 0.95, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut', delay: 0.6 }}
            className="block text-center mt-2 sm:mt-0 sm:absolute sm:-bottom-3 sm:-right-8 font-normal text-[#86D2F9] opacity-95 whitespace-nowrap italic"
            style={{ 
              fontFamily: 'var(--font-plus-jakarta-sans), var(--font-inter), sans-serif',
              fontSize: 'clamp(1rem, 1.5vw, 1.35rem)',
              textShadow: '0 2px 8px rgba(0, 0, 0, 0.3)' 
            }}
          >
            your supportive buddy.
          </motion.span>
        </div>

        {/* ZONE 2: Reassurance */}
        <div className="flex flex-col items-center mb-8 sm:mb-10 space-y-1 select-none">
          {/* "Don't worry." */}
          <motion.p
            initial={{ opacity: 0, y: yOffset }}
            animate={{ opacity: 0.85, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut', delay: 0.9 }}
            className="text-xs sm:text-[0.95rem] md:text-[1.05rem] font-normal tracking-wide text-[#8598B3]"
            style={{ fontFamily: 'var(--font-inter), sans-serif' }}
          >
            Don't worry.
          </motion.p>
          {/* "I'm here with you." */}
          <motion.p
            initial={{ opacity: 0, y: yOffset }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut', delay: 1.1 }}
            className="text-base sm:text-[1.3rem] md:text-[1.45rem] font-medium tracking-wide text-[#E6F0FF]"
            style={{ 
              fontFamily: 'var(--font-inter), sans-serif',
              textShadow: '0 0 10px rgba(230, 240, 255, 0.2)'
            }}
          >
            I'm here with you.
          </motion.p>
        </div>

        {/* ZONE 3: Emotional Signature */}
        <motion.div
          initial={{ opacity: 0, y: yOffset }}
          animate={{ opacity: 0.8, y: 0 }}
          transition={{ duration: 0.9, ease: 'easeOut', delay: 1.4 }}
          className="flex flex-col sm:flex-row items-center sm:justify-center sm:space-x-3 font-light tracking-[0.08em] text-[#798DA3] mb-10 sm:mb-12 space-y-1 sm:space-y-0 select-none"
          style={{ 
            fontFamily: 'var(--font-inter), sans-serif',
            fontSize: 'clamp(0.95rem, 1.2vw, 1.15rem)'
          }}
        >
          <span>I remember.</span>
          <span className="hidden sm:inline opacity-30">•</span>
          <span>I understand.</span>
          <span className="hidden sm:inline opacity-30">•</span>
          <span>I grow with you.</span>
        </motion.div>

        {/* ZONE 4: Torch Interaction */}
        <motion.div 
          className="mt-4 sm:mt-6 md:mt-8 flex flex-col items-center min-h-[220px] sm:min-h-[240px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.7 }}
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
                  className="text-xs sm:text-sm tracking-widest uppercase font-medium"
                  style={{ color: '#8B9BB8', fontFamily: 'var(--font-space-grotesk), sans-serif' }}
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
