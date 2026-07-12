'use client';

import { useState, useEffect } from 'react';
import { motion, MotionValue, useTransform, useMotionValueEvent, useReducedMotion } from 'framer-motion';

interface Props {
  progress: MotionValue<number>;
  isActive: boolean;
}

export default function ListeningScene({ progress, isActive }: Props) {
  const shouldReduceMotion = useReducedMotion();
  const messageText = "I don't know... I just can't sleep lately.";
  const [typedText, setTypedText] = useState("");

  // Scene visible range: [0.25, 0.38]
  const opacity = useTransform(progress, [0, 0.24, 0.26, 0.37, 0.39, 1], [0, 0, 1, 1, 0, 0], { clamp: true });

  // Phase 1: "YOU TALK." (0.25 to 0.295)
  // Fades in: 0.25 -> 0.265 | Holds: 0.265 -> 0.285 | Exits: 0.285 -> 0.295
  const talkOpacity = useTransform(progress, [0, 0.25, 0.265, 0.285, 0.295, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const talkY = useTransform(progress, [0.25, 0.295], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Phase 2: "ESONA LISTENS." (0.295 to 0.33)
  // Fades in: 0.295 -> 0.305 | Holds: 0.305 -> 0.32 | Exits: 0.32 -> 0.33
  const listensOpacity = useTransform(progress, [0, 0.295, 0.305, 0.32, 0.33, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const listensY = useTransform(progress, [0.295, 0.33], [15, shouldReduceMotion ? 15 : -15], { clamp: true });

  // Phase 3 & 4: Chat Bubble and Typing (0.33 to 0.375)
  // Fades in: 0.33 -> 0.34 | Holds: 0.34 -> 0.37 | Exits: 0.37 -> 0.375
  const bubbleOpacity = useTransform(progress, [0, 0.33, 0.34, 0.37, 0.375, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const bubbleY = useTransform(progress, [0.33, 0.375], [30, shouldReduceMotion ? 30 : 0], { clamp: true });

  // Typing scroll link (types slowly from 0.34 to 0.365)
  const typedProgress = useTransform(progress, [0.34, 0.365], [0, messageText.length], { clamp: true });
  
  useMotionValueEvent(typedProgress, "change", (latest) => {
    const charIndex = Math.min(messageText.length, Math.max(0, Math.floor(latest)));
    setTypedText(messageText.slice(0, charIndex));
  });

  // Phase 4: Underline highlights (glow starts after typing ends: 0.363 to 0.375)
  const highlight1Color = useTransform(progress, [0.363, 0.369], ["rgba(255,255,255,0.9)", "rgba(56,189,248,1)"], { clamp: true }); // don't know
  const highlight2Color = useTransform(progress, [0.366, 0.372], ["rgba(255,255,255,0.9)", "rgba(251,146,60,1)"], { clamp: true }); // can't sleep
  const highlight3Color = useTransform(progress, [0.369, 0.375], ["rgba(255,255,255,0.9)", "rgba(167,139,250,1)"], { clamp: true }); // lately

  // Phase 5: "There is emotion beneath every sentence." (0.355 to 0.375)
  const footerOpacity = useTransform(progress, [0, 0.355, 0.365, 0.372, 0.375, 1], [0, 0, 1, 1, 0, 0], { clamp: true });
  const footerY = useTransform(progress, [0.355, 0.375], [15, shouldReduceMotion ? 15 : 0], { clamp: true });

  return (
    <motion.div
      className="absolute inset-0 flex flex-col items-center justify-center px-6 select-none z-10"
      style={{
        opacity,
        pointerEvents: isActive ? 'auto' : 'none',
      }}
    >
      {/* 1. YOU TALK */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{
          opacity: talkOpacity,
          y: talkY,
        }}
      >
        <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[0.25em] text-[#C2DBFF]" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
          YOU TALK.
        </h2>
      </motion.div>

      {/* 2. ESONA LISTENS */}
      <motion.div
        className="absolute text-center max-w-xl mx-auto"
        style={{
          opacity: listensOpacity,
          y: listensY,
        }}
      >
        <h2 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-[0.25em] text-cyan-400" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif', textShadow: '0 0 15px rgba(34,211,238,0.3)' }}>
          ESONA LISTENS.
        </h2>
      </motion.div>

      {/* 3. Cinematic Chat Message Bubble */}
      <motion.div
        className="absolute flex flex-col items-center justify-center w-full max-w-lg"
        style={{
          opacity: bubbleOpacity,
          y: bubbleY,
        }}
      >
        {/* User avatar and card */}
        <div className="w-full px-6 py-6 rounded-2xl border border-white/10"
             style={{
               background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.05) 0%, rgba(59, 130, 246, 0.02) 100%)',
               backdropFilter: 'blur(8px)',
               boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
             }}
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-cyan-400/20 border border-cyan-400/40 flex items-center justify-center text-[10px] text-cyan-300 font-bold">
              U
            </div>
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
              You
            </span>
          </div>

          <div className="text-lg sm:text-xl font-light text-slate-100 leading-relaxed min-h-[50px]">
            {/* Render the typed text with reactive color highlights */}
            {typedText.split(" ").map((word, wordIdx) => {
              // Word level matching for highlighting
              const cleanWord = word.replace(/[^a-zA-Z']/g, "").toLowerCase();
              
              if (cleanWord === "know" && wordIdx <= 2) {
                // "don't know" - highlight 1
                return (
                  <motion.span key={wordIdx} className="underline decoration-cyan-400/30 decoration-2 underline-offset-4" style={{ color: highlight1Color }}>
                    {word}{" "}
                  </motion.span>
                );
              } else if (cleanWord === "sleep" || cleanWord === "sleep.") {
                // "can't sleep" - highlight 2
                return (
                  <motion.span key={wordIdx} className="underline decoration-orange-400/30 decoration-2 underline-offset-4 font-normal" style={{ color: highlight2Color }}>
                    {word}{" "}
                  </motion.span>
                );
              } else if (cleanWord === "lately" || cleanWord === "lately.") {
                // "lately" - highlight 3
                return (
                  <motion.span key={wordIdx} className="underline decoration-purple-400/30 decoration-2 underline-offset-4 font-normal" style={{ color: highlight3Color }}>
                    {word}{" "}
                  </motion.span>
                );
              }
              // Normal words
              return <span key={wordIdx}>{word} </span>;
            })}
          </div>
        </div>

        {/* 5. Bottom description */}
        <motion.div
          className="mt-8 text-center"
          style={{
            opacity: footerOpacity,
            y: footerY,
          }}
        >
          <p className="text-sm sm:text-base font-light text-[#8BA0B8] tracking-wide">
            There is <span className="font-semibold text-cyan-300">emotion</span> beneath every sentence.
          </p>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
