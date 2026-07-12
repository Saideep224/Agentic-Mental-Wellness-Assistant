'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  SkipForward, 
  SkipBack, 
  Volume2, 
  VolumeX, 
  Music, 
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { musicLibrary, Track } from '@/data/musicLibrary';

interface MoodMusicPanelProps {
  latestEmotion?: string;
  className?: string;
}

const MOOD_CONFIG: Record<string, { emoji: string; title: string; color: string; bgGradient: string; textClass: string }> = {
  'happiness': { emoji: '😊', title: 'Happy', color: '#10b981', bgGradient: 'from-emerald-950/40 to-emerald-900/10', textClass: 'text-emerald-400' },
  'excitement': { emoji: '🤩', title: 'Excited', color: '#fbbf24', bgGradient: 'from-amber-950/40 to-amber-900/10', textClass: 'text-amber-400' },
  'sadness': { emoji: '😔', title: 'Sad', color: '#3b82f6', bgGradient: 'from-blue-950/40 to-blue-900/10', textClass: 'text-blue-400' },
  'loneliness': { emoji: '🥺', title: 'Lonely', color: '#6366f1', bgGradient: 'from-indigo-950/40 to-indigo-900/10', textClass: 'text-indigo-400' },
  'anxiety': { emoji: '😰', title: 'Anxious', color: '#a855f7', bgGradient: 'from-purple-950/40 to-purple-900/10', textClass: 'text-purple-400' },
  'fear': { emoji: '😨', title: 'Fearful', color: '#4f46e5', bgGradient: 'from-indigo-950/40 to-indigo-900/10', textClass: 'text-indigo-400' },
  'anger': { emoji: '😤', title: 'Angry', color: '#ef4444', bgGradient: 'from-red-950/40 to-red-900/10', textClass: 'text-red-400' },
  'frustration': { emoji: '😣', title: 'Frustrated', color: '#f97316', bgGradient: 'from-orange-950/40 to-orange-900/10', textClass: 'text-orange-400' },
  'neutral': { emoji: '😌', title: 'Neutral', color: '#06b6d4', bgGradient: 'from-cyan-950/40 to-cyan-900/10', textClass: 'text-cyan-400' },
};

