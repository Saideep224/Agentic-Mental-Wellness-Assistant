'use client';

import { motion } from 'framer-motion';

const agentConfig: Record<string, { emoji: string; name: string; gradient: string; border: string }> = {
  buddy: { emoji: '💙', name: 'Esona', gradient: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)', border: 'rgba(56, 189, 248, 0.3)' },
  lex: { emoji: '⚖️', name: 'Lex', gradient: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)', border: 'rgba(245, 158, 11, 0.3)' },
  maya: { emoji: '👨‍⚕️', name: 'Dr. Maya', gradient: 'linear-gradient(135deg, #059669 0%, #047857 100%)', border: 'rgba(16, 185, 129, 0.3)' },
  ray: { emoji: '👮', name: 'Officer Ray', gradient: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', border: 'rgba(239, 68, 68, 0.3)' },
  techie: { emoji: '💻', name: 'Techie', gradient: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)', border: 'rgba(99, 102, 241, 0.3)' },
  mentor: { emoji: '📚', name: 'Mentor', gradient: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', border: 'rgba(139, 92, 246, 0.3)' },
  finance: { emoji: '💰', name: 'Finance Coach', gradient: 'linear-gradient(135deg, #db2777 0%, #be185d 100%)', border: 'rgba(236, 72, 153, 0.3)' },
  fitness: { emoji: '🏋️', name: 'Fitness Coach', gradient: 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)', border: 'rgba(20, 184, 166, 0.3)' },
  relationship: { emoji: '💜', name: 'Relationship Coach', gradient: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'rgba(168, 85, 247, 0.3)' },
};

interface TypingIndicatorProps {
  agentId?: string;
}

export default function TypingIndicator({ agentId = 'buddy' }: TypingIndicatorProps) {
  const config = agentConfig[agentId] || agentConfig.buddy;

  const dotVariants = {
    animate: (i: number) => ({
      scale: [1, 1.35, 1],
      opacity: [0.4, 1, 0.4],
      transition: {
        duration: 0.9,
        repeat: Infinity,
        ease: 'easeInOut' as const,
        delay: i * 0.3,
      },
    }),
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      className="flex items-end gap-3 mb-6 justify-start select-none"
    >
      {/* AI Avatar */}
      <div className="flex-shrink-0 mb-1">
        <div
          className="w-9 h-9 rounded-full flex items-center justify-center text-lg select-none"
          style={{
            background: config.gradient,
            boxShadow: `0 0 12px ${config.border}`,
          }}
        >
          {config.emoji}
        </div>
      </div>

      {/* Bubble Container */}
      <div className="max-w-[75%]">
        {/* Agent Name */}
        <div 
          className="text-xs font-semibold mb-1 px-1 select-none flex items-center gap-1.5" 
          style={{ color: 'var(--text-secondary)' }}
        >
          <span>{config.emoji}</span>
          <span>{config.name}</span>
        </div>

        {/* Typing Bubble */}
        {/* Typing Bubble and Text Status */}
        <div className="flex items-center gap-3">
          <div
            className="rounded-2xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(167, 139, 250, 0.1) 0%, rgba(244, 114, 182, 0.05) 100%)',
              border: '1px solid rgba(167, 139, 250, 0.18)',
              boxShadow: '0 4px 15px rgba(167, 139, 250, 0.03)',
              borderBottomLeftRadius: '6px',
              borderBottomRightRadius: '18px',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              width: '68px',
              height: '38px',
            }}
          >
            {/* Animated Dots */}
            <div className="flex items-center justify-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  custom={i}
                  variants={dotVariants}
                  animate="animate"
                  className="w-2.5 h-2.5 rounded-full"
                  style={{
                    backgroundColor: agentId === 'buddy' ? '#38BDF8' : '#A855F7',
                  }}
                />
              ))}
            </div>
          </div>
          <span 
            className="text-xs font-medium animate-pulse select-none" 
            style={{ color: 'var(--text-muted)' }}
          >
            {config.name} is thinking...
          </span>
        </div>
      </div>
    </motion.div>
  );
}
