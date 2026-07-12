'use client';

import React, { useState, useEffect, useRef } from 'react';
import * as api from '@/api';

interface MusicPlayerProps {
  className?: string;
}

export default function MusicPlayer({ className = '' }: MusicPlayerProps) {
  const [profile, setProfile] = useState<any>(null);
  const [suggested, setSuggested] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  const loadData = async () => {
    const token = api.getToken();
    if (!token) return;
    try {
      setLoading(true);
      const [prof, sugg] = await Promise.all([
        api.getEmotionalProfile(token).catch(() => null),
        api.apiGet<any>('/api/music/suggested-songs', token).catch(() => null)
      ]);
      setProfile(prof);
      setSuggested(sugg);

      // Set audio tracks based on mood_type
      if (sugg?.mood_type === 'sadness') {
        // Slow acoustic lo-fi stream
        setAudioUrl('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3');
      } else if (sugg?.mood_type === 'anxiety') {
        // Calming ambient rain/lo-fi stream
        setAudioUrl('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3');
      } else {
        // Upbeat/motivational pop lo-fi stream
        setAudioUrl('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3');
      }
    } catch (err) {
      console.warn('Failed to load music player data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // Sync volume changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  // Handle Play/Pause
  const handleTogglePlay = () => {
    if (!audioRef.current && audioUrl) {
      const audio = new Audio(audioUrl);
      audio.volume = volume;
      audio.loop = true;
      audioRef.current = audio;
    }

    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play().then(() => {
          setIsPlaying(true);
        }).catch((err) => {
          console.warn('Playback failed:', err);
        });
      }
    }
  };

  // Check if user interests include music or songs
  const interestsList = profile?.interests || [];
  const likesMusic = interestsList.some((i: string) => 
    i.toLowerCase().includes('music') || 
    i.toLowerCase().includes('song') ||
    i.toLowerCase().includes('singing') ||
    i.toLowerCase().includes('instrument')
  );

  if (loading) {
    return (
      <div className={`p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] animate-pulse text-center text-xs text-[var(--text-muted)] ${className}`}>
        Tuning Buddy Radio... 📻
      </div>
    );
  }

  // Get color themes dynamically based on mood type
  let moodColor = 'rgba(56, 189, 248, 0.15)'; // default cyan
  let moodBorder = 'rgba(56, 189, 248, 0.3)';
  let moodText = 'text-sky-400';
  let playlistIcon = '🎵';

  if (suggested?.mood_type === 'sadness') {
    moodColor = 'rgba(245, 158, 11, 0.15)'; // amber
    moodBorder = 'rgba(245, 158, 11, 0.3)';
    moodText = 'text-amber-400';
    playlistIcon = '🍂';
  } else if (suggested?.mood_type === 'anxiety') {
    moodColor = 'rgba(167, 139, 250, 0.15)'; // purple
    moodBorder = 'rgba(167, 139, 250, 0.3)';
    moodText = 'text-purple-400';
    playlistIcon = '🌧️';
  } else if (suggested?.mood_type === 'happy') {
    moodColor = 'rgba(16, 185, 129, 0.15)'; // emerald
    moodBorder = 'rgba(16, 185, 129, 0.3)';
    moodText = 'text-emerald-400';
    playlistIcon = '☀️';
  }

  return (
    <div className={`p-4 rounded-2xl border transition-all duration-300 ${className}`}
      style={{
        background: 'rgba(9, 13, 26, 0.65)',
        backdropFilter: 'blur(16px)',
        borderColor: isPlaying ? moodBorder : 'var(--glass-border)',
        boxShadow: isPlaying ? `0 0 20px ${moodColor}` : 'none'
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{playlistIcon}</span>
          <div>
            <h4 className="text-xs font-bold text-[var(--text-primary)] leading-none">Buddy Radio</h4>
            <span className="text-[9px] text-[var(--text-muted)] mt-1 inline-block">Mood-adaptive beats</span>
          </div>
        </div>
        {likesMusic && (
          <span className="text-[9px] font-semibold bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-white/60">
            Music Lover
          </span>
        )}
      </div>

      <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] mb-3">
        <span className={`text-[10px] uppercase font-bold tracking-wider ${moodText}`}>
          Suggested Genre: {suggested?.genre || 'Lo-Fi Chill'}
        </span>
        <div className="mt-2 space-y-1">
          {suggested?.songs?.map((song: string, idx: number) => {
            const encodedSearch = encodeURIComponent(song);
            const spotifyUrl = `https://open.spotify.com/search/${encodedSearch}`;
            const youtubeUrl = `https://www.youtube.com/results?search_query=${encodedSearch}`;

            return (
              <div key={idx} className="flex items-center justify-between gap-2 py-0.5 border-b border-white/[0.02] last:border-0">
                <span className="text-[11px] text-[var(--text-primary)] truncate font-medium flex-1">
                  {idx + 1}. {song}
                </span>
                <div className="flex items-center gap-1.5">
                  <a href={spotifyUrl} target="_blank" rel="noopener noreferrer" 
                     className="text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors font-medium hover:underline">
                    Spotify
                  </a>
                  <span className="text-[9px] text-white/20">|</span>
                  <a href={youtubeUrl} target="_blank" rel="noopener noreferrer"
                     className="text-[10px] text-red-400 hover:text-red-300 transition-colors font-medium hover:underline">
                    YouTube
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Local lo-fi player controller */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleTogglePlay}
          className="w-8 h-8 rounded-full flex items-center justify-center bg-white text-black hover:bg-white/90 active:scale-95 transition-all shadow-md"
          title={isPlaying ? "Pause Radio" : "Play Radio"}
        >
          {isPlaying ? (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M6.75 5.25a.75.75 0 0 1 .75-.75H9a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H7.5a.75.75 0 0 1-.75-.75V5.25Zm7.5 0A.75.75 0 0 1 15 4.5h1.5a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H15a.75.75 0 0 1-.75-.75V5.25Z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 translate-x-[1px]">
              <path fillRule="evenodd" d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z" clipRule="evenodd" />
            </svg>
          )}
        </button>

        {isPlaying && (
          <div className="flex-1 flex items-center gap-1.5">
            {/* Visual Equalizer animation */}
            <div className="flex items-end gap-[2px] h-3 w-6">
              <span className="w-[3px] bg-sky-400 animate-[eq-bar_0.8s_ease-in-out_infinite_alternate]" style={{ height: '30%' }}></span>
              <span className="w-[3px] bg-purple-400 animate-[eq-bar_0.6s_ease-in-out_infinite_alternate_0.2s]" style={{ height: '70%' }}></span>
              <span className="w-[3px] bg-pink-400 animate-[eq-bar_0.9s_ease-in-out_infinite_alternate_0.4s]" style={{ height: '50%' }}></span>
              <span className="w-[3px] bg-amber-400 animate-[eq-bar_0.7s_ease-in-out_infinite_alternate_0.1s]" style={{ height: '40%' }}></span>
            </div>
            <span className="text-[10px] text-[var(--text-muted)] italic font-mono truncate">
              {isPlaying ? "Streaming lo-fi beats..." : ""}
            </span>
          </div>
        )}

        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-[9px] text-[var(--text-muted)] select-none">🔊</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="w-16 h-1 rounded bg-white/15 appearance-none cursor-pointer outline-none accent-white"
          />
        </div>
      </div>
    </div>
  );
}
