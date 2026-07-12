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
      <footer className="relative z-10 py-8 text-center border-t px-4" style={{ borderColor: 'var(--glass-border)' }}>
        <p className="text-[10px] sm:text-xs max-w-2xl mx-auto mb-4 opacity-75 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          Note: Esona is an AI wellness companion, not a licensed therapist or crisis counselor. If you are in distress or danger, please contact professional emergency services or helplines.
        </p>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          © {new Date().getFullYear()} Esona — Your AI Wellness Companion. Built with care. 💙
        </p>
      </footer>
    </main>
  );
}
