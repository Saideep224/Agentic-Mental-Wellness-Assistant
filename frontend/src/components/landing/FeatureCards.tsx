'use client';

import { motion } from 'framer-motion';
import { Brain, MessageCircle, Waves } from 'lucide-react';

const features = [
  {
    icon: Brain,
    emoji: '🧠',
    title: 'Understands You',
    description:
      'A multi-agent system that analyzes your personality, emotional patterns, and communication style to truly get who you are.',
    gradient: 'linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(59, 130, 246, 0.05))',
    glowColor: 'var(--glow-cyan)',
    iconColor: 'var(--accent-cyan)',
  },
  {
    icon: MessageCircle,
    emoji: '💭',
    title: 'Remembers Your Story',
    description:
      'Emotional memory that grows with every conversation. Esona remembers what matters to you and builds context over time.',
    gradient: 'linear-gradient(135deg, rgba(167, 139, 250, 0.1), rgba(244, 114, 182, 0.05))',
    glowColor: 'var(--glow-purple)',
    iconColor: 'var(--accent-purple)',
  },
  {
    icon: Waves,
    emoji: '🌊',
    title: 'Adapts to You',
    description:
      'Communication style that matches your preferences — whether you need a friend, a listener, or honest perspective.',
    gradient: 'linear-gradient(135deg, rgba(52, 211, 153, 0.1), rgba(34, 211, 238, 0.05))',
    glowColor: 'var(--glow-emerald)',
    iconColor: 'var(--accent-emerald)',
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' as const },
  },
};

export default function FeatureCards() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2
            className="text-3xl sm:text-4xl font-bold mb-4 glow-text"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            More than a chatbot
          </h2>
          <p className="text-lg max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
            Esona is a multi-agent AI system designed to understand and support your emotional wellbeing.
          </p>
        </motion.div>

        {/* Feature cards */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={cardVariants}
              whileHover={{ scale: 1.03, y: -5 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              className="glass-card p-8 cursor-default group"
              style={{
                background: feature.gradient,
              }}
            >
              {/* Icon */}
              <div className="mb-6">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center transition-shadow duration-300 group-hover:shadow-lg"
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--glass-border)',
                  }}
                >
                  <span className="text-2xl">{feature.emoji}</span>
                </div>
              </div>

              {/* Title */}
              <h3
                className="text-xl font-semibold mb-3"
                style={{
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-outfit), sans-serif',
                }}
              >
                {feature.title}
              </h3>

              {/* Description */}
              <p
                className="text-sm leading-relaxed"
                style={{ color: 'var(--text-secondary)' }}
              >
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
