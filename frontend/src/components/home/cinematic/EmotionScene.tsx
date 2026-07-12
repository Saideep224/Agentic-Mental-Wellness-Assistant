'use client';

import { motion, MotionValue, useTransform, useReducedMotion } from 'framer-motion';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function EmotionScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();

  // Scene visible range: [0.375, 0.50]
  // Fades in: 0.375 -> 0.395 | Holds: 0.395 -> 0.485 | Exits: 0.485 -> 0.50
  const opacity = useTransform(progress, [0, 0.375, 0.395, 0.485, 0.50, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const y = useTransform(progress, [0.375, 0.50], [20, shouldReduceMotion ? 20 : -20], { clamp: true });

  // Animated bars based on scroll progress (0.395 to 0.45)
  const anxietyWidth = useTransform(progress, [0.395, 0.44], ["0%", "68%"], { clamp: true });
  const stressWidth = useTransform(progress, [0.40, 0.445], ["0%", "21%"], { clamp: true });
  const neutralWidth = useTransform(progress, [0.405, 0.45], ["0%", "11%"], { clamp: true });

  // Animated percentages (0.395 to 0.45)
  const anxietyPercent = useTransform(progress, [0.395, 0.44], [0, 68], { clamp: true });
  const stressPercent = useTransform(progress, [0.40, 0.445], [0, 21], { clamp: true });
  const neutralPercent = useTransform(progress, [0.405, 0.45], [0, 11], { clamp: true });

  // Glow intensity for the bars
  const anxietyShadow = useTransform(
    progress,
    [0.44, 0.45],
    ["0 0 0px rgba(251,146,60,0)", "0 0 12px rgba(251,146,60,0.4)"],
    { clamp: true }
  );

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        y,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      <div className="w-full max-w-2xl mx-auto flex flex-col md:flex-row items-center gap-10">
        
        {/* Left Side: Emotional Breakdown Demonstration */}
        <div className="w-full max-w-md flex-shrink-0 flex flex-col gap-6">
          <div className="px-6 py-6 rounded-2xl border border-white/5 bg-[#0a0f28]/60 backdrop-blur-md">
            <h3 className="text-xs uppercase tracking-[0.25em] text-[#8B9BB8] mb-5 font-semibold" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
              Signal Breakdown
            </h3>

            <div className="flex flex-col gap-4">
              {/* Anxiety Bar */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-medium tracking-wide">
                  <span className="text-[#FB923C] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#FB923C]" />
                    Anxiety
                  </span>
                  <motion.span className="text-slate-200">
                    {useTransform(anxietyPercent, (val) => `${Math.round(val)}%`)}
                  </motion.span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-[#FB923C]/50 to-[#FB923C] rounded-full"
                    style={{ width: anxietyWidth, boxShadow: anxietyShadow }}
                  />
                </div>
              </div>

              {/* Stress Bar */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-medium tracking-wide">
                  <span className="text-[#F59E0B] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#F59E0B]" />
                    Stress
                  </span>
                  <motion.span className="text-slate-200">
                    {useTransform(stressPercent, (val) => `${Math.round(val)}%`)}
                  </motion.span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-[#F59E0B]/50 to-[#F59E0B] rounded-full"
                    style={{ width: stressWidth }}
                  />
                </div>
              </div>

              {/* Neutral Bar */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-medium tracking-wide">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-slate-500" />
                    Neutral
                  </span>
                  <motion.span className="text-slate-400">
                    {useTransform(neutralPercent, (val) => `${Math.round(val)}%`)}
                  </motion.span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-slate-500 rounded-full"
                    style={{ width: neutralWidth }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Narrative and Technical Summary */}
        <div className="flex flex-col gap-5 text-center md:text-left max-w-sm">
          <span className="text-xs font-semibold tracking-[0.25em] text-cyan-400 uppercase" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
            Scene 04 / Context
          </span>
          <h2 className="text-3xl sm:text-4xl font-light text-slate-100 leading-snug">
            Esona listens <br />
            <span className="font-semibold text-white">beyond the words.</span>
          </h2>
          <p className="text-xs sm:text-sm text-[#8BA0B8] leading-relaxed border-l-2 border-cyan-400/20 pl-4 py-1">
            Hybrid emotion understanding powered by contextual analysis.
          </p>
        </div>

      </div>
    </motion.div>
  );
}
