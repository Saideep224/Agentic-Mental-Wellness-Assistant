'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

export default function CTASection() {
  return (
    <section className="relative py-32 px-6 overflow-hidden">
      {/* Gradient background */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, rgba(34, 211, 238, 0.06) 0%, rgba(167, 139, 250, 0.03) 40%, transparent 70%)',
        }}
      />

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-2xl sm:text-3xl font-light leading-relaxed mb-4"
          style={{
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-outfit), sans-serif',
          }}
        >
          You don&apos;t have to figure it all out alone.
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-lg mb-10"
          style={{ color: 'var(--text-muted)' }}
        >
          Esona is here whenever you need — no judgment, just understanding.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href="/login"
            className="gradient-btn-purple px-8 py-4 text-base rounded-2xl inline-flex items-center gap-2 transition-all duration-300"
            style={{
              boxShadow: '0 0 25px rgba(167, 139, 250, 0.2), 0 4px 15px rgba(0, 0, 0, 0.3)',
            }}
          >
            <span>Start a Conversation</span>
            <span>💬</span>
          </Link>

          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Free to use • No sign-up spam • Your space
          </p>
        </motion.div>
      </div>
    </section>
  );
}
