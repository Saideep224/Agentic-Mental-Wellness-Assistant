'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { getFromStorage, setToStorage } from '@/utils';

export function useAmbientAudio() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.3);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // Check stored preference
    const storedPref = getFromStorage('esona_ambient_audio');
    if (storedPref === 'playing') {
      setIsPlaying(true);
    }

    const storedVolume = getFromStorage('esona_ambient_volume');
    if (storedVolume) {
      setVolume(parseFloat(storedVolume));
    }

    // Create audio element
    // NOTE: Place your ambient audio file at /public/audio/ambient.mp3
    const audio = new Audio('/audio/ambient.mp3');
    audio.loop = true;
    audio.volume = volume;
    audioRef.current = audio;

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = useCallback(() => {
    if (!audioRef.current) return;

    if (isPlaying) {
      // Fade out
      let vol = audioRef.current.volume;
      const fadeOut = setInterval(() => {
        vol = Math.max(0, vol - 0.05);
        if (audioRef.current) audioRef.current.volume = vol;
        if (vol <= 0) {
          clearInterval(fadeOut);
          audioRef.current?.pause();
          if (audioRef.current) audioRef.current.volume = volume;
        }
      }, 50);
      setToStorage('esona_ambient_audio', 'paused');
    } else {
      audioRef.current.volume = 0;
      audioRef.current.play().catch(() => {});
      let vol = 0;
      const fadeIn = setInterval(() => {
        vol = Math.min(volume, vol + 0.05);
        if (audioRef.current) audioRef.current.volume = vol;
        if (vol >= volume) {
          clearInterval(fadeIn);
        }
      }, 50);
      setToStorage('esona_ambient_audio', 'playing');
    }

    setIsPlaying((prev) => !prev);
  }, [isPlaying, volume]);

  const changeVolume = useCallback((newVolume: number) => {
    const clamped = Math.max(0, Math.min(1, newVolume));
    setVolume(clamped);
    if (audioRef.current && isPlaying) {
      audioRef.current.volume = clamped;
    }
    setToStorage('esona_ambient_volume', String(clamped));
  }, [isPlaying]);

  return {
    isPlaying,
    volume,
    toggle,
    changeVolume,
  };
}
