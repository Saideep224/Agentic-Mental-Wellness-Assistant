'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import HeroSection from '@/components/landing/HeroSection';
import FeatureCards from '@/components/landing/FeatureCards';
import CTASection from '@/components/landing/CTASection';
import { supabase } from '@/database/supabase';

export default function LandingPage() {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          // User is already authenticated — redirect to chat
          router.replace('/chat');
          return;
        }
      } catch (err) {
        console.warn('[LandingPage] Auth check failed:', err);
      }
      setIsChecking(false);
    };

    checkAuth();
  }, [router]);

  // Show nothing while checking auth to prevent flash of landing page
  if (isChecking) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 rounded-full border-2 border-sky-400/30 border-t-sky-400 animate-spin" />
      </main>
    );
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
