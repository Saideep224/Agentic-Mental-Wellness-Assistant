'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

export default function HeroSection() {
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
          className="text-7xl sm:text-8xl md:text-9xl font-bold mb-3 glow-text"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          Esona
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' as const }}
          className="text-xl sm:text-2xl mb-8 tracking-wide"
          style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          your supporting buddie
        </motion.p>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: 'easeOut' as const }}
          className="text-base sm:text-lg mb-10 max-w-xl mx-auto leading-relaxed"
          style={{ color: 'rgba(255, 255, 255, 0.6)' }}
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
              boxShadow: '0 0 30px rgba(56, 189, 248, 0.3), 0 4px 20px rgba(0, 0, 0, 0.3)',
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
      </div>
    </section>
  );
}
