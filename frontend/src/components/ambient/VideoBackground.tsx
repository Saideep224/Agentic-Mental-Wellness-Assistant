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
          background:
            'linear-gradient(180deg, rgba(4,6,20,0.62) 0%, rgba(4,6,20,0.50) 40%, rgba(4,6,20,0.68) 80%, rgba(4,6,20,0.88) 100%)',
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
