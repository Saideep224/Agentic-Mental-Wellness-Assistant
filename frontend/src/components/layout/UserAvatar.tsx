'use client';

import { motion } from 'framer-motion';
import { User as UserIcon } from 'lucide-react';
import { cn } from '@/utils';

interface UserAvatarProps {
  avatarUrl?: string | null;
  name?: string | null;
  size?: number; // size in pixels
  glow?: boolean;
  className?: string;
  enableHover?: boolean;
}

export default function UserAvatar({
  avatarUrl,
  name,
  size = 32,
  glow = true,
  className,
  enableHover = true,
}: UserAvatarProps) {
  const firstLetter = name?.trim() ? name.trim().charAt(0).toUpperCase() : '?';

  // Return a calming gradient color determined by the first character of their name
  const getCalmingGradient = (char: string) => {
    const code = char.charCodeAt(0) || 0;
    const remainder = code % 4;
    
    if (remainder === 0) {
      return 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)'; // Deep Sky Blue
    } else if (remainder === 1) {
      return 'linear-gradient(135deg, #7c3aed 0%, #db2777 100%)'; // Calm Lavender-Violet to Pink
    } else if (remainder === 2) {
      return 'linear-gradient(135deg, #0d9488 0%, #0f766e 100%)'; // Ethereal Teal
    } else {
      return 'linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)'; // Peaceful Indigo
    }
  };

  const containerStyle = {
    width: `${size}px`,
    height: `${size}px`,
  };

  const textStyle = {
    fontSize: `${size * 0.42}px`,
  };

  // Outer glow filter based on size
  const glowShadow = glow 
    ? {
        boxShadow: `0 0 ${size * 0.25}px rgba(56, 189, 248, 0.22)`,
        borderColor: 'rgba(56, 189, 248, 0.25)',
      }
    : {};

  const hoverGlow = glow && enableHover
    ? {
        boxShadow: `0 0 ${size * 0.4}px rgba(56, 189, 248, 0.45)`,
        borderColor: 'rgba(56, 189, 248, 0.45)',
      }
    : {};

  return (
    <motion.div
      whileHover={enableHover ? { scale: 1.04, ...hoverGlow } : {}}
      whileTap={enableHover ? { scale: 0.96 } : {}}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn(
        'rounded-full overflow-hidden flex items-center justify-center border shrink-0 bg-slate-950 transition-all duration-300',
        className
      )}
      style={{
        ...containerStyle,
        ...glowShadow,
        borderColor: glow ? 'rgba(56, 189, 248, 0.15)' : 'var(--glass-border)',
      }}
    >
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt={name || 'User Avatar'}
          referrerPolicy="no-referrer"
          className="w-full h-full object-cover rounded-full"
        />
      ) : (
        <div
          className="w-full h-full flex items-center justify-center font-bold text-white uppercase select-none"
          style={{
            background: getCalmingGradient(firstLetter),
            ...textStyle,
            fontFamily: 'var(--font-space-grotesk), sans-serif',
          }}
        >
          {firstLetter === '?' ? (
            <UserIcon size={size * 0.48} className="text-white/80" />
          ) : (
            firstLetter
          )}
        </div>
      )}
    </motion.div>
  );
}
