'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Volume2, VolumeX } from 'lucide-react';

export default function AmbientAudioToggle() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Create audio element
    // NOTE: Add your ambient audio file to /public/audio/ambient.mp3
    const audio = new Audio('/audio/ambient.mp3');
    audio.loop = true;
    audio.volume = 0.3;
    audioRef.current = audio;

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const toggleAudio = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      // Fade out
      const fadeOut = setInterval(() => {
        if (audioRef.current && audioRef.current.volume > 0.05) {
          audioRef.current.volume = Math.max(0, audioRef.current.volume - 0.05);
        } else {
          clearInterval(fadeOut);
          audioRef.current?.pause();
          if (audioRef.current) audioRef.current.volume = 0.3;
        }
      }, 50);
    } else {
      audioRef.current.volume = 0;
      audioRef.current.play().catch(() => {
        // Autoplay may be blocked by browser
      });
      // Fade in
      const fadeIn = setInterval(() => {
        if (audioRef.current && audioRef.current.volume < 0.25) {
          audioRef.current.volume = Math.min(0.3, audioRef.current.volume + 0.05);
        } else {
          clearInterval(fadeIn);
        }
      }, 50);
    }

    setIsPlaying(!isPlaying);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="relative">
        <AnimatePresence>
          {showTooltip && (
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 5, scale: 0.95 }}
              className="absolute bottom-full right-0 mb-2 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap glass-card"
              style={{ color: 'var(--text-secondary)' }}
            >
              {isPlaying ? 'Mute ambient sounds' : 'Play ambient sounds'}
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          onClick={toggleAudio}
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          className="w-12 h-12 rounded-full glass-card flex items-center justify-center cursor-pointer transition-all duration-300"
          style={{
            boxShadow: isPlaying ? 'var(--glow-cyan)' : 'none',
            borderColor: isPlaying ? 'rgba(34, 211, 238, 0.3)' : 'var(--glass-border)',
          }}
          aria-label={isPlaying ? 'Mute ambient sounds' : 'Play ambient sounds'}
        >
          {isPlaying ? (
            <Volume2 size={18} style={{ color: 'var(--accent-cyan)' }} />
          ) : (
            <VolumeX size={18} style={{ color: 'var(--text-muted)' }} />
          )}
        </motion.button>
      </div>
    </div>
  );
}
