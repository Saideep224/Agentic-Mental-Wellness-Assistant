'use client';

import { useState, useEffect } from 'react';
import { motion, useReducedMotion, MotionValue, useTransform, useMotionTemplate, useMotionValue } from 'framer-motion';

interface Particle {
  id: number;
  size: number;
  left: string;
  top: string;
  delay: number;
  duration: number;
}

interface AmbientBackgroundProps {
  activeScene: number;
  progress?: MotionValue<number>;
}

const SCENE_CONFIGS: Record<number, {
  bg: string;
  glow: string;
  glowOpacity: number;
  fogOpacity: number;
  particlesCount: number;
  particlesColor: string;
  glowColor: string;
  showRays: boolean;
  raysOpacity: number;
}> = {
  0: {
    bg: 'linear-gradient(to bottom, #02040b 0%, #010205 100%)',
    glow: 'radial-gradient(circle at 50% 0%, rgba(34, 211, 238, 0.04) 0%, transparent 70%)',
    glowOpacity: 0.3,
    fogOpacity: 0.15,
    particlesCount: 25,
    particlesColor: 'rgba(103, 232, 249, 0.8)', // Cyan-300
    glowColor: 'rgba(56, 189, 248, 0.85)',
    showRays: true,
    raysOpacity: 0.15,
  },
  1: {
    bg: 'linear-gradient(to bottom, #010204 0%, #000001 100%)',
    glow: 'radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.01) 0%, transparent 50%)',
    glowOpacity: 0.05,
    fogOpacity: 0.1,
    particlesCount: 50, 
    particlesColor: 'rgba(255, 255, 255, 0.75)', // White
    glowColor: 'rgba(255, 255, 255, 0.6)',
    showRays: false,
    raysOpacity: 0,
  },
  2: {
    bg: 'linear-gradient(to bottom, #010512 0%, #010205 100%)',
    glow: 'radial-gradient(circle at 50% 50%, rgba(34, 211, 238, 0.06) 0%, transparent 70%)',
    glowOpacity: 0.45,
    fogOpacity: 0.2,
    particlesCount: 30,
    particlesColor: 'rgba(103, 232, 249, 0.8)', // Cyan-300
    glowColor: 'rgba(56, 189, 248, 0.85)',
    showRays: true,
    raysOpacity: 0.18,
  },
  3: {
    bg: 'linear-gradient(to bottom, #02071a 0%, #010209 100%)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(34, 211, 238, 0.08) 0%, rgba(123, 140, 255, 0.03) 60%, transparent 100%)',
    glowOpacity: 0.65,
    fogOpacity: 0.25,
    particlesCount: 35,
    particlesColor: 'rgba(103, 232, 249, 0.85)', // Cyan-300
    glowColor: 'rgba(56, 189, 248, 0.9)',
    showRays: true,
    raysOpacity: 0.22,
  },
  4: {
    bg: 'linear-gradient(to bottom, #010410 0%, #000105 100%)',
    glow: 'radial-gradient(circle at 40% 60%, rgba(167, 139, 250, 0.05) 0%, rgba(56, 189, 248, 0.03) 50%, transparent 100%)',
    glowOpacity: 0.5,
    fogOpacity: 0.55, 
    particlesCount: 20,
    particlesColor: 'rgba(196, 181, 253, 0.8)', // Purple-300
    glowColor: 'rgba(167, 139, 250, 0.8)',
    showRays: false,
    raysOpacity: 0,
  },
  5: {
    bg: 'linear-gradient(to bottom, #010103 0%, #000000 100%)',
    glow: 'radial-gradient(circle at 50% 50%, transparent 100%)',
    glowOpacity: 0,
    fogOpacity: 0.05,
    particlesCount: 20, 
    particlesColor: 'rgba(103, 232, 249, 0.75)', // Cyan-300
    glowColor: 'rgba(56, 189, 248, 0.8)',
    showRays: false,
    raysOpacity: 0,
  },
  6: {
    bg: 'linear-gradient(to bottom, #020516 0%, #01020b 100%)',
    glow: 'radial-gradient(circle at 50% 30%, rgba(123, 140, 255, 0.07) 0%, rgba(244, 114, 182, 0.02) 60%, transparent 100%)',
    glowOpacity: 0.55,
    fogOpacity: 0.25,
    particlesCount: 30,
    particlesColor: 'rgba(165, 180, 252, 0.8)', // Indigo-300
    glowColor: 'rgba(129, 140, 248, 0.8)',
    showRays: true,
    raysOpacity: 0.15,
  },
  7: {
    bg: 'linear-gradient(to bottom, #030e2a 0%, #010410 100%)',
    glow: 'radial-gradient(circle at 50% -10%, rgba(56, 189, 248, 0.18) 0%, rgba(34, 211, 238, 0.06) 50%, transparent 100%)',
    glowOpacity: 0.75,
    fogOpacity: 0.15,
    particlesCount: 40,
    particlesColor: 'rgba(103, 232, 249, 0.95)', // Cyan-300
    glowColor: 'rgba(34, 211, 238, 0.9)',
    showRays: true,
    raysOpacity: 0.35, 
  },
};

