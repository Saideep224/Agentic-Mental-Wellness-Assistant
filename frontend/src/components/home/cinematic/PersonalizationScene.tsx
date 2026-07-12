'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';
import { PERSONALIZATION_PREFS } from './demoData';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function PersonalizationScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();

  // Scene visible range: [0.75, 0.875]
  const opacity = useTransform(progress, [0, 0.75, 0.765, 0.865, 0.875, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const y = useTransform(progress, [0.75, 0.875], [20, shouldReduceMotion ? 20 : -20], { clamp: true });

  // Phase 1: "Because everyone needs to be heard differently." (0.75 to 0.795)
  // Fades in: 0.75 -> 0.765 | Holds: 0.765 -> 0.785 | Exits: 0.785 -> 0.795
  const text1Opacity = useTransform(progress, [0, 0.75, 0.765, 0.785, 0.795, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 2: Sequential quotes (0.795 to 0.865)
  // Quote 1: 0.795 -> 0.80 | Holds: 0.80 -> 0.812 | Exits: 0.812 -> 0.815
  const quote1Opacity = useTransform(progress, [0, 0.795, 0.80, 0.812, 0.815, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  // Quote 2: 0.815 -> 0.82 | Holds: 0.82 -> 0.827 | Exits: 0.827 -> 0.83
  const quote2Opacity = useTransform(progress, [0, 0.815, 0.82, 0.827, 0.83, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  // Quote 3: 0.83 -> 0.835 | Holds: 0.835 -> 0.842 | Exits: 0.842 -> 0.845
  const quote3Opacity = useTransform(progress, [0, 0.83, 0.835, 0.842, 0.845, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  // Quote 4: 0.845 -> 0.85 | Holds: 0.85 -> 0.86 | Exits: 0.86 -> 0.865
  const quote4Opacity = useTransform(progress, [0, 0.845, 0.85, 0.86, 0.865, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 3: Response adaptation panels (0.855 to 0.875)
  // Fades in: 0.855 -> 0.865 | Holds: 0.865 -> 0.872 | Exits: 0.872 -> 0.875
  const adaptationOpacity = useTransform(progress, [0, 0.855, 0.865, 0.872, 0.875, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  
  // Slide inputs
  const prefPanelX = useTransform(progress, [0.855, 0.865], [-30, 0], { clamp: true });
  const replyPanelX = useTransform(progress, [0.855, 0.865], [30, 0], { clamp: true });

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        y,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* 1. Introductory Statement */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{ opacity: text1Opacity }}
      >
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-light text-slate-300 leading-snug">
          Because everyone <br />
          <span className="font-semibold text-white">needs to be heard differently.</span>
        </h2>
      </motion.div>

      {/* 2. Sequential Quotes */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {/* Quote 1 */}
        <motion.p
          className="absolute text-xl sm:text-2xl font-light text-[#86D2F9] italic"
          style={{ opacity: quote1Opacity, fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          "Some need advice."
        </motion.p>
        
        {/* Quote 2 */}
        <motion.p
          className="absolute text-xl sm:text-2xl font-light text-[#A8BDD6] italic"
          style={{ opacity: quote2Opacity, fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          "Some need silence."
        </motion.p>

        {/* Quote 3 */}
        <motion.p
          className="absolute text-xl sm:text-2xl font-light text-[#FB923C] italic"
          style={{ opacity: quote3Opacity, fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          "Some need honesty."
        </motion.p>

        {/* Quote 4 */}
        <motion.p
          className="absolute text-xl sm:text-2xl md:text-3xl font-medium text-white italic"
          style={{ opacity: quote4Opacity, fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          "Some just need someone to stay."
        </motion.p>
      </div>

      {/* 3. Adaptation Panel Display */}
      <motion.div
        className="w-full max-w-3xl flex flex-col items-center gap-6"
        style={{ opacity: adaptationOpacity }}
      >
        <h2 className="text-2xl sm:text-3xl font-light text-center text-slate-100">
          Esona learns <span className="font-semibold text-white">how to be there for you.</span>
        </h2>

        <div className="w-full flex flex-col md:flex-row gap-6 mt-4">
          {/* Left panel: Preferences */}
          <motion.div
            className="flex-1 px-6 py-6 rounded-2xl border border-white/5 bg-[#0a0f28]/40 backdrop-blur-sm"
            style={{ x: shouldReduceMotion ? 0 : prefPanelX }}
          >
            <h3 className="text-xs uppercase tracking-[0.25em] text-[#8B9BB8] mb-4 font-semibold" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
              User Preference Profile
            </h3>
            <div className="flex flex-wrap gap-2">
              {PERSONALIZATION_PREFS.map((pref, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 rounded-lg border border-cyan-400/20 text-xs font-light text-cyan-300"
                  style={{
                    background: 'rgba(34, 211, 238, 0.05)',
                    fontFamily: 'var(--font-space-grotesk), sans-serif',
                  }}
                >
                  {pref}
                </span>
              ))}
            </div>
            <p className="text-[10px] text-slate-500 mt-4 leading-relaxed">
              *Response styling preferences automatically updated in memory context.
            </p>
          </motion.div>

          {/* Right panel: Reply */}
          <motion.div
            className="flex-1 px-6 py-6 rounded-2xl border border-[#86D2F9]/10 bg-[#0c1935]/40 backdrop-blur-sm flex flex-col justify-between"
            style={{ x: shouldReduceMotion ? 0 : replyPanelX }}
          >
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-full bg-[#86D2F9]/20 border border-[#86D2F9]/40 flex items-center justify-center text-[10px] text-[#86D2F9] font-bold">
                  E
                </div>
                <span className="text-xs font-semibold tracking-wider text-[#86D2F9] uppercase">
                  Esona
                </span>
              </div>
              <p className="text-sm sm:text-base font-light text-slate-200 leading-relaxed italic">
                "yeah... we don't have to fix anything rn. <br />
                you can just stay here and talk to me."
              </p>
            </div>
            <div className="text-[10px] text-slate-500 mt-6">
              Style: Casual & Supportive • Gentle Tone
            </div>
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}
