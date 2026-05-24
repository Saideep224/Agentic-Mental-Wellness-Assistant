'use client';

export default function WaveAnimation() {
  return (
    <div
      className="fixed bottom-0 left-0 w-full pointer-events-none overflow-hidden"
      style={{ zIndex: 0, height: '200px' }}
      aria-hidden="true"
    >
      {/* Wave Layer 1 - Cyan */}
      <svg
        className="absolute bottom-0 animate-wave"
        style={{ width: '200%', height: '120px', opacity: 0.1 }}
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

      {/* Wave Layer 2 - Blue */}
      <svg
        className="absolute bottom-0"
        style={{
          width: '200%',
          height: '100px',
          opacity: 0.07,
          animation: 'wave 20s linear infinite',
          animationDirection: 'reverse',
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

      {/* Wave Layer 3 - Purple */}
      <svg
        className="absolute bottom-0"
        style={{
          width: '200%',
          height: '80px',
          opacity: 0.05,
          animation: 'wave 25s linear infinite',
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
  );
}
