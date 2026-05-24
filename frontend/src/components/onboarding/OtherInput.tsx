'use client';

import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface OtherInputProps {
  isVisible: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function OtherInput({ isVisible, value, onChange }: OtherInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isVisible && inputRef.current) {
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isVisible]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, height: 0, marginTop: 0 }}
          animate={{ opacity: 1, height: 'auto', marginTop: 12 }}
          exit={{ opacity: 0, height: 0, marginTop: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="overflow-hidden"
        >
          <div className="relative">
            <textarea
              ref={inputRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              placeholder="Tell us in your own words..."
              rows={3}
              className="w-full px-4 py-3 glass-input resize-none text-sm leading-relaxed"
              style={{
                minHeight: '80px',
                fontFamily: 'inherit',
              }}
              maxLength={300}
            />
            <div className="absolute bottom-2 right-3">
              <span
                className="text-xs"
                style={{
                  color: value.length > 250 ? 'var(--accent-pink)' : 'var(--text-muted)',
                }}
              >
                {value.length}/300
              </span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
