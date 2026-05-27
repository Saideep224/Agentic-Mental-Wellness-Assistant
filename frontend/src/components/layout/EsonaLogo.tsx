'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { cn } from '@/utils';

interface EsonaLogoProps {
  size?: number;
  className?: string;
  showParticles?: boolean;
  glowIntensity?: 'none' | 'low' | 'medium' | 'high';
  enableHoverEffect?: boolean;
  animateIntro?: boolean;
  aiState?: 'idle' | 'listening' | 'speaking';
}

// Pre-defined static particles to prevent hydration mismatch
const PARTICLE_TEMPLATES = [
  { left: '15%', delay: 0.2, duration: 6, scale: 0.6, tx: -15 },
  { left: '28%', delay: 1.5, duration: 7, scale: 0.8, tx: 20 },
  { left: '42%', delay: 0.8, duration: 5, scale: 0.5, tx: -10 },
  { left: '55%', delay: 2.2, duration: 8, scale: 0.9, tx: 25 },
  { left: '68%', delay: 0.5, duration: 6.5, scale: 0.7, tx: -20 },
  { left: '80%', delay: 1.9, duration: 7.5, scale: 0.6, tx: 15 },
  { left: '22%', delay: 3.0, duration: 5.5, scale: 0.7, tx: 10 },
  { left: '62%', delay: 3.5, duration: 6.8, scale: 0.8, tx: -15 },
];

