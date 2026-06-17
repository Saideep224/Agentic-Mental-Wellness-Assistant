'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface EsonaLoaderProps {
  onComplete?: () => void;
  force?: boolean;
  duration?: number;
}

// 17x8 half-grid representing half of the symmetric pixel-art lantern
const lanternHalfGrid = [
  [0, 0, 0, 0, 0, 0, 1, 1], // Row 0: loop top
  [0, 0, 0, 0, 0, 1, 0, 0], // Row 1: loop side
  [0, 0, 0, 0, 0, 1, 0, 0], // Row 2
  [0, 0, 0, 0, 0, 0, 1, 1], // Row 3
  [0, 0, 1, 1, 1, 1, 1, 1], // Row 4: top cap
  [0, 1, 2, 2, 2, 2, 2, 2], // Row 5: cap highlight
  [1, 1, 1, 1, 1, 1, 1, 1], // Row 6: cap base
  [1, 3, 3, 4, 4, 4, 4, 4], // Row 7: glass top
  [1, 3, 4, 4, 4, 5, 5, 5], // Row 8: glass + flame
  [1, 3, 4, 4, 5, 6, 6, 6], // Row 9: flame mid
  [1, 3, 4, 5, 6, 6, 6, 6], // Row 10: flame core
  [1, 3, 4, 4, 5, 6, 6, 6], // Row 11
  [1, 3, 4, 4, 4, 5, 5, 5], // Row 12
  [1, 3, 3, 4, 4, 4, 4, 4], // Row 13: glass bottom
  [1, 1, 1, 1, 1, 1, 1, 1], // Row 14: base cap
  [0, 0, 1, 1, 2, 2, 2, 2], // Row 15: base stand
  [0, 0, 0, 1, 1, 1, 1, 1]  // Row 16: base bottom
];

// Mirror the half grid to produce a 16x17 symmetric grid
const lanternGrid = lanternHalfGrid.map(row => [...row, ...[...row].reverse()]);

const getPixelColor = (val: number, stage: number) => {
  switch (val) {
    case 1: return '#0B0F19'; // Dark slate metal frame
    case 2: return '#1E293B'; // Metal highlights
    case 3: return '#080C16'; // Glass outline border
    case 4: return 'rgba(125, 211, 252, 0.08)'; // Transparent glass pane
    case 5: // Flame outer glow
      if (stage === 1) return '#0369A1'; // Dark sky blue
      if (stage === 2) return '#06B6D4'; // Vibrant cyan
      return '#7DD3FC'; // Glowing sky-blue (Stage 3)
    case 6: // Flame hot core
      if (stage === 1) return '#0284C7'; // Dim blue
      if (stage === 2) return '#38BDF8'; // Light sky-blue
      return '#FFFFFF'; // Pure white hot core (Stage 3)
    default: return 'transparent';
  }
};

const PixelTree = ({ x, scale, color }: { x: number; scale: number; color: string }) => {
  return (
    <svg
      viewBox="0 0 40 60"
      className="absolute bottom-0 select-none pointer-events-none"
      style={{
        left: `${x}%`,
        width: `${40 * scale}px`,
        height: `${60 * scale}px`,
        shapeRendering: 'crispEdges',
      }}
    >
      <rect x="18" y="48" width="4" height="12" fill={color} />
      <rect x="6" y="40" width="28" height="8" fill={color} />
      <rect x="10" y="32" width="20" height="8" fill={color} />
      <rect x="14" y="24" width="12" height="8" fill={color} />
      <rect x="16" y="14" width="8" height="10" fill={color} />
      <rect x="18" y="6" width="4" height="8" fill={color} />
    </svg>
  );
};

const FAR_TREES = [
  { x: 4, scale: 1.2 }, { x: 14, scale: 0.9 }, { x: 26, scale: 1.1 },
  { x: 38, scale: 1.3 }, { x: 50, scale: 1.0 }, { x: 62, scale: 1.2 },
  { x: 74, scale: 0.9 }, { x: 86, scale: 1.1 }, { x: 95, scale: 1.2 }
];

const MID_TREES = [
  { x: 8, scale: 1.6 }, { x: 20, scale: 1.4 }, { x: 32, scale: 1.7 },
  { x: 46, scale: 1.5 }, { x: 58, scale: 1.8 }, { x: 70, scale: 1.4 },
  { x: 82, scale: 1.6 }, { x: 91, scale: 1.5 }
];

