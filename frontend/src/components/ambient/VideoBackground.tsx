'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * VideoBackground – renders BG1.mp4 as a full-screen fixed background layer.
 *
 * Flash-prevention strategy:
 * 1. html { background-color: #040614 } in globals.css ensures the first paint
 *    is always the correct dark color — no white/gray flash before JS runs.
 * 2. `poster="/background.png"` shows a static frame of the background
 *    immediately while the video file is still being downloaded / decoded.
 * 3. An opaque overlay (#040614) sits on top of the video and fades to
 *    transparent only once `canplay` fires — so the first visible video frame
 *    is never a half-loaded or black flicker.
 */
export default function VideoBackground() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoReady, setVideoReady] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // `canplay` fires as soon as the browser has buffered enough to start —
    // this is when we safely reveal the live video (fade the overlay out).
    const handleCanPlay = () => setVideoReady(true);

    // If the video is already ready (cached), fire immediately.
    if (video.readyState >= 3) {
      setVideoReady(true);
    } else {
      video.addEventListener('canplay', handleCanPlay, { once: true });
    }

    return () => {
      video.removeEventListener('canplay', handleCanPlay);
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
      }}
    >
      {/* The video itself — poster provides instant still frame before the
          video data arrives. The browser shows the poster on the very first
          frame, so there is never a black or blank moment. */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        poster="/background.png"
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: 'center',
        }}
      >
        <source src="/BG1.mp4" type="video/mp4" />
      </video>

      {/* Flash-prevention overlay: starts opaque (#040614 = --bg-primary),
          fades to transparent once the video is ready to play.
          This hides any single-frame decode glitch when the video first starts. */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: '#040614',
          opacity: videoReady ? 0 : 1,
          transition: 'opacity 0.8s ease-out',
          pointerEvents: 'none',
          zIndex: 1,
        }}
      />

      {/* Multi-layer cinematic overlay — darkens the video so text pops */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(4, 8, 25, 0.72)',
          zIndex: 2,
        }}
      />

      {/* Subtle vignette edges for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at center, transparent 50%, rgba(4,6,20,0.55) 100%)',
          zIndex: 3,
        }}
      />
    </div>
  );
}
