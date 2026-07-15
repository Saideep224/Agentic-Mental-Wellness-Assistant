'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import { FLOATING_THOUGHTS } from './demoData';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function HiddenThoughtsScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();

  // Scene visible range: [0.125, 0.25]
  const opacity = useTransform(progress, [0, 0.08, 0.125, 0.245, 0.255, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  
  // Parallax shifts for floating thoughts based on scroll
  const thoughtY1 = useTransform(progress, [0.125, 0.25], [50, -50], { clamp: true });
  const thoughtY2 = useTransform(progress, [0.125, 0.25], [100, -150], { clamp: true });
  const thoughtY3 = useTransform(progress, [0.125, 0.25], [150, -250], { clamp: true });

  // First statement: "Sometimes... you don't even know what you're feeling"
  // Fades in: 0.125 -> 0.145 | Holds: 0.145 -> 0.18 | Exits: 0.18 -> 0.20
  const text1Opacity = useTransform(progress, [0, 0.125, 0.145, 0.18, 0.20, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const text1Y = useTransform(progress, [0.125, 0.20], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Thoughts dissolve: visible from 0.125 to 0.20, fading out with text1
  const thoughtsOpacity = useTransform(progress, [0, 0.125, 0.145, 0.18, 0.20, 1], [0, 0, 0.8, 0.8, 0, 0], { clamp: true });

  // Second statement: "But your words say more than you think"
  // Fades in: 0.20 -> 0.22 | Holds: 0.22 -> 0.24 | Exits: 0.24 -> 0.25
  const text2Opacity = useTransform(progress, [0, 0.20, 0.22, 0.24, 0.25, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const text2Y = useTransform(progress, [0.20, 0.25], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Helper to map depth to y transform
  const getThoughtY = (depth: number) => {
    if (shouldReduceMotion) return 0;
    if (depth === 1) return thoughtY1;
    if (depth === 2) return thoughtY2;
    return thoughtY3;
  };

  // Helper to map depth to styling
  const getThoughtStyle = (depth: number) => {
    if (depth === 1) return { fontSize: '1rem', filter: 'blur(0px)', opacity: 0.65 };
    if (depth === 2) return { fontSize: '1.25rem', filter: 'blur(1px)', opacity: 0.45 };
    return { fontSize: '1.5rem', filter: 'blur(2.5px)', opacity: 0.25 };
  };

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* 3D Parallax Floating Thoughts */}
      <motion.div 
        className="absolute inset-0 overflow-hidden"
        style={{ opacity: thoughtsOpacity }}
      >
        {FLOATING_THOUGHTS.map((t, idx) => (
          <motion.div
            key={idx}
            className="absolute font-light text-[#A9C7FA] whitespace-nowrap"
            style={{
              left: t.x,
              top: t.y,
              y: getThoughtY(t.depth),
              ...getThoughtStyle(t.depth),
              fontFamily: 'var(--font-space-grotesk), sans-serif',
            }}
          >
            "{t.text}"
          </motion.div>
        ))}
      </motion.div>

      {/* Narrative Text 1 */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto flex flex-col gap-4"
        style={{
          opacity: text1Opacity,
          y: text1Y,
        }}
      >
        <span className="text-sm tracking-[0.2em] font-medium text-cyan-400 uppercase">
          Sometimes...
        </span>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-200 leading-snug">
          you don't even know <br />
          <span className="font-semibold text-white">what you're feeling.</span>
        </h2>
      </motion.div>

      {/* Narrative Text 2 */}
      <motion.div
        className="absolute text-center max-w-2xl mx-auto flex flex-col gap-4"
        style={{
          opacity: text2Opacity,
          y: text2Y,
        }}
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-200 leading-snug">
          But your <span className="font-semibold text-cyan-300">words</span> <br />
          say more than you think.
        </h2>
      </motion.div>
    </motion.div>
  );
}
