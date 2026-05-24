'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import BreathingOrb from '@/components/ambient/BreathingOrb';

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden">
      {/* Background breathing orb */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-60">
        <BreathingOrb size={400} />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center max-w-3xl mx-auto">
        {/* Main title */}
        <motion.h1
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.8, ease: 'easeOut' as const }}
          className="text-7xl sm:text-8xl md:text-9xl font-bold mb-4 glow-text"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          Esona
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' as const }}
          className="text-xl sm:text-2xl mb-6 tracking-wide"
          style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          your supporting buddie
        </motion.p>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: 'easeOut' as const }}
          className="text-base sm:text-lg mb-12 max-w-xl mx-auto leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}
        >
          An emotionally adaptive AI that truly understands you — your moods, your words, your silence.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.6, ease: 'easeOut' as const }}
        >
          <Link
            href="/login"
            className="inline-flex items-center gap-2 px-8 py-4 text-lg font-semibold rounded-2xl transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
              color: 'var(--bg-primary)',
              boxShadow: '0 0 30px rgba(34, 211, 238, 0.3), 0 4px 20px rgba(0, 0, 0, 0.3)',
            }}
          >
            <span>Begin Your Journey</span>
            <motion.span
              animate={{ x: [0, 4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              →
            </motion.span>
          </Link>
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="w-6 h-10 rounded-full border-2 flex items-start justify-center pt-2"
            style={{ borderColor: 'var(--text-muted)' }}
          >
            <div
              className="w-1.5 h-3 rounded-full"
              style={{ background: 'var(--accent-cyan)' }}
            />
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
