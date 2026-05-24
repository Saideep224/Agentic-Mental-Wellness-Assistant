'use client';

import { motion } from 'framer-motion';

export default function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex items-end gap-3"
    >
      {/* AI avatar */}
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
        style={{
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
          color: 'var(--bg-primary)',
        }}
      >
        E
      </div>

      {/* Typing bubble */}
      <div
        className="px-5 py-4 rounded-2xl flex items-center gap-3"
        style={{
          background: 'rgba(167, 139, 250, 0.08)',
          border: '1px solid rgba(167, 139, 250, 0.15)',
          borderBottomLeftRadius: '6px',
          backdropFilter: 'blur(10px)',
          WebkitBackdropFilter: 'blur(10px)',
        }}
      >
        {/* Dots */}
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full typing-dot"
              style={{
                backgroundColor: 'var(--accent-purple)',
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Esona is thinking...
        </span>
      </div>
    </motion.div>
  );
}
