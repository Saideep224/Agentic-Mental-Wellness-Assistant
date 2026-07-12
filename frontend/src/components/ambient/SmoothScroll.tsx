'use client';

import { useEffect, useRef } from 'react';
import Lenis from 'lenis';

interface Props {
  children: React.ReactNode;
}

export default function SmoothScroll({ children }: Props) {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Initialize Lenis
    const lenis = new Lenis({
      duration: 1.5,           // Duration of the scroll animation
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // Custom easing curve (easeOutExpo)
      orientation: 'vertical',
      gestureOrientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 0.9,     // Slightly reduce wheel speed for cinematic pacing
      touchMultiplier: 1.5,     // Maintain fluid touch paging
      infinite: false,
    });

    lenisRef.current = lenis;
    (window as any).lenis = lenis;

    // RAF Loop
    let rafId: number;
    function raf(time: number) {
      lenis.raf(time);
      rafId = requestAnimationFrame(raf);
    }
    rafId = requestAnimationFrame(raf);

    // Sync Lenis with standard scroll events to ensure page layout shifts update
    const resizeObserver = new ResizeObserver(() => {
      lenis.resize();
    });
    resizeObserver.observe(document.body);

    return () => {
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      lenis.destroy();
      if ((window as any).lenis === lenis) {
        (window as any).lenis = null;
      }
    };
  }, []);

  return <>{children}</>;
}
