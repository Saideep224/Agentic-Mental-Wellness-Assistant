'use client';

import { motion } from 'framer-motion';
import { Brain, MessageCircle, Cloud } from 'lucide-react';

function UnderstandsYouAnimation() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-2xl">
      {/* Concentric pulsing rings */}
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute top-1/2 left-1/2 w-48 h-48 rounded-full border border-cyan-500/10"
          style={{ x: '-50%', y: '-50%' }}
          animate={{
            scale: [0.2, 1.4],
            opacity: [0.5, 0],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            delay: i * 1.6,
            ease: 'easeOut',
          }}
        />
      ))}
      {/* Horizontal grid scan line */}
      <motion.div
        className="absolute left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-cyan-400/15 to-transparent"
        animate={{
          top: ['0%', '100%'],
        }}
        transition={{
          duration: 7,
          repeat: Infinity,
          ease: 'linear',
        }}
      />
    </div>
  );
}

function RemembersYourStoryAnimation() {
  const particles = [
    { x: ['10%', '80%', '20%'], y: ['20%', '70%', '40%'], scale: [0.8, 1.2, 0.8] },
    { x: ['90%', '30%', '70%'], y: ['40%', '80%', '30%'], scale: [1, 0.6, 1.1] },
    { x: ['20%', '60%', '10%'], y: ['80%', '20%', '70%'], scale: [0.7, 1.1, 0.7] },
    { x: ['70%', '15%', '85%'], y: ['15%', '45%', '85%'], scale: [1.1, 0.8, 1.1] },
    { x: ['35%', '85%', '45%'], y: ['55%', '15%', '85%'], scale: [0.8, 1.1, 0.8] },
  ];
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-2xl">
      {particles.map((p, i) => (
        <motion.div
          key={i}
          className="absolute w-1.5 h-1.5 rounded-full"
          style={{
            background: 'rgba(167, 139, 250, 0.2)',
            filter: 'blur(0.5px)',
            boxShadow: '0 0 6px rgba(167, 139, 250, 0.4)',
          }}
          animate={{
            left: p.x,
            top: p.y,
            scale: p.scale,
          }}
          transition={{
            duration: 14 + i * 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
}

function AdaptsToYouAnimation() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none rounded-2xl flex items-end justify-center pb-8 opacity-15 group-hover:opacity-35 transition-opacity duration-500">
      {/* Morphing blob */}
      <motion.div
        className="absolute top-1/2 left-1/2 w-44 h-44 rounded-full"
        style={{
          x: '-50%',
          y: '-50%',
          background: 'radial-gradient(circle, rgba(52, 211, 153, 0.12) 0%, transparent 70%)',
          filter: 'blur(8px)',
        }}
        animate={{
          borderRadius: [
            '40% 60% 70% 30% / 40% 40% 60% 60%',
            '70% 30% 50% 50% / 60% 40% 60% 40%',
            '40% 60% 70% 30% / 40% 40% 60% 60%',
          ],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 9,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
      {/* Mini equalizer bars */}
      <div className="flex items-end gap-1 h-8 z-10">
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <motion.div
            key={i}
            className="w-0.5 bg-emerald-400/20 rounded-full"
            animate={{
              height: [
                '15%',
                i % 2 === 0 ? '60%' : '40%',
                i % 3 === 0 ? '80%' : '25%',
                '15%',
              ],
            }}
            transition={{
              duration: 1.6 + (i * 0.15),
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </div>
  );
}

const features = [
  {
    icon: Brain,
    emoji: '🧠',
    title: 'Understands You',
    description:
      'A multi-agent system that analyzes your personality, emotional patterns, and communication style to truly get who you are.',
    gradient: 'linear-gradient(135deg, rgba(56, 189, 248, 0.06), rgba(59, 130, 246, 0.03))',
    glowColor: 'var(--glow-cyan)',
    iconColor: 'var(--accent-cyan)',
    animation: UnderstandsYouAnimation,
  },
  {
    icon: MessageCircle,
    emoji: '💭',
    title: 'Remembers Your Story',
    description:
      'Emotional memory that grows with every conversation. Esona remembers what matters to you and builds context over time.',
    gradient: 'linear-gradient(135deg, rgba(167, 139, 250, 0.06), rgba(244, 114, 182, 0.03))',
    glowColor: 'var(--glow-purple)',
    iconColor: 'var(--accent-purple)',
    animation: RemembersYourStoryAnimation,
  },
  {
    icon: Cloud,
    emoji: '☁️',
    title: 'Adapts to You',
    description:
      'Communication style that matches your preferences — whether you need a friend, a listener, or honest perspective.',
    gradient: 'linear-gradient(135deg, rgba(52, 211, 153, 0.06), rgba(56, 189, 248, 0.03))',
    glowColor: 'var(--glow-emerald)',
    iconColor: 'var(--accent-emerald)',
    animation: AdaptsToYouAnimation,
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
            style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
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
          {features.map((feature) => {
            const Animation = feature.animation;
            return (
              <motion.div
                key={feature.title}
                variants={cardVariants}
                whileHover={{ scale: 1.03, y: -5 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                className="glass-card p-8 cursor-default group relative overflow-hidden"
                style={{
                  background: feature.gradient,
                }}
              >
                {/* Background theme animation */}
                <Animation />

                {/* Content wrapper to float above the animation */}
                <div className="relative z-10">
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
                      fontFamily: 'var(--font-space-grotesk), sans-serif',
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
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
