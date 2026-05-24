import type { Metadata } from 'next';
import { Inter, Outfit } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import AuthProvider from '@/providers/AuthProvider';
import ThemeProvider from '@/providers/ThemeProvider';
import FloatingParticles from '@/components/ambient/FloatingParticles';
import WaveAnimation from '@/components/ambient/WaveAnimation';




const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const outfit = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
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
        className={`${inter.variable} ${outfit.variable} font-sans antialiased`}
        style={{
          fontFamily: 'var(--font-inter), system-ui, sans-serif',
        }}
      >
        <AuthProvider>
          <ThemeProvider>
            {/* Ambient background */}
            <FloatingParticles />
            <WaveAnimation />

            {/* Main content */}
            <div className="relative z-10 min-h-screen">{children}</div>

            {/* UncloseAI Floating Assistant */}
            <Script src="https://uncloseai.com/uncloseai.js" type="module" strategy="lazyOnload" />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
