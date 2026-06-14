'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const messages = [
  "Esona is listening...",
  "Reading your responses...",
  "Reflecting on your words...",
  "Sensing the energy...",
  "Typing a reply...",
];

export default function TypingIndicator() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % messages.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex items-end gap-3 mb-4"
    >
      {/* AI avatar */}
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
        style={{
          background: 'var(--gradient-primary)',
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
              className="w-2 h-2 rounded-full typing-dot animate-bounce"
              style={{
                backgroundColor: 'var(--accent-purple)',
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
        <AnimatePresence mode="wait">
          <motion.span
            key={index}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.2 }}
            className="text-xs"
            style={{ color: 'var(--text-muted)' }}
          >
            {messages[index]}
          </motion.span>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
