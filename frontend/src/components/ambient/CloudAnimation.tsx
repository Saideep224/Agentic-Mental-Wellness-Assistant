'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cloud, Eye, EyeOff, X, Minus, Plus } from 'lucide-react';

interface CloudLayer {
  id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
  driftSpeed: number;
  sensitivity: number; // cursor parallax sensitivity
  blur: number;
  type: 'gradient' | 'image';
  imageSrc?: string;
  zIndex: number;
}

const CLOUD_LAYERS: CloudLayer[] = [
  // Far background — slow drift, low sensitivity
  { id: 1, x: 5, y: 8, width: 350, height: 180, opacity: 0.12, driftSpeed: 0.3, sensitivity: 0.3, blur: 4, type: 'gradient', zIndex: 1 },
  { id: 2, x: 65, y: 5, width: 400, height: 200, opacity: 0.1, driftSpeed: 0.25, sensitivity: 0.25, blur: 5, type: 'gradient', zIndex: 1 },
  // Mid layer — moderate drift and sensitivity
  { id: 3, x: 15, y: 35, width: 300, height: 150, opacity: 0.15, driftSpeed: 0.5, sensitivity: 0.6, blur: 3, type: 'gradient', zIndex: 2 },
  { id: 4, x: 70, y: 25, width: 280, height: 140, opacity: 0.14, driftSpeed: 0.45, sensitivity: 0.55, blur: 3, type: 'gradient', zIndex: 2 },
  { id: 5, x: 40, y: 60, width: 320, height: 160, opacity: 0.12, driftSpeed: 0.4, sensitivity: 0.5, blur: 3, type: 'gradient', zIndex: 2 },
  // Foreground — fast drift, high sensitivity
  { id: 6, x: -5, y: 70, width: 450, height: 220, opacity: 0.12, driftSpeed: 0.7, sensitivity: 1.2, blur: 5, type: 'gradient', zIndex: 3 },
  { id: 7, x: 80, y: 65, width: 310, height: 150, opacity: 0.16, driftSpeed: 0.65, sensitivity: 1.0, blur: 3, type: 'gradient', zIndex: 3 },
  { id: 8, x: 30, y: 80, width: 250, height: 120, opacity: 0.15, driftSpeed: 0.6, sensitivity: 0.8, blur: 3, type: 'gradient', zIndex: 3 },
];