export default function MoodMusicPanel({ latestEmotion = 'Neutral', className = '' }: MoodMusicPanelProps) {
  const [playlist, setPlaylist] = useState<Track[]>([]);
  const [activeTrackIndex, setActiveTrackIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [volume, setVolume] = useState<number>(0.5);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [prevVolume, setPrevVolume] = useState<number>(0.5);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Normalize detected emotion to keys in our MOOD_CONFIG
  const normalizedEmotion = latestEmotion.toLowerCase();
  const config = MOOD_CONFIG[normalizedEmotion] || MOOD_CONFIG['neutral'];

  // Centralized track loader
  const loadTrack = (track: Track, index: number) => {
    if (!track) return;
    
    if (!audioRef.current && typeof window !== 'undefined') {
      audioRef.current = new Audio();
      audioRef.current.volume = isMuted ? 0 : volume;
    }
    
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();

    setActiveTrackIndex(index);

    audio.src = track.src;
    audio.load();
    audio.currentTime = 0;

    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
  };

  // 1. Mood Playlist Progression Logic
  useEffect(() => {
    let selectedTracks: Track[] = [];

    // Sadness: calm first, then happy/uplifting
    if (normalizedEmotion === 'sadness' || normalizedEmotion === 'loneliness') {
      const calmTracks = musicLibrary.filter(t => t.categories.includes('calm'));
      const happyTracks = musicLibrary.filter(t => t.categories.includes('happy'));
      selectedTracks = [...calmTracks.slice(0, 2), ...happyTracks.slice(0, 2)];
    }
    // Anger/Frustration: energetic first to match energy, then calm
    else if (normalizedEmotion === 'anger' || normalizedEmotion === 'frustration') {
      const energeticTracks = musicLibrary.filter(t => t.categories.includes('energetic'));
      const calmTracks = musicLibrary.filter(t => t.categories.includes('calm'));
      selectedTracks = [...energeticTracks.slice(0, 2), ...calmTracks.slice(0, 2)];
    }
    // Anxiety/Fear: grounding first, then calm
    else if (normalizedEmotion === 'anxiety' || normalizedEmotion === 'fear') {
      const groundingTracks = musicLibrary.filter(t => t.categories.includes('grounding'));
      const calmTracks = musicLibrary.filter(t => t.categories.includes('calm'));
      selectedTracks = [...groundingTracks.slice(0, 2), ...calmTracks.slice(0, 2)];
    }
    // Happy/Excitement: happy first, then energetic
    else if (normalizedEmotion === 'happiness' || normalizedEmotion === 'excitement') {
      const happyTracks = musicLibrary.filter(t => t.categories.includes('happy'));
      const energeticTracks = musicLibrary.filter(t => t.categories.includes('energetic'));
      selectedTracks = [...happyTracks.slice(0, 2), ...energeticTracks.slice(0, 2)];
    }
    // Neutral: calm
    else {
      selectedTracks = musicLibrary.filter(t => t.categories.includes('calm'));
    }

    // Fallback if no tracks match
    if (selectedTracks.length === 0) {
      selectedTracks = musicLibrary;
    }

    setPlaylist(selectedTracks);
    
    if (selectedTracks.length > 0) {
      loadTrack(selectedTracks[0], 0);
    }
  }, [latestEmotion]);

  const activeTrack = playlist[activeTrackIndex] || null;

  // 2. Initialize and manage HTMLAudioElement Events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    if (!audioRef.current) {
      audioRef.current = new Audio();
    }

    const audio = audioRef.current;
    audio.volume = isMuted ? 0 : volume;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => setDuration(audio.duration || 0);
    const handleError = () => setIsPlaying(false);
    
    const handleEnded = () => {
      // Auto play next track
      handleNext();
    };

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
    };
  }, [playlist, activeTrackIndex, volume, isMuted]); // Re-attach when handlers capture new state

  // Cleanup audio on component unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  const handlePlayPause = async () => {
    if (!audioRef.current) return;
    const audio = audioRef.current;

    if (isPlaying) {
      audio.pause();
    } else {
      const track = playlist[activeTrackIndex];
      if (track) {
        if (!audio.src || !audio.src.endsWith(track.src)) {
          loadTrack(track, activeTrackIndex);
        }
      }
      try {
        await audio.play();
      } catch (err) {
        setIsPlaying(false);
        console.warn('Playback failed:', err);
      }
    }
  };

  const handleNext = async () => {
    if (playlist.length === 0) return;
    const nextIdx = (activeTrackIndex + 1) % playlist.length;
    const wasPlaying = isPlaying;
    
    loadTrack(playlist[nextIdx], nextIdx);
    
    if (wasPlaying && audioRef.current) {
      try {
        await audioRef.current.play();
      } catch (err) {
        setIsPlaying(false);
        console.warn('Autoplay blocked on next:', err);
      }
    }
  };

  const handlePrev = async () => {
    if (playlist.length === 0) return;
    const prevIdx = (activeTrackIndex - 1 + playlist.length) % playlist.length;
    const wasPlaying = isPlaying;
    
    loadTrack(playlist[prevIdx], prevIdx);
    
    if (wasPlaying && audioRef.current) {
      try {
        await audioRef.current.play();
      } catch (err) {
        setIsPlaying(false);
        console.warn('Autoplay blocked on prev:', err);
      }
    }
  };

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!audioRef.current) return;
    const newTime = parseFloat(e.target.value);
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (isMuted && val > 0) {
      setIsMuted(false);
    }
    if (audioRef.current) {
      audioRef.current.volume = val;
    }
  };

  const toggleMute = () => {
    if (isMuted) {
      setVolume(prevVolume);
      setIsMuted(false);
      if (audioRef.current) audioRef.current.volume = prevVolume;
    } else {
      setPrevVolume(volume);
      setIsMuted(true);
      if (audioRef.current) audioRef.current.volume = 0;
    }
  };

  const formatTime = (time: number) => {
    if (isNaN(time)) return '0:00';
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // Wellness description message helper
  const getWellnessMessage = () => {
    switch (normalizedEmotion) {
      case 'sadness':
      case 'loneliness':
        return "Gentle calm transitioning to warm uplifts to soothe your heart.";
      case 'anger':
      case 'frustration':
        return "Releasing intense energy first, gradually settling into peace.";
      case 'anxiety':
      case 'fear':
        return "Deep grounding rhythms transitioning to pure serene soundscapes.";
      case 'happiness':
      case 'excitement':
        return "Keeping the vibrant positive energy flowing high.";
      default:
        return "Relaxing lo-fi ambient tracks to keep you company.";
    }
  };

  const getEmojiForCategory = (cat: string) => {
    if (cat.includes('happy')) return '✨';
    if (cat.includes('energetic')) return '🔥';
    if (cat.includes('grounding')) return '🌿';
    return '🌊';
  };

  return (
    <div className={`flex flex-col p-4 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-white/10 shadow-2xl text-slate-200 w-80 max-h-[520px] select-none ${className}`}>
      
      {/* 1. Header: Mood Badge & Subtitle */}
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex flex-col">
          <div className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">Current Mood</div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-lg">{config.emoji}</span>
            <span className={`font-bold text-sm ${config.textClass}`}>{config.title}</span>
          </div>
        </div>
        <button 
          onClick={() => {
            // Restart current track or playlist
            if (audioRef.current) {
              audioRef.current.currentTime = 0;
              setCurrentTime(0);
            }
          }}
          className="p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
          title="Restart Track"
        >
          <RotateCcw size={14} />
        </button>
      </div>

      <div className="py-2.5 text-xs text-slate-400 leading-relaxed italic flex items-start gap-1">
        <Sparkles size={12} className="text-yellow-500 flex-shrink-0 mt-0.5" />
        <span>{getWellnessMessage()}</span>
      </div>

      {/* 2. Active Track Info */}
      {activeTrack ? (
        <div className={`mt-2 p-3 rounded-xl bg-gradient-to-br ${config.bgGradient} border border-white/5 flex flex-col gap-2`}>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-slate-800/80 flex items-center justify-center text-slate-400 border border-white/10 flex-shrink-0">
              <Music size={22} className={isPlaying ? 'animate-bounce' : ''} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-sm text-white truncate leading-tight">{activeTrack.title}</div>
              <div className="text-xs text-slate-400 truncate mt-0.5">{activeTrack.artist}</div>
            </div>
          </div>

          {/* Progress Slider */}
          <div className="flex flex-col gap-1 mt-1">
            <input 
              type="range" 
              min={0}
              max={duration || 100}
              value={currentTime}
              onChange={handleProgressChange}
              className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-sky-400 focus:outline-none"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-medium">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Main Controls */}
          <div className="flex items-center justify-between mt-1 px-1">
            <div className="flex items-center gap-1.5">
              <button 
                onClick={toggleMute}
                className="text-slate-400 hover:text-white transition-colors"
              >
                {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
              </button>
              <input 
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-12 h-1 bg-white/15 rounded-lg appearance-none cursor-pointer accent-sky-400 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-3">
              <button 
                onClick={handlePrev}
                className="p-1 rounded-full text-slate-400 hover:text-white transition-all hover:bg-white/5 active:scale-95 cursor-pointer"
              >
                <SkipBack size={18} />
              </button>
              <button 
                onClick={handlePlayPause}
                className="p-2 rounded-full bg-white hover:bg-slate-200 text-slate-900 transition-all hover:scale-105 active:scale-95 cursor-pointer shadow-md flex items-center justify-center"
              >
                {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
              </button>
              <button 
                onClick={handleNext}
                className="p-1 rounded-full text-slate-400 hover:text-white transition-all hover:bg-white/5 active:scale-95 cursor-pointer"
              >
                <SkipForward size={18} />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="py-6 text-center text-xs text-slate-500 italic">
          No track loaded.
        </div>
      )}

      {/* 3. Playlist Queue */}
      <div className="mt-3 flex-1 overflow-y-auto max-h-[190px] pr-1 flex flex-col gap-1.5 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 px-1">Playlist queue</div>
        {playlist.map((track, idx) => {
          const isSelected = idx === activeTrackIndex;
          return (
            <div 
              key={track.id}
              onClick={async () => {
                loadTrack(track, idx);
                if (audioRef.current) {
                  try {
                    await audioRef.current.play();
                  } catch (err) {
                    setIsPlaying(false);
                    console.warn('Autoplay blocked from playlist:', err);
                  }
                }
              }}
              className={`p-2 rounded-xl transition-all duration-200 flex items-center gap-3 cursor-pointer ${
                isSelected 
                  ? 'bg-white/10 border border-white/15 text-white shadow-sm' 
                  : 'bg-white/[0.02] border border-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-white'
              }`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs border ${
                isSelected 
                  ? 'bg-sky-500/20 border-sky-400/30 text-sky-400' 
                  : 'bg-slate-800/50 border-white/5 text-slate-400'
              }`}>
                {isSelected && isPlaying ? (
                  <div className="flex gap-0.5 items-end h-3">
                    <span className="w-0.5 h-3 bg-sky-400 animate-pulse rounded-full" />
                    <span className="w-0.5 h-2 bg-sky-400 animate-pulse rounded-full" style={{ animationDelay: '0.15s' }} />
                    <span className="w-0.5 h-3.5 bg-sky-400 animate-pulse rounded-full" style={{ animationDelay: '0.3s' }} />
                  </div>
                ) : (
                  <span>{getEmojiForCategory(track.categories[0])}</span>
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold truncate leading-none">{track.title}</div>
                <div className="text-[10px] text-slate-400 truncate mt-1 leading-none">{track.artist}</div>
              </div>
              {track.attributionUrl && (
                <a 
                  href={track.attributionUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-[9px] text-slate-500 hover:text-slate-300 transition-colors uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10"
                  title="View Pixabay License"
                >
                  License
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
