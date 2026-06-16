'use client';

import HeroSection from '@/components/landing/HeroSection';
import FeatureCards from '@/components/landing/FeatureCards';
import CTASection from '@/components/landing/CTASection';

export default function LandingPage() {
  return (
    <main className="relative">
      <HeroSection />
      <FeatureCards />
      <CTASection />

      {/* Footer */}
      <footer className="relative z-10 py-8 text-center border-t" style={{ borderColor: 'var(--glass-border)' }}>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          © {new Date().getFullYear()} Esona — Your Supporting Buddy. Built with care. 💙
        </p>
      </footer>
    </main>
  );
}
