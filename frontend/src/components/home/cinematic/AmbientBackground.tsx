'use client';

import { useState, useEffect } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

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
}

const SCENE_CONFIGS: Record<number, {
  bg: string;
  glow: string;
  glowOpacity: number;
  fogOpacity: number;
  particlesCount: number;
  particlesColor: string;
  showRays: boolean;
  raysOpacity: number;
}> = {
  // 0: INTRO - Deep dark underwater, almost black/navy, subtle light rays from top
  0: {
    bg: 'linear-gradient(to bottom, #02040b 0%, #010205 100%)',
    glow: 'radial-gradient(circle at 50% 0%, rgba(34, 211, 238, 0.04) 0%, transparent 70%)',
    glowOpacity: 0.3,
    fogOpacity: 0.15,
    particlesCount: 20,
    particlesColor: 'rgba(34, 211, 238, 0.08)',
    showRays: true,
    raysOpacity: 0.15,
  },
  // 1: THOUGHTS - Almost black / floating particles representing hidden thoughts
  1: {
    bg: 'linear-gradient(to bottom, #010204 0%, #000001 100%)',
    glow: 'radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.01) 0%, transparent 50%)',
    glowOpacity: 0.05,
    fogOpacity: 0.1,
    particlesCount: 48, 
    particlesColor: 'rgba(255, 255, 255, 0.06)',
    showRays: false,
    raysOpacity: 0,
  },
  // 2: LISTENING - Blue light slowly appears
  2: {
    bg: 'linear-gradient(to bottom, #010512 0%, #010205 100%)',
    glow: 'radial-gradient(circle at 50% 50%, rgba(34, 211, 238, 0.06) 0%, transparent 70%)',
    glowOpacity: 0.45,
    fogOpacity: 0.2,
    particlesCount: 24,
    particlesColor: 'rgba(34, 211, 238, 0.08)',
    showRays: true,
    raysOpacity: 0.18,
  },
  // 3: EMOTION - Soft caustics and blue glows appearing
  3: {
    bg: 'linear-gradient(to bottom, #02071a 0%, #010209 100%)',
    glow: 'radial-gradient(circle at 50% 40%, rgba(34, 211, 238, 0.08) 0%, rgba(123, 140, 255, 0.03) 60%, transparent 100%)',
    glowOpacity: 0.65,
    fogOpacity: 0.25,
    particlesCount: 28,
    particlesColor: 'rgba(34, 211, 238, 0.1)',
    showRays: true,
    raysOpacity: 0.22,
  },
  // 4: MEMORY - Fog / blurry lights
  4: {
    bg: 'linear-gradient(to bottom, #010410 0%, #000105 100%)',
    glow: 'radial-gradient(circle at 40% 60%, rgba(167, 139, 250, 0.05) 0%, rgba(56, 189, 248, 0.03) 50%, transparent 100%)',
    glowOpacity: 0.5,
    fogOpacity: 0.55, 
    particlesCount: 15,
    particlesColor: 'rgba(167, 139, 250, 0.06)',
    showRays: false,
    raysOpacity: 0,
  },
  // 5: KG - Pure dark background + glowing graph
  5: {
    bg: 'linear-gradient(to bottom, #010103 0%, #000000 100%)',
    glow: 'radial-gradient(circle at 50% 50%, transparent 100%)',
    glowOpacity: 0,
    fogOpacity: 0.05,
    particlesCount: 0, 
    particlesColor: 'transparent',
    showRays: false,
    raysOpacity: 0,
  },
  // 6: PERSONALITY - Soft blue-purple atmosphere
  6: {
    bg: 'linear-gradient(to bottom, #020516 0%, #01020b 100%)',
    glow: 'radial-gradient(circle at 50% 30%, rgba(123, 140, 255, 0.07) 0%, rgba(244, 114, 182, 0.02) 60%, transparent 100%)',
    glowOpacity: 0.55,
    fogOpacity: 0.25,
    particlesCount: 22,
    particlesColor: 'rgba(123, 140, 255, 0.08)',
    showRays: true,
    raysOpacity: 0.15,
  },
  // 7: FINAL - Rise towards moonlit ocean surface
  7: {
    bg: 'linear-gradient(to bottom, #030e2a 0%, #010410 100%)',
    glow: 'radial-gradient(circle at 50% -10%, rgba(56, 189, 248, 0.18) 0%, rgba(34, 211, 238, 0.06) 50%, transparent 100%)',
    glowOpacity: 0.75,
    fogOpacity: 0.15,
    particlesCount: 32,
    particlesColor: 'rgba(34, 211, 238, 0.12)',
    showRays: true,
    raysOpacity: 0.35, 
  },
};

export default function AmbientBackground({ activeScene }: AmbientBackgroundProps) {
  const shouldReduceMotion = useReducedMotion();
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    // Generate particles on client to prevent SSR/hydration mismatch
    const generated = Array.from({ length: 50 }).map((_, i) => ({
      id: i,
      size: Math.random() * 4 + 1.5, // 1.5px to 5.5px (tiny floating particles)
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 100}%`,
      delay: Math.random() * 5,
      duration: Math.random() * 12 + 8, // 8s to 20s
    }));
    setParticles(generated);
  }, []);

  const config = SCENE_CONFIGS[activeScene] || SCENE_CONFIGS[0];

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden select-none z-0">
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
            backgroundImage: 'repeating-linear-gradient(75deg, transparent, transparent 50px, rgba(34, 211, 238, 0.03) 70px, rgba(34, 211, 238, 0.06) 90px, transparent 110px, transparent 160px)',
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

      {/* Floating Particles */}
      {!shouldReduceMotion && (
        <div className="absolute inset-0">
          {particles.map((p, idx) => {
            const isVisible = idx < config.particlesCount;
            if (!isVisible) return null;

            return (
              <motion.div
                key={p.id}
                className="absolute rounded-full blur-[0.5px]"
                style={{
                  width: p.size,
                  height: p.size,
                  left: p.left,
                  top: p.top,
                  background: config.particlesColor,
                  boxShadow: `0 0 6px ${config.particlesColor}`,
                }}
                animate={{
                  y: [0, -70, 0],
                  x: [0, Math.random() * 24 - 12, 0],
                  opacity: [0.1, 0.45, 0.1],
                }}
                transition={{
                  duration: p.duration,
                  delay: p.delay,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