export default function AmbientBackground({ activeScene, progress }: AmbientBackgroundProps) {
  const shouldReduceMotion = useReducedMotion();
  const fallbackProgress = useMotionValue(0);
  const actualProgress = progress || fallbackProgress;

  // Sunrise Ray Color Interpolation
  const rayColor1 = useTransform(
    actualProgress,
    [0, 0.25, 0.5, 0.75, 1],
    [
      'rgba(94, 215, 232, 0.03)',  // Cool Cyan
      'rgba(142, 197, 232, 0.03)', // Soft Blue
      'rgba(243, 217, 164, 0.04)', // Pale Warm Light
      'rgba(232, 182, 107, 0.05)', // Soft Amber
      'rgba(232, 182, 107, 0.05)'
    ]
  );

  const rayColor2 = useTransform(
    actualProgress,
    [0, 0.25, 0.5, 0.75, 1],
    [
      'rgba(94, 215, 232, 0.06)',  // Cool Cyan
      'rgba(142, 197, 232, 0.06)', // Soft Blue
      'rgba(243, 217, 164, 0.07)', // Pale Warm Light
      'rgba(232, 182, 107, 0.10)', // Soft Amber
      'rgba(232, 182, 107, 0.10)'
    ]
  );

  const raysBackgroundImage = useMotionTemplate`repeating-linear-gradient(75deg, transparent, transparent 50px, ${rayColor1} 70px, ${rayColor2} 90px, transparent 110px, transparent 160px)`;

  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    // Generate particles on client to prevent SSR/hydration mismatch
    // Increase generated count to 60 for beautiful stellar density
    const generated = Array.from({ length: 60 }).map((_, i) => ({
      id: i,
      size: Math.random() * 3.5 + 1.2, // 1.2px to 4.7px size
      left: `${Math.random() * 100}%`,
      top: '105%', // Always start from off-screen bottom
      delay: Math.random() * 16, // Delay spread matching duration to distribute on load
      duration: Math.random() * 10 + 10, // Float time: 10s to 20s
    }));
    setParticles(generated);
  }, []);

  const config = SCENE_CONFIGS[activeScene] || SCENE_CONFIGS[0];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
      {/* CSS-based keyframe animations for ultra-smooth rendering & negative delay support */}
      <style>{`
        @keyframes floatSpaceStars {
          0% {
            transform: translateY(0) scale(0.8);
            opacity: 0;
          }
          10% {
            opacity: 0.85;
          }
          90% {
            opacity: 0.85;
          }
          100% {
            transform: translateY(-112vh) scale(1.1);
            opacity: 0;
          }
        }
      `}</style>

      {/* Background gradient transition */}
      <motion.div
        className="absolute inset-0"
        style={{ background: config.bg }}
        animate={{ background: config.bg }}
        transition={{ duration: 1.2, ease: 'easeInOut' }}
      />

      {/* Volumetric Light Rays (swaying gently) */}
      {config.showRays && !shouldReduceMotion && (
        <motion.div
          className="absolute inset-0 origin-top mix-blend-screen pointer-events-none opacity-20"
          style={{
            backgroundImage: raysBackgroundImage,
            filter: 'blur(10px)',
          }}
          animate={{
            rotate: [-1.5, 1.5, -1.5],
            scaleX: [0.95, 1.05, 0.95],
            opacity: config.raysOpacity,
          }}
          transition={{
            duration: 14,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      {/* Caustic / Glow Overlay Layer */}
      <motion.div 
        className="absolute inset-0 mix-blend-screen transition-all"
        style={{
          background: config.glow,
          filter: 'blur(50px)',
        }}
        animate={{
          opacity: config.glowOpacity,
        }}
        transition={{ duration: 1.2 }}
      />

      {/* Underwater Fog/Misty Layer */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(circle at 50% 50%, transparent 20%, rgba(4, 6, 20, 0.9) 100%)',
        }}
        animate={{
          opacity: config.fogOpacity,
        }}
        transition={{ duration: 1.2 }}
      />

      {/* Floating Space Particles */}
      {!shouldReduceMotion && (
        <div className="absolute inset-0">
          {particles.map((p, idx) => {
            const isVisible = idx < config.particlesCount;
            if (!isVisible) return null;

            return (
              <div
                key={p.id}
                className="absolute rounded-full transition-colors duration-1000"
                style={{
                  width: `${p.size}px`,
                  height: `${p.size}px`,
                  left: p.left,
                  top: '105%',
                  background: config.particlesColor,
                  boxShadow: `0 0 6px ${config.glowColor}, 0 0 12px rgba(56, 189, 248, 0.35)`,
                  animation: `floatSpaceStars ${p.duration}s linear infinite`,
                  animationDelay: `-${p.delay}s`, // Instantly initializes particles distributed in height
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
