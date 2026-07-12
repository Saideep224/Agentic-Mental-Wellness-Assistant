'use client';

import CinematicHome from '@/components/home/cinematic/CinematicHome';
import SmoothScroll from '@/components/ambient/SmoothScroll';

export default function LandingPage() {
  return (
    <SmoothScroll>
      <main className="relative bg-[#040614] min-h-screen w-full">
        <CinematicHome />
      </main>
    </SmoothScroll>
  );
}