export default function EsonaLogo({
  size = 40,
  className,
  showParticles = false,
  glowIntensity = 'medium',
  enableHoverEffect = true,
  animateIntro = true,
  aiState = 'idle',
}: EsonaLogoProps) {
  const [mounted, setMounted] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Motion values for 3D tilt hover effect
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  // Smooth springs for interpolation
  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [15, -15]), { stiffness: 150, damping: 20 });
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-15, 15]), { stiffness: 150, damping: 20 });

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!enableHoverEffect || !cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = event.clientX - rect.left - width / 2;
    const mouseY = event.clientY - rect.top - height / 2;
    x.set(mouseX / width);
    y.set(mouseY / height);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    x.set(0);
    y.set(0);
  };

  // Determine glow intensity styles
  const glowStyles = {
    none: '',
    low: 'bg-sky-400/10 blur-md opacity-40',
    medium: 'bg-gradient-to-tr from-sky-400/20 via-cyan-400/25 to-blue-500/15 blur-xl opacity-75',
    high: 'bg-gradient-to-tr from-sky-400/35 via-cyan-400/40 to-indigo-500/25 blur-2xl opacity-100',
  }[glowIntensity];

  // Aspect ratio of the cropped logo is roughly 1:1.32 (1516w x 2000h)
  const height = size * 1.32;

  // Twinkle/Sparkle animation for the top diamond star
  const sparkleVariants = {
    animate: {
      scale: [1, 1.4, 0.8, 1.4, 1],
      opacity: [0.8, 1, 0.6, 1, 0.8],
      rotate: [0, 45, 90, 135, 180],
      transition: {
        duration: 5,
        ease: 'easeInOut' as const,
        repeat: Infinity,
      },
    },
    hover: {
      scale: [1, 1.7, 0.9, 1.7, 1],
      opacity: [0.9, 1, 0.7, 1, 0.9],
      rotate: [0, 90, 180, 270, 360],
      transition: {
        duration: 3,
        ease: 'easeInOut' as const,
        repeat: Infinity,
      },
    },
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      className={cn('relative flex items-center justify-center select-none', className)}
      style={{
        width: `${size}px`,
        height: `${height}px`,
        perspective: 800,
      }}
    >
      {/* 1. Ambient Background Aura (Anime Energy) */}
      {glowIntensity !== 'none' && (
        <motion.div
          className={cn('absolute rounded-full pointer-events-none', glowStyles)}
          style={{
            width: `${size * 1.6}px`,
            height: `${size * 1.6}px`,
            left: `-${size * 0.3}px`,
            top: `-${size * 0.15}px`,
          }}
          animate={{
            scale: aiState === 'speaking' ? [1, 1.15, 1] : isHovered ? 1.25 : [1, 1.08, 0.98, 1.05, 1],
            opacity: aiState === 'speaking' ? [0.6, 1, 0.6] : isHovered ? 0.95 : [0.7, 0.85, 0.65, 0.8, 0.7],
            boxShadow: aiState === 'speaking' ? ['0 0 10px rgba(56,189,248,0.3)', '0 0 35px rgba(56,189,248,0.8)', '0 0 10px rgba(56,189,248,0.3)'] : 'none',
          }}
          transition={{
            scale: aiState === 'speaking' ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : isHovered ? { duration: 0.3 } : { duration: 6, repeat: Infinity, ease: 'easeInOut' },
            opacity: aiState === 'speaking' ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : isHovered ? { duration: 0.3 } : { duration: 6, repeat: Infinity, ease: 'easeInOut' },
            boxShadow: aiState === 'speaking' ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 },
          }}
        />
      )}

      {/* 2. Magical Floating Particles (Anime Spirit Orbs) */}
      {mounted && showParticles && (
        <div className="absolute inset-0 overflow-visible pointer-events-none">
          {PARTICLE_TEMPLATES.map((particle, idx) => (
            <motion.div
              key={idx}
              className="absolute rounded-full bg-cyan-300"
              style={{
                left: particle.left,
                bottom: '10%',
                width: `${4 * particle.scale}px`,
                height: `${4 * particle.scale}px`,
                filter: `drop-shadow(0 0 4px rgba(56, 189, 248, 0.8))`,
              }}
              initial={{ y: 0, x: 0, opacity: 0 }}
              animate={{
                y: -height * 1.1,
                x: [0, particle.tx / 2, particle.tx, particle.tx / 2, 0],
                opacity: [0, 0.7, 0.8, 0.3, 0],
              }}
              transition={{
                duration: isHovered ? particle.duration * 0.7 : particle.duration,
                repeat: Infinity,
                delay: particle.delay,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      )}

      {/* 3. Main Logo Container (With 3D Tilt support) */}
      <motion.div
        className="w-full h-full relative cursor-pointer"
        style={{
          rotateX: enableHoverEffect ? rotateX : 0,
          rotateY: enableHoverEffect ? rotateY : 0,
          transformStyle: 'preserve-3d',
        }}
        initial={animateIntro ? { scale: 0.75, opacity: 0 } : false}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 120, damping: 14, delay: 0.1 }}
      >
        {/* Logo Image */}
        <motion.img
          src="/logo.png"
          alt="Esona"
          className="w-full h-full object-contain logo-premium logo-anime-glow"
          style={{ transform: 'translateZ(10px)' }}
          animate={isHovered ? { scale: 1.05 } : { scale: 1 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />

        {/* 4. Shine Sweep Shimmer (Periodic + Hover trigger) */}
        <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none" style={{ transform: 'translateZ(15px)' }}>
          <div
            className={cn(
              'shimmer-sweep-overlay',
              isHovered ? 'animate-shimmer-sweep' : 'animate-shimmer-sweep'
            )}
            style={{
              animationDuration: isHovered ? '1.8s' : '4.5s',
            }}
          />
        </div>

        {/* 5. Ethereal Vector Twinkling Star (At the top of the logo) */}
        <motion.div
          className="absolute -translate-x-1/2 -translate-y-1/2 flex items-center justify-center"
          style={{
            left: '50.1%',
            top: '4.8%',
            width: `${size * 0.16}px`,
            height: `${size * 0.16}px`,
            transform: 'translateZ(20px)',
          }}
          variants={sparkleVariants}
          animate={isHovered ? 'hover' : 'animate'}
        >
          {/* Star Core Glow */}
          <div className="absolute w-full h-full bg-cyan-300 rounded-full blur-[2px] opacity-70 animate-pulse" />
          
          {/* Vector 4-pointed Star */}
          <svg
            viewBox="0 0 24 24"
            fill="none"
            className="w-full h-full text-white"
            style={{ filter: 'drop-shadow(0 0 3px rgba(56, 189, 248, 1))' }}
          >
            <path
              d="M12,2 L14.5,9.5 L22,12 L14.5,14.5 L12,22 L9.5,14.5 L2,12 L9.5,9.5 Z"
              fill="currentColor"
            />
          </svg>
        </motion.div>
      </motion.div>
    </div>
  );
}
