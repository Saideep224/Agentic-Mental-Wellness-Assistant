import type { Metadata } from 'next';
import { Inter, Space_Grotesk } from 'next/font/google';
import Script from 'next/script';
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
  title: 'Esona - Your Supporting Buddie',
  description:
    'An emotionally adaptive AI that truly understands you — your moods, your words, your silence. Esona is a multi-agent mental wellness chatbot that grows with you.',
  keywords: ['mental health', 'AI chatbot', 'emotional support', 'wellness', 'therapy'],
  authors: [{ name: 'Esona Team' }],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
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
