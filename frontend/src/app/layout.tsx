import type { Metadata } from 'next';
import { Inter, Space_Grotesk } from 'next/font/google';
import '@/styles/globals.css';
import AuthProvider from '@/providers/AuthProvider';
import ThemeProvider from '@/providers/ThemeProvider';
import FloatingParticles from '@/components/ambient/FloatingParticles';
import VideoBackground from '@/components/ambient/VideoBackground';
import PageTransition from '@/components/layout/PageTransition';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXTAUTH_URL || 'http://localhost:3000'),
  title: 'Esona - Your Supporting Buddy',
  description:
    'An emotionally adaptive AI that truly understands you — your moods, your words, your silence. Esona is a multi-agent mental wellness chatbot that grows with you.',
  keywords: ['mental health', 'AI chatbot', 'emotional support', 'wellness', 'therapy'],
  authors: [{ name: 'Esona Team' }],
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/favicon.png', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png' },
    ],
  },
  manifest: '/manifest.json',
  openGraph: {
    title: 'Esona - Your Supporting Buddy',
    description:
      'An emotionally adaptive AI that truly understands you — your moods, your words, your silence. Esona is a multi-agent mental wellness chatbot that grows with you.',
    type: 'website',
    images: [
      {
        url: '/logo.png',
        width: 1200,
        height: 630,
        alt: 'Esona Logo',
      },
    ],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="dark"
      // Inline style on <html> ensures the dark base is applied even
      // before the external CSS file is parsed — eliminates the very
      // first-frame white flash on cold loads.
      style={{ backgroundColor: '#040614' }}
    >
      <head>
        {/*
         * Preload hints — tell the browser to fetch these assets at the
         * highest network priority BEFORE the page finishes parsing.
         * background.png = poster for the video → visible on first paint.
         * BG1.mp4       = background video   → starts playing sooner.
         */}
        <link rel="preload" href="/background.png" as="image" />
        <link
          rel="preload"
          href="/BG1.mp4"
          as="video"
          type="video/mp4"
          // @ts-expect-error — crossOrigin is valid on link preload
          crossOrigin="anonymous"
        />
      </head>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} font-sans antialiased`}
        style={{
          fontFamily: 'var(--font-inter), system-ui, sans-serif',
        }}
      >
        <AuthProvider>
          <ThemeProvider>
            {/* Ambient background */}
            <VideoBackground />
            <FloatingParticles />

            {/* Main content with smooth page fade */}
            <div className="relative z-10 min-h-screen">
              <PageTransition>
                {children}
              </PageTransition>
            </div>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
