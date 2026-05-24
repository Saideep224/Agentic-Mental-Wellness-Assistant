'use client';

import { useEffect, useState } from 'react';

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  duration: number;
  delay: number;
  color: string;
}

export default function FloatingParticles() {
  const [particles, setParticles] = useState<Particle[]>([]);

  useEffect(() => {
    const colors = [
      'rgba(34, 211, 238, 0.4)',  // cyan
      'rgba(167, 139, 250, 0.35)', // purple
      'rgba(59, 130, 246, 0.3)',   // blue
      'rgba(34, 211, 238, 0.25)',  // dim cyan
      'rgba(167, 139, 250, 0.2)', // dim purple
    ];

    const generated: Particle[] = Array.from({ length: 40 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 2 + Math.random() * 3,
      opacity: 0.1 + Math.random() * 0.3,
      duration: 10 + Math.random() * 20,
      delay: Math.random() * 15,
      color: colors[Math.floor(Math.random() * colors.length)],
    }));

    setParticles(generated);
  }, []);

  if (particles.length === 0) return null;

  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      {particles.map((particle) => (
        <div
          key={particle.id}
          className="absolute rounded-full"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: `${particle.size}px`,
            height: `${particle.size}px`,
            backgroundColor: particle.color,
            boxShadow: `0 0 ${particle.size * 3}px ${particle.color}`,
            opacity: particle.opacity,
            animation: `particle-drift ${particle.duration}s linear ${particle.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
