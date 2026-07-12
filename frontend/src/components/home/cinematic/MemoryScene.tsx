'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import { MEMORY_FRAGMENTS } from './demoData';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function MemoryScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();

  // Scene visible range: [0.50, 0.625]
  const opacity = useTransform(progress, [0, 0.50, 0.515, 0.615, 0.625, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 1: "Most conversations are forgotten." (0.50 to 0.545)
  // Fades in: 0.50 -> 0.515 | Holds: 0.515 -> 0.535 | Exits: 0.535 -> 0.545
  const text1Opacity = useTransform(progress, [0, 0.50, 0.515, 0.535, 0.545, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const text1Y = useTransform(progress, [0.50, 0.545], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Phase 2: "Esona remembers what matters." (0.545 to 0.59)
  // Fades in: 0.545 -> 0.56 | Holds: 0.56 -> 0.58 | Exits: 0.58 -> 0.59
  const text2Opacity = useTransform(progress, [0, 0.545, 0.56, 0.58, 0.59, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const text2Y = useTransform(progress, [0.545, 0.59], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Phase 3: Memory fragments fade in one by one (0.555 to 0.615)
  const frag0Opacity = useTransform(progress, [0, 0.555, 0.565, 0.605, 0.615, 1], [0, 0, 0.85, 0.85, 0, 0], { clamp: true });
  const frag1Opacity = useTransform(progress, [0, 0.565, 0.575, 0.605, 0.615, 1], [0, 0, 0.85, 0.85, 0, 0], { clamp: true });
  const frag2Opacity = useTransform(progress, [0, 0.575, 0.585, 0.605, 0.615, 1], [0, 0, 0.85, 0.85, 0, 0], { clamp: true });
  const frag3Opacity = useTransform(progress, [0, 0.585, 0.595, 0.605, 0.615, 1], [0, 0, 0.85, 0.85, 0, 0], { clamp: true });
  const frag4Opacity = useTransform(progress, [0, 0.595, 0.605, 0.605, 0.615, 1], [0, 0, 0.85, 0.85, 0, 0], { clamp: true });

  const fragY = useTransform(progress, [0.555, 0.615], [30, shouldReduceMotion ? 30 : -30], { clamp: true });

  const getFragOpacity = (idx: number) => {
    if (idx === 0) return frag0Opacity;
    if (idx === 1) return frag1Opacity;
    if (idx === 2) return frag2Opacity;
    if (idx === 3) return frag3Opacity;
    return frag4Opacity;
  };

  // Phase 4: "Not every word. The things that make you, you." (0.585 to 0.625)
  // Fades in: 0.585 -> 0.595 | Holds: 0.595 -> 0.615 | Exits: 0.615 -> 0.625
  const text3Opacity = useTransform(progress, [0, 0.585, 0.595, 0.615, 0.625, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const text3Y = useTransform(progress, [0.585, 0.625], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* 1. Forgotten Text */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{
          opacity: text1Opacity,
          y: text1Y,
        }}
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-300 leading-snug">
          Most conversations <br />
          <span className="font-semibold text-slate-400">are forgotten.</span>
        </h2>
      </motion.div>

      {/* 2. Remembers Text */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{
          opacity: text2Opacity,
          y: text2Y,
        }}
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-300 leading-snug">
          Esona remembers <br />
          <span className="font-semibold text-cyan-300" style={{ textShadow: '0 0 10px rgba(34,211,238,0.2)' }}>
            what matters.
          </span>
        </h2>
      </motion.div>

      {/* 3. Memory fragments fading in around */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {MEMORY_FRAGMENTS.map((frag, idx) => (
          <motion.div
            key={idx}
            className="absolute px-4 py-2 rounded-xl border border-white/5 text-xs sm:text-sm font-light text-slate-300"
            style={{
              left: frag.x,
              top: frag.y,
              opacity: getFragOpacity(idx),
              y: fragY,
              background: 'rgba(10, 15, 40, 0.4)',
              backdropFilter: 'blur(4px)',
              boxShadow: '0 4px 15px rgba(0,0,0,0.3)',
              fontFamily: 'var(--font-space-grotesk), sans-serif',
            }}
          >
            {frag.text}
          </motion.div>
        ))}
      </div>

      {/* 4. Not every word... */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto flex flex-col gap-3"
        style={{
          opacity: text3Opacity,
          y: text3Y,
        }}
      >
        <span className="text-xs uppercase tracking-[0.25em] text-[#8B9BB8] font-semibold">
          Not every word.
        </span>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-300 leading-snug">
          The things that <br />
          make you, <span className="font-semibold text-white">you.</span>
        </h2>
      </motion.div>
    </motion.div>
  );
}