const FRONT_TREES = [
  { x: 1, scale: 2.2 }, { x: 12, scale: 2.0 }, { x: 25, scale: 2.4 },
  { x: 40, scale: 2.1 }, { x: 54, scale: 2.3 }, { x: 66, scale: 2.0 },
  { x: 78, scale: 2.2 }, { x: 88, scale: 2.1 }
];

export default function EsonaLoader({ onComplete, force = false, duration = 4500 }: EsonaLoaderProps) {
  const [mounted, setMounted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState(1);
  const [stars, setStars] = useState<{ x: number; y: number; size: number; delay: number; duration: number }[]>([]);
  const [fireflies, setFireflies] = useState<{ id: number; x: number; delay: number; duration: number; size: number; drift: number }[]>([]);

  useEffect(() => {
    setMounted(true);

    // Initial check for session bypass
    if (!force && typeof window !== 'undefined' && sessionStorage.getItem('esona_loaded') === 'true') {
      if (onComplete) onComplete();
      return;
    }

    // Generate stars
    const generatedStars = Array.from({ length: 35 }).map(() => ({
      x: Math.random() * 100,
      y: Math.random() * 70,
      size: Math.random() > 0.85 ? 3 : 2,
      delay: Math.random() * 5,
      duration: 3 + Math.random() * 4
    }));
    setStars(generatedStars);

    // Generate fireflies
    const generatedFireflies = Array.from({ length: 18 }).map((_, idx) => ({
      id: idx,
      x: 10 + Math.random() * 80,
      delay: Math.random() * 4,
      duration: 6 + Math.random() * 6,
      size: Math.random() > 0.7 ? 4 : 2,
      drift: -40 + Math.random() * 80
    }));
    setFireflies(generatedFireflies);

    // Animation progress logic
    const intervalTime = 30; // 30ms ticks
    const steps = duration / intervalTime;
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      const nextProgress = Math.min(100, (currentStep / steps) * 100);
      setProgress(nextProgress);

      if (nextProgress < 33.3) {
        setStage(1);
      } else if (nextProgress < 66.6) {
        setStage(2);
      } else if (nextProgress < 100) {
        setStage(3);
      } else {
        clearInterval(interval);
        setTimeout(() => {
          if (!force && typeof window !== 'undefined') {
            sessionStorage.setItem('esona_loaded', 'true');
          }
          if (onComplete) onComplete();
        }, 400);
      }
    }, intervalTime);

    return () => clearInterval(interval);
  }, [onComplete, force, duration]);

  if (!mounted) return null;

  const stageTexts = [
    'Loading memories...',
    'Understanding emotions...',
    'Preparing your safe space...'
  ];

  const cellClass = (val: number) => {
    if (stage === 3) {
      if (val === 5) return 'flame-pixel-5';
      if (val === 6) return 'flame-pixel-6';
    }
    return '';
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden select-none"
      style={{
        background: 'radial-gradient(circle at center, #0B0E23 0%, #040614 100%)'
      }}
    >
      {/* CSS keyframe definitions for pixel-art lighting effects */}
      <style>{`
        @keyframes float-up {
          0% {
            transform: translateY(105vh) translateX(0) scale(0.9);
            opacity: 0;
          }
          15% {
            opacity: 0.75;
          }
          85% {
            opacity: 0.75;
          }
          100% {
            transform: translateY(-10vh) translateX(var(--drift)) scale(1.1);
            opacity: 0;
          }
        }
        @keyframes twinkle {
          0%, 100% { opacity: 0.25; }
          50% { opacity: 0.95; }
        }
        @keyframes breathe-lantern {
          0%, 100% { transform: scale(1); filter: drop-shadow(0 0 16px rgba(125, 211, 252, 0.15)); }
          50% { transform: scale(1.025); filter: drop-shadow(0 0 28px rgba(125, 211, 252, 0.4)); }
        }
        @keyframes flame-pulse-5 {
          0%, 100% { background-color: #7DD3FC; }
          50% { background-color: #06B6D4; }
        }
        @keyframes flame-pulse-6 {
          0%, 100% { background-color: #FFFFFF; }
          50% { background-color: #E0F2FE; }
        }
        .flame-pixel-5 {
          animation: flame-pulse-5 1.4s infinite ease-in-out;
        }
        .flame-pixel-6 {
          animation: flame-pulse-6 1.4s infinite ease-in-out;
        }
        .lantern-breathing {
          animation: breathe-lantern 3.2s infinite ease-in-out;
        }
      `}</style>

      {/* 1. Starry Sky */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        {stars.map((star, idx) => (
          <div
            key={idx}
            className="absolute bg-white"
            style={{
              left: `${star.x}%`,
              top: `${star.y}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              animation: `twinkle ${star.duration}s infinite ease-in-out`,
              animationDelay: `${star.delay}s`,
            }}
          />
        ))}
      </div>

      {/* 2. Floating Fireflies (Ambient Particles) */}
      <div className="absolute inset-0 z-10 overflow-hidden pointer-events-none">
        {fireflies.map((fly) => (
          <div
            key={fly.id}
            className="absolute bg-[#7DD3FC] shadow-[0_0_8px_#7DD3FC]"
            style={{
              left: `${fly.x}%`,
              bottom: 0,
              width: `${fly.size}px`,
              height: `${fly.size}px`,
              '--drift': `${fly.drift}px`,
              animation: `float-up ${fly.duration}s infinite linear`,
              animationDelay: `${fly.delay}s`,
            } as React.CSSProperties}
          />
        ))}
      </div>

      {/* 3. Layered Pixel-Art Forest Silhouettes (Parallax Depth) */}
      <div className="absolute inset-x-0 bottom-0 h-40 z-20 pointer-events-none overflow-hidden">
        {/* Far layer */}
        <div className="absolute inset-x-0 bottom-0 h-full opacity-35">
          {FAR_TREES.map((tree, idx) => (
            <PixelTree key={idx} x={tree.x} scale={tree.scale} color="#06091B" />
          ))}
        </div>
        {/* Mid layer */}
        <div className="absolute inset-x-0 bottom-0 h-full opacity-65">
          {MID_TREES.map((tree, idx) => (
            <PixelTree key={idx} x={tree.x} scale={tree.scale} color="#080C25" />
          ))}
        </div>
        {/* Front layer */}
        <div className="absolute inset-x-0 bottom-0 h-full">
          {FRONT_TREES.map((tree, idx) => (
            <PixelTree key={idx} x={tree.x} scale={tree.scale} color="#0A0F2E" />
          ))}
        </div>
      </div>

      {/* 4. Loader Content Center Box */}
      <div className="relative z-30 flex flex-col items-center justify-center">
        {/* Pixel-art Lantern Icon */}
        <div 
          className={`relative p-4 rounded-3xl transition-all duration-1000 ${stage === 3 ? 'lantern-breathing' : ''}`}
          style={{
            background: 'rgba(10, 14, 34, 0.35)',
            border: '1px solid rgba(125, 211, 252, 0.08)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <div
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(16, 7px)',
              gridTemplateRows: 'repeat(17, 7px)',
              gap: '0px',
            }}
          >
            {lanternGrid.flatMap((row, rIdx) =>
              row.map((val, cIdx) => (
                <div
                  key={`${rIdx}-${cIdx}`}
                  className={cellClass(val)}
                  style={{
                    width: '7px',
                    height: '7px',
                    backgroundColor: getPixelColor(val, stage),
                    transition: 'background-color 500ms ease',
                  }}
                />
              ))
            )}
          </div>
        </div>

        {/* Loading Progress Bar */}
        <div className="relative w-64 h-[3px] bg-slate-900/60 border border-white/5 rounded-full overflow-visible mt-8 mb-6">
          <div
            className="h-full rounded-full transition-all duration-100 ease-out"
            style={{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #38BDF8, #7DD3FC)',
              boxShadow: '0 0 12px #7DD3FC, 0 0 20px #38BDF8',
            }}
          />
          {progress > 0 && (
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white transition-all duration-100 ease-out"
              style={{
                left: `calc(${progress}% - 4px)`,
                boxShadow: '0 0 8px #FFFFFF, 0 0 16px #7DD3FC',
              }}
            />
          )}
        </div>

        {/* Dynamic Stage Text Cross-fade */}
        <div className="h-6 flex items-center justify-center overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={stage}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className="text-base font-semibold tracking-wide text-center"
              style={{ color: '#FFFFFF' }}
            >
              {stageTexts[stage - 1]}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Brand Subtitle */}
        <div 
          className="text-[10px] mt-2 font-mono tracking-[0.25em] uppercase opacity-75 font-medium transition-colors duration-500"
          style={{ color: stage === 3 ? '#7DD3FC' : '#AFC7E8' }}
        >
          Esona Wellness
        </div>
      </div>
    </div>
  );
}
