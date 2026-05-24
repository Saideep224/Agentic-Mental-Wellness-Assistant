'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wind, ArrowLeft, ArrowRight, Eye, EyeOff, X } from 'lucide-react';

export default function WaveAnimation() {
  const [isOpen, setIsOpen] = useState(false);
  const [windSpeed, setWindSpeed] = useState<number>(3);
  const [windDirection, setWindDirection] = useState<'left' | 'right'>('right');
  const [showWindTrails, setShowWindTrails] = useState<boolean>(true);

  // Sync settings with local storage for session persistence
  useEffect(() => {
    const savedSpeed = localStorage.getItem('esona-wind-speed');
    const savedDir = localStorage.getItem('esona-wind-dir');
    const savedTrails = localStorage.getItem('esona-wind-trails');

    if (savedSpeed) setWindSpeed(Number(savedSpeed));
    if (savedDir) setWindDirection(savedDir as 'left' | 'right');
    if (savedTrails) setShowWindTrails(savedTrails === 'true');
  }, []);

  const handleSetWindSpeed = (speed: number) => {
    setWindSpeed(speed);
    localStorage.setItem('esona-wind-speed', String(speed));
  };

  const handleSetWindDirection = (dir: 'left' | 'right') => {
    setWindDirection(dir);
    localStorage.setItem('esona-wind-dir', dir);
  };

  const handleSetShowWindTrails = (show: boolean) => {
    setShowWindTrails(show);
    localStorage.setItem('esona-wind-trails', String(show));
  };

  // Map wind speeds to human-readable descriptors
  const getWindDescription = (speed: number) => {
    if (speed <= 2) return 'Calm Breeze 🍃';
    if (speed <= 4) return 'Gentle Wind 💨';
    if (speed <= 6) return 'Fresh Breeze 🌊';
    if (speed <= 8) return 'Moderate Gale 🌪️';
    return 'Storm Force! ⚡';
  };

  // Dynamically calculate animation speed (faster speed = shorter duration)
  const duration1 = `${Math.max(15 * (3 / windSpeed), 2)}s`;
  const duration2 = `${Math.max(20 * (3 / windSpeed), 3)}s`;
  const duration3 = `${Math.max(25 * (3 / windSpeed), 4)}s`;

  // Scale the wave height dynamically with the wind force
  const height1 = `${100 + windSpeed * 8}px`;
  const height2 = `${80 + windSpeed * 7}px`;
  const height3 = `${60 + windSpeed * 6}px`;

  // Determine direction
  const animDirection = windDirection === 'left' ? 'normal' : 'reverse';

  // Trails data
  const trails = Array.from({ length: 7 });

  return (
    <>
      {/* Scope-contained style inject for wind trail keyframes */}
      <style jsx global>{`
        @keyframes wind-trail-right {
          0% {
            transform: translateX(-150px) scaleX(0.7);
            opacity: 0;
          }
          10% {
            opacity: 0.15;
          }
          90% {
            opacity: 0.15;
          }
          100% {
            transform: translateX(100vw) scaleX(1.4);
            opacity: 0;
          }
        }
        @keyframes wind-trail-left {
          0% {
            transform: translateX(100vw) scaleX(0.7);
            opacity: 0;
          }
          10% {
            opacity: 0.15;
          }
          90% {
            opacity: 0.15;
          }
          100% {
            transform: translateX(-150px) scaleX(1.4);
            opacity: 0;
          }
        }
      `}</style>

      {/* Wind Trails Layer */}
      {showWindTrails && (
        <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
          {trails.map((_, i) => {
            const top = 10 + i * 12; // vertical distribution
            const delay = i * 2.0; // stagger start times
            const trailDuration = (7 / windSpeed) * 3; // faster speed = shorter duration
            const scale = 0.6 + (i % 3) * 0.2; // randomized sizes

            return (
              <svg
                key={i}
                className="absolute opacity-0"
                style={{
                  top: `${top}%`,
                  width: '150px',
                  height: '12px',
                  animation: `${windDirection === 'right' ? 'wind-trail-right' : 'wind-trail-left'} ${trailDuration}s linear infinite`,
                  animationDelay: `${delay}s`,
                  transform: `scale(${scale})`,
                }}
                viewBox="0 0 100 10"
                preserveAspectRatio="none"
              >
                <path
                  d="M0,5 Q25,8 50,5 T100,5"
                  fill="none"
                  stroke="rgba(255, 255, 255, 0.2)"
                  strokeWidth="1.2"
                  strokeDasharray="8,4"
                />
              </svg>
            );
          })}
        </div>
      )}

      {/* Wave Animation Layer */}
      <div
        className="fixed bottom-0 left-0 w-full pointer-events-none overflow-hidden"
        style={{ zIndex: 0, height: '220px' }}
        aria-hidden="true"
      >
        {/* Wave Layer 1 - Cyan (Top layer, fastest) */}
        <svg
          className="absolute bottom-0"
          style={{
            width: '200%',
            height: height1,
            opacity: 0.1,
            animation: `wave ${duration1} linear infinite`,
            animationDirection: animDirection,
          }}
          viewBox="0 0 1440 120"
          preserveAspectRatio="none"
        >
          <path
            d="M0,60 C180,120 360,0 540,60 C720,120 900,0 1080,60 C1260,120 1440,0 1440,60 L1440,120 L0,120 Z"
            fill="#22d3ee"
          />
          <path
            d="M1440,60 C1620,120 1800,0 1980,60 C2160,120 2340,0 2520,60 C2700,120 2880,0 2880,60 L2880,120 L1440,120 Z"
            fill="#22d3ee"
          />
        </svg>

        {/* Wave Layer 2 - Blue (Middle layer) */}
        <svg
          className="absolute bottom-0"
          style={{
            width: '200%',
            height: height2,
            opacity: 0.07,
            animation: `wave ${duration2} linear infinite`,
            animationDirection: animDirection === 'normal' ? 'reverse' : 'normal', // counter-flow
          }}
          viewBox="0 0 1440 100"
          preserveAspectRatio="none"
        >
          <path
            d="M0,50 C240,100 480,0 720,50 C960,100 1200,0 1440,50 L1440,100 L0,100 Z"
            fill="#3b82f6"
          />
          <path
            d="M1440,50 C1680,100 1920,0 2160,50 C2400,100 2640,0 2880,50 L2880,100 L1440,100 Z"
            fill="#3b82f6"
          />
        </svg>

        {/* Wave Layer 3 - Purple (Bottom layer, slowest) */}
        <svg
          className="absolute bottom-0"
          style={{
            width: '200%',
            height: height3,
            opacity: 0.05,
            animation: `wave ${duration3} linear infinite`,
            animationDirection: animDirection,
          }}
          viewBox="0 0 1440 80"
          preserveAspectRatio="none"
        >
          <path
            d="M0,40 C360,80 720,0 1080,40 C1440,80 1440,0 1440,40 L1440,80 L0,80 Z"
            fill="#a78bfa"
          />
          <path
            d="M1440,40 C1800,80 2160,0 2520,40 C2880,80 2880,0 2880,40 L2880,80 L1440,80 Z"
            fill="#a78bfa"
          />
        </svg>
      </div>

      {/* Floating Wind Controller Widget */}
      <div className="fixed bottom-6 left-6 z-50 pointer-events-auto">
        <AnimatePresence>
          {!isOpen ? (
            <motion.button
              layoutId="wind-panel"
              onClick={() => setIsOpen(true)}
              whileHover={{ scale: 1.05, boxShadow: 'var(--glow-cyan)' }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center justify-center w-12 h-12 rounded-full cursor-pointer glass-card border border-white/10 text-white"
              title="Adjust Wind Settings"
            >
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ repeat: Infinity, duration: 4, ease: 'easeInOut' }}
              >
                <Wind size={20} className="text-cyan-400" />
              </motion.div>
            </motion.button>
          ) : (
            <motion.div
              layoutId="wind-panel"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-72 rounded-2xl glass-card border border-white/10 p-5 shadow-2xl relative overflow-hidden"
              style={{
                background: 'rgba(10, 14, 26, 0.75)',
                backdropFilter: 'blur(20px)',
              }}
            >
              <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
                <div className="flex items-center gap-2">
                  <Wind size={18} className="text-cyan-400 animate-pulse" />
                  <h3 className="font-semibold text-sm text-white" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                    Wind Controller
                  </h3>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-white/40 hover:text-white cursor-pointer transition-colors duration-200"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-4 text-xs">
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-white/70">
                    <span>Wind Force</span>
                    <span className="font-medium text-cyan-400">{windSpeed}x</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={windSpeed}
                    onChange={(e) => handleSetWindSpeed(Number(e.target.value))}
                    className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                  />
                  <div className="text-[10px] text-white/50 italic text-right font-medium">
                    {getWindDescription(windSpeed)}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="text-white/70 block">Wind Direction</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSetWindDirection('left')}
                      className="flex-1 py-1.5 rounded-lg border flex items-center justify-center gap-1 cursor-pointer transition-all duration-300"
                      style={{
                        background: windDirection === 'left' ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                        color: windDirection === 'left' ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.5)',
                        borderColor: windDirection === 'left' ? 'rgba(34, 211, 238, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      }}
                    >
                      <ArrowLeft size={14} />
                      <span>Leftward</span>
                    </button>
                    <button
                      onClick={() => handleSetWindDirection('right')}
                      className="flex-1 py-1.5 rounded-lg border flex items-center justify-center gap-1 cursor-pointer transition-all duration-300"
                      style={{
                        background: windDirection === 'right' ? 'rgba(34, 211, 238, 0.1)' : 'transparent',
                        color: windDirection === 'right' ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.5)',
                        borderColor: windDirection === 'right' ? 'rgba(34, 211, 238, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                      }}
                    >
                      <span>Rightward</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-white/70">Show Wind Trails</span>
                  <button
                    onClick={() => handleSetShowWindTrails(!showWindTrails)}
                    className="p-1.5 rounded-lg border cursor-pointer hover:bg-white/5 transition-all duration-200"
                    style={{
                      color: showWindTrails ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.3)',
                      borderColor: showWindTrails ? 'rgba(34, 211, 238, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    {showWindTrails ? <Eye size={16} /> : <EyeOff size={16} />}
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
