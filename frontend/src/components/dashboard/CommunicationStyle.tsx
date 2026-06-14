'use client';

import { motion } from 'framer-motion';
import { CommunicationPreference } from '@/types';
import { Heart, ShieldCheck, AlertTriangle } from 'lucide-react';

interface CommunicationStyleProps {
  preferences: CommunicationPreference | null;
}

export default function CommunicationStyle({ preferences }: CommunicationStyleProps) {
  const defaultPrefs: CommunicationPreference = {
    preferredTone: 'Warm and understanding, like a close friend',
    whatHelps: [
      'Active listening without judgment',
      'Validation of emotions before advice',
      'Gentle humor when appropriate',
      'Short, thoughtful responses',
    ],
    whatToAvoid: [
      'Toxic positivity or dismissive phrases',
      'Overly formal or robotic language',
      'Unsolicited advice when just venting',
      'Generic or vague responses',
    ],
  };

  const prefs = preferences || defaultPrefs;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="glass-card p-6"
    >
      <h3
        className="text-lg font-semibold mb-1"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-space-grotesk), sans-serif',
        }}
      >
        Communication Guide
      </h3>
      <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
        How Esona adapts to communicate with you
      </p>

      {/* Preferred Tone */}
      <div className="mb-5">
        <div className="flex items-center gap-2 mb-3">
          <Heart size={14} style={{ color: 'var(--accent-pink)' }} />
          <span
            className="text-sm font-medium"
            style={{ color: 'var(--accent-pink)' }}
          >
            Preferred Tone
          </span>
        </div>
        <p
          className="text-sm pl-6 italic"
          style={{ color: 'var(--text-secondary)' }}
        >
          &ldquo;{prefs.preferredTone}&rdquo;
        </p>
      </div>

      {/* What Helps */}
      <div className="mb-5">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck size={14} style={{ color: 'var(--accent-emerald)' }} />
          <span
            className="text-sm font-medium"
            style={{ color: 'var(--accent-emerald)' }}
          >
            What Helps Most
          </span>
        </div>
        <ul className="space-y-2 pl-6">
          {prefs.whatHelps.map((item, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.08 }}
              className="flex items-start gap-2 text-sm"
              style={{ color: 'var(--text-secondary)' }}
            >
              <span style={{ color: 'var(--accent-emerald)' }}>•</span>
              {item}
            </motion.li>
          ))}
        </ul>
      </div>

      {/* What to Avoid */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={14} style={{ color: 'var(--accent-purple)' }} />
          <span
            className="text-sm font-medium"
            style={{ color: 'var(--accent-purple)' }}
          >
            What to Avoid
          </span>
        </div>
        <ul className="space-y-2 pl-6">
          {prefs.whatToAvoid.map((item, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + i * 0.08 }}
              className="flex items-start gap-2 text-sm"
              style={{ color: 'var(--text-secondary)' }}
            >
              <span style={{ color: 'var(--accent-purple)' }}>•</span>
              {item}
            </motion.li>
          ))}
        </ul>
      </div>
    </motion.div>
  );
}