export default function CloudAnimation() {
  const [isOpen, setIsOpen] = useState(false);
  const [driftMultiplier, setDriftMultiplier] = useState(1);
  const [cursorSensitivity, setCursorSensitivity] = useState(1);
  const [showClouds, setShowClouds] = useState(true);

  // Mouse position ref (not state, to avoid re-renders)
  const mouseRef = useRef({ x: 0, y: 0 });
  const smoothMouseRef = useRef({ x: 0, y: 0 });
  const driftOffsetRef = useRef(0);
  const rafIdRef = useRef<number>(0);
  const cloudContainerRef = useRef<HTMLDivElement>(null);
  const cloudRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Load from localStorage
  useEffect(() => {
    const savedDrift = localStorage.getItem('esona-cloud-drift');
    const savedSens = localStorage.getItem('esona-cloud-sensitivity');
    const savedShow = localStorage.getItem('esona-cloud-show');

    if (savedDrift) setDriftMultiplier(Number(savedDrift));
    if (savedSens) setCursorSensitivity(Number(savedSens));
    if (savedShow) setShowClouds(savedShow === 'true');
  }, []);

  const handleSetDrift = (val: number) => {
    setDriftMultiplier(val);
    localStorage.setItem('esona-cloud-drift', String(val));
  };

  const handleSetSensitivity = (val: number) => {
    setCursorSensitivity(val);
    localStorage.setItem('esona-cloud-sensitivity', String(val));
  };

  const handleSetShowClouds = (val: boolean) => {
    setShowClouds(val);
    localStorage.setItem('esona-cloud-show', String(val));
  };

  // Mouse tracking
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;
      mouseRef.current = {
        x: (e.clientX - centerX) / centerX, // -1 to 1
        y: (e.clientY - centerY) / centerY, // -1 to 1
      };
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Animation loop — smooth lerp + drift
  const animate = useCallback(() => {
    const lerpFactor = 0.04; // smooth interpolation speed

    // Smooth mouse position
    smoothMouseRef.current.x += (mouseRef.current.x - smoothMouseRef.current.x) * lerpFactor;
    smoothMouseRef.current.y += (mouseRef.current.y - smoothMouseRef.current.y) * lerpFactor;

    // Drift offset (continuous horizontal movement)
    driftOffsetRef.current += 0.015 * driftMultiplier;

    // Apply transforms to each cloud layer
    CLOUD_LAYERS.forEach((cloud, i) => {
      const el = cloudRefs.current[i];
      if (!el) return;

      const parallaxX = smoothMouseRef.current.x * cloud.sensitivity * cursorSensitivity * 40;
      const parallaxY = smoothMouseRef.current.y * cloud.sensitivity * cursorSensitivity * 20;

      // Drift offset varies per cloud
      const driftX = Math.sin(driftOffsetRef.current * cloud.driftSpeed + cloud.id * 0.7) * 30;
      const driftY = Math.cos(driftOffsetRef.current * cloud.driftSpeed * 0.5 + cloud.id * 1.3) * 10;

      el.style.transform = `translate(${parallaxX + driftX}px, ${parallaxY + driftY}px)`;
    });

    rafIdRef.current = requestAnimationFrame(animate);
  }, [driftMultiplier, cursorSensitivity]);

  useEffect(() => {
    if (showClouds) {
      rafIdRef.current = requestAnimationFrame(animate);
    }
    return () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, [animate, showClouds]);

  const getDriftLabel = (val: number) => {
    if (val <= 0.5) return 'Still Air ☁️';
    if (val <= 1) return 'Gentle Breeze 🍃';
    if (val <= 1.5) return 'Drifting ☁️';
    if (val <= 2) return 'Breezy 💨';
    return 'Rushing Wind 🌬️';
  };

  return (
    <>
      {/* Cloud layers */}
      {showClouds && (
        <div
          ref={cloudContainerRef}
          className="fixed inset-0 pointer-events-none overflow-hidden"
          style={{ zIndex: 1 }}
          aria-hidden="true"
        >
          {CLOUD_LAYERS.map((cloud, i) => (
            <div
              key={cloud.id}
              ref={(el) => { cloudRefs.current[i] = el; }}
              className="absolute will-change-transform"
              style={{
                left: `${cloud.x}%`,
                top: `${cloud.y}%`,
                width: `${cloud.width}px`,
                height: `${cloud.height}px`,
                opacity: cloud.opacity,
                filter: cloud.blur > 0 ? `blur(${cloud.blur}px)` : undefined,
                zIndex: cloud.zIndex,
                transition: 'opacity 0.5s ease',
              }}
            >
              <div
                className="w-full h-full rounded-full"
                style={{
                  background: 'radial-gradient(ellipse at center, rgba(56, 189, 248, 0.15) 0%, rgba(167, 139, 250, 0.06) 50%, transparent 100%)',
                }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Cloud Controller Widget */}
      <div className="fixed bottom-6 left-6 z-50 pointer-events-auto">
        <AnimatePresence>
          {!isOpen ? (
            <motion.button
              layoutId="cloud-panel"
              onClick={() => setIsOpen(true)}
              whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(91, 155, 213, 0.3)' }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center justify-center w-12 h-12 rounded-full cursor-pointer glass-card text-white"
              title="Adjust Cloud Settings"
            >
              <motion.div
                animate={{ y: [0, -3, 0] }}
                transition={{ repeat: Infinity, duration: 3, ease: 'easeInOut' }}
              >
                <Cloud size={20} className="text-sky-400" />
              </motion.div>
            </motion.button>
          ) : (
            <motion.div
              layoutId="cloud-panel"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-72 rounded-2xl glass-card p-5 shadow-2xl relative overflow-hidden"
              style={{
                background: 'rgba(10, 14, 30, 0.8)',
                backdropFilter: 'blur(20px)',
              }}
            >
              <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-2">
                <div className="flex items-center gap-2">
                  <Cloud size={18} className="text-sky-400 animate-pulse" />
                  <h3
                    className="font-semibold text-sm text-white"
                    style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
                  >
                    Cloud Controller
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
                {/* Drift Speed */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-white/70">
                    <span>Drift Speed</span>
                    <span className="font-medium text-sky-400">{driftMultiplier.toFixed(1)}×</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="3"
                    step="0.1"
                    value={driftMultiplier}
                    onChange={(e) => handleSetDrift(Number(e.target.value))}
                    className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-sky-400"
                  />
                  <div className="text-[10px] text-white/50 italic text-right font-medium">
                    {getDriftLabel(driftMultiplier)}
                  </div>
                </div>

                {/* Cursor Sensitivity */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center text-white/70">
                    <span>Cursor Effect</span>
                    <span className="font-medium text-sky-400">{cursorSensitivity.toFixed(1)}×</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="3"
                    step="0.1"
                    value={cursorSensitivity}
                    onChange={(e) => handleSetSensitivity(Number(e.target.value))}
                    className="w-full h-1 bg-white/10 rounded-lg appearance-none cursor-pointer accent-sky-400"
                  />
                </div>

                {/* Toggle Clouds */}
                <div className="flex items-center justify-between pt-1">
                  <span className="text-white/70">Show Clouds</span>
                  <button
                    onClick={() => handleSetShowClouds(!showClouds)}
                    className="p-1.5 rounded-lg border cursor-pointer hover:bg-white/5 transition-all duration-200"
                    style={{
                      color: showClouds ? 'rgb(56, 189, 248)' : 'rgba(255, 255, 255, 0.3)',
                      borderColor: showClouds ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    {showClouds ? <Eye size={16} /> : <EyeOff size={16} />}
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
