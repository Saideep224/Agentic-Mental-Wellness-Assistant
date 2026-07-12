'use client';

import { useState, useRef, useEffect } from 'react';
import { useScroll, useSpring, useMotionValueEvent } from 'framer-motion';
import { Volume2, VolumeX } from 'lucide-react';
import AmbientBackground from './AmbientBackground';
import ScrollProgress from './ScrollProgress';
import IntroScene from './IntroScene';
import HiddenThoughtsScene from './HiddenThoughtsScene';
import ListeningScene from './ListeningScene';
import EmotionScene from './EmotionScene';
import MemoryScene from './MemoryScene';
import KnowledgeGraphScene from './KnowledgeGraphScene';
import PersonalizationScene from './PersonalizationScene';
import FinalScene from './FinalScene';
import Link from 'next/link';
import EsonaLogo from '@/components/layout/EsonaLogo';
import { useAuth } from '@/providers/AuthProvider';

export default function CinematicHome() {
  const { isAuthenticated } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeScene, setActiveScene] = useState(0);

  // Track page-level scroll progress
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"]
  });

  // Apply fluid spring physics to scroll progress (simulating scrub: 2.0)
  const smoothProgress = useSpring(scrollYProgress, {
    stiffness: 70,
    damping: 30,
    restDelta: 0.0001
  });

  // Dynamically update the active scene index based on smooth progress
  useMotionValueEvent(smoothProgress, "change", (latest) => {
    const index = Math.min(7, Math.floor(latest * 8));
    setActiveScene(index);
  });

  // Initialize and clean up calm ambient audio
  useEffect(() => {
    const audio = new Audio('/music/calm/morgan-ambient-calm-ambient-dreamscape-529861.mp3');
    audio.loop = true;
    audio.volume = 0.25;
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
      // Fade out audio before pausing
      let vol = audioRef.current.volume;
      const fadeOut = setInterval(() => {
        vol = Math.max(0, vol - 0.05);
        if (audioRef.current) audioRef.current.volume = vol;
        if (vol <= 0) {
          clearInterval(fadeOut);
          audioRef.current?.pause();
          if (audioRef.current) audioRef.current.volume = 0.25;
          setIsPlaying(false);
        }
      }, 50);
    } else {
      audioRef.current.volume = 0;
      audioRef.current.play().catch(() => {});
      let vol = 0;
      const fadeIn = setInterval(() => {
        vol = Math.min(0.25, vol + 0.05);
        if (audioRef.current) audioRef.current.volume = vol;
        if (vol >= 0.25) {
          clearInterval(fadeIn);
        }
      }, 50);
      setIsPlaying(true);
    }
  };

  return (
    <div ref={containerRef} className="relative h-[2000vh] w-full bg-transparent select-none">
      {/* Sticky Viewport frame */}
      <div className="sticky top-0 h-screen w-full overflow-hidden flex items-center justify-center">
        
        {/* Layer 0: Continuous Background Caustics / Fog / Stars */}
        <AmbientBackground activeScene={activeScene} />

        {/* Global Minimalist Header / Navigation Bar (Fixed at top on all slides) */}
        <div className="absolute top-8 left-8 right-8 flex items-center justify-between z-[60] pointer-events-auto">
          <div className="flex items-center gap-2">
            <EsonaLogo size={28} showParticles={false} glowIntensity="low" />
            <span className="text-lg font-semibold tracking-wider text-slate-200" style={{ fontFamily: 'var(--font-space-grotesk), sans-serif' }}>
              Esona
            </span>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/login" className="text-xs uppercase tracking-widest text-[#8B9BB8] hover:text-white transition-colors">
              Login
            </Link>
            <Link href={isAuthenticated ? "/chat" : "/login"} className="text-xs uppercase tracking-widest px-4 py-2 rounded-lg border border-white/10 hover:border-cyan-400/30 text-slate-200 transition-all duration-300">
              Get Started
            </Link>
          </div>
        </div>

        {/* Layer 1: Storytelling Scenes (Absolute Stacked) */}
        <IntroScene progress={smoothProgress} isActive={activeScene === 0} />
        <HiddenThoughtsScene progress={smoothProgress} isActive={activeScene === 1} />
        <ListeningScene progress={smoothProgress} isActive={activeScene === 2} />
        <EmotionScene progress={smoothProgress} isActive={activeScene === 3} />
        <MemoryScene progress={smoothProgress} isActive={activeScene === 4} />
        <KnowledgeGraphScene progress={smoothProgress} isActive={activeScene === 5} />
        <PersonalizationScene progress={smoothProgress} isActive={activeScene === 6} />
        <FinalScene progress={smoothProgress} isActive={activeScene === 7} />

        {/* Layer 2: Interactive Navigation Timeline */}
        <ScrollProgress scrollYProgress={smoothProgress} activeScene={activeScene} />

        {/* Layer 3: Ambient Sound Toggle Button */}
        <button
          onClick={toggleAudio}
          className="fixed bottom-8 left-8 z-50 p-3 rounded-full border border-white/10 bg-[#0a0f28]/60 backdrop-blur-md text-[#8B9BB8] hover:text-white hover:border-cyan-400/20 transition-all duration-300 cursor-pointer shadow-lg"
          aria-label={isPlaying ? "Mute ambient music" : "Play ambient music"}
        >
          {isPlaying ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>

      </div>
    </div>
  );
}
