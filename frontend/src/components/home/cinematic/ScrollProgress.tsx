'use client';

import { motion, MotionValue, useTransform } from 'framer-motion';

interface Props {
  scrollYProgress: MotionValue<number>;
  activeScene: number;
}

const SCENE_NAMES = [
  "Esona",
  "Silent thoughts",
  "The message",
  "Listening deeper",
  "Human memory",
  "Connected worlds",
  "Personalized care",
  "Just talk"
];

export default function ScrollProgress({ scrollYProgress, activeScene }: Props) {
  // Transform scroll progress to a percentage height for the active track
  const progressHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  const handleDotClick = (index: number) => {
    if (typeof window === 'undefined') return;
    
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const targetScroll = docHeight * (index / (SCENE_NAMES.length - 1));
    
    window.scrollTo({
      top: targetScroll,
      behavior: 'smooth'
    });
  };

  return (
    <div className="fixed right-8 top-1/2 -translate-y-1/2 z-50 hidden md:flex items-center gap-4 select-none">
      {/* Active Scene Label */}
      <div className="text-right">
        <motion.div
          key={activeScene}
          initial={{ opacity: 0, x: 5 }}
          animate={{ opacity: 0.6, x: 0 }}
          className="text-xs uppercase tracking-[0.2em] font-semibold text-[#8B9BB8]"
          style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}
        >
          {SCENE_NAMES[activeScene]}
        </motion.div>
        <div className="text-[10px] text-[#8B9BB8]/40 mt-1">
          Scene 0{activeScene + 1} / 0{SCENE_NAMES.length}
        </div>
      </div>

      {/* Progress Dots Container */}
      <div className="relative flex flex-col items-center gap-3">
        {/* Continuous Track Line */}
        <div className="absolute top-1 bottom-1 w-[1px] bg-white/10">
          <motion.div
            className="absolute top-0 w-full bg-cyan-400"
            style={{ height: progressHeight }}
          />
        </div>

        {/* Scene Indicator Dots */}
        {SCENE_NAMES.map((name, i) => {
          const isActive = i === activeScene;
          return (
            <button
              key={name}
              onClick={() => handleDotClick(i)}
              className="group relative w-3 h-3 flex items-center justify-center focus:outline-none"
              aria-label={`Jump to Scene ${i + 1}: ${name}`}
            >
              {/* Dot */}
              <motion.div
                className={`rounded-full transition-all duration-300 ${
                  isActive 
                    ? "bg-cyan-400 w-2.5 h-2.5 shadow-[0_0_8px_rgba(34,211,238,0.5)]" 
                    : "bg-white/20 w-1.5 h-1.5 group-hover:bg-cyan-400/50"
                }`}
              />

              {/* Tooltip */}
              <div className="absolute right-6 top-1/2 -translate-y-1/2 opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-200 bg-[#080d20]/90 border border-white/5 text-[10px] uppercase tracking-wider text-white py-1 px-2.5 rounded whitespace-nowrap shadow-xl">
                {name}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
