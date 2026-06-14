'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/providers/AuthProvider';
import HeroSection from '@/components/landing/HeroSection';
import FeatureCards from '@/components/landing/FeatureCards';
import CTASection from '@/components/landing/CTASection';

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // If the user is already authenticated (e.g. pressed Back after login),
  // silently send them to /chat without allowing the landing page to render.
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace('/chat');
    }
  }, [isAuthenticated, isLoading, router]);

  // While auth is loading or redirect is pending, render nothing visible
  if (isLoading || isAuthenticated) {
    return <div className="min-h-screen" />;
  }

  return (
    <main className="relative">
      <HeroSection />
      <FeatureCards />
      <CTASection />

      {/* Footer */}
      <footer className="relative z-10 py-8 text-center border-t" style={{ borderColor: 'var(--glass-border)' }}>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          © {new Date().getFullYear()} Esona — Your Supporting Buddie. Built with care. 💙
        </p>
      </footer>
    </main>
  );
}
