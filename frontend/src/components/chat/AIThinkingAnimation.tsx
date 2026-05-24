'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const agentStages = [
  { name: 'Emotion Agent', status: 'Understanding your emotions...', color: 'var(--accent-purple)' },
  { name: 'Context Agent', status: 'Analyzing context...', color: 'var(--accent-blue)' },
  { name: 'Personality Agent', status: 'Matching your style...', color: 'var(--accent-cyan)' },
  { name: 'Response Agent', status: 'Crafting a response...', color: 'var(--accent-emerald)' },
];

export default function AIThinkingAnimation() {
  const [activeAgent, setActiveAgent] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveAgent((prev) => (prev + 1) % agentStages.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="glass-card p-6 max-w-sm mx-auto"
    >
      {/* Agent orbs in a circle */}
      <div className="relative w-32 h-32 mx-auto mb-4">
        {agentStages.map((agent, i) => {
          const angle = (i * 360) / agentStages.length - 90;
          const radian = (angle * Math.PI) / 180;
          const x = 50 + 40 * Math.cos(radian);
          const y = 50 + 40 * Math.sin(radian);
          const isActive = i === activeAgent;

          return (
            <motion.div
              key={agent.name}
              className="absolute rounded-full"
              style={{
                width: isActive ? 16 : 10,
                height: isActive ? 16 : 10,
                left: `${x}%`,
                top: `${y}%`,
                transform: 'translate(-50%, -50%)',
                background: agent.color,
                boxShadow: isActive ? `0 0 20px ${agent.color}` : 'none',
                opacity: isActive ? 1 : 0.3,
                transition: 'all 0.5s ease',
              }}
            />
          );
        })}

        {/* Center spinning indicator */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 rounded-full animate-spin-slow"
          style={{
            border: '2px solid transparent',
            borderTopColor: agentStages[activeAgent].color,
            borderRightColor: agentStages[activeAgent].color,
          }}
        />
      </div>

      {/* Status text */}
      <div className="text-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeAgent}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.3 }}
          >
            <p
              className="text-xs font-medium mb-1"
              style={{ color: agentStages[activeAgent].color }}
            >
              {agentStages[activeAgent].name}
            </p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {agentStages[activeAgent].status}
            </p>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
