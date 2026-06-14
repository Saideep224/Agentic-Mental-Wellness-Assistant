'use client';

/**
 * VideoBackground – renders BG1.mp4 as a full-screen fixed background layer.
 * A dark cinematic overlay sits on top so all UI remains crisp and readable.
 */
export default function VideoBackground() {
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
      {/* The video itself */}
      <video
        autoPlay
        loop
        muted
        playsInline
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

      {/* Multi-layer cinematic overlay — darkens the video so text pops */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(4, 8, 25, 0.72)',
        }}
      />

      {/* Subtle vignette edges for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse at center, transparent 50%, rgba(4,6,20,0.55) 100%)',
        }}
      />
    </div>
  );
}
