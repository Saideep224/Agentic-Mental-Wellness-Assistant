'use client';

import { useEffect, useRef, useCallback } from 'react';

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
  // Mouse position ref (not state, to avoid re-renders)
  const mouseRef = useRef({ x: 0, y: 0 });
  const smoothMouseRef = useRef({ x: 0, y: 0 });
  const driftOffsetRef = useRef(0);
  const rafIdRef = useRef<number>(0);
  const cloudContainerRef = useRef<HTMLDivElement>(null);
  const cloudRefs = useRef<(HTMLDivElement | null)[]>([]);

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
    driftOffsetRef.current += 0.015 * 1;

    // Apply transforms to each cloud layer
    CLOUD_LAYERS.forEach((cloud, i) => {
      const el = cloudRefs.current[i];
      if (!el) return;

      const parallaxX = smoothMouseRef.current.x * cloud.sensitivity * 1 * 40;
      const parallaxY = smoothMouseRef.current.y * cloud.sensitivity * 1 * 20;

      // Drift offset varies per cloud
      const driftX = Math.sin(driftOffsetRef.current * cloud.driftSpeed + cloud.id * 0.7) * 30;
      const driftY = Math.cos(driftOffsetRef.current * cloud.driftSpeed * 0.5 + cloud.id * 1.3) * 10;

      el.style.transform = `translate(${parallaxX + driftX}px, ${parallaxY + driftY}px)`;
    });

    rafIdRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    rafIdRef.current = requestAnimationFrame(animate);
    return () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, [animate]);

  return (
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
  );
}
