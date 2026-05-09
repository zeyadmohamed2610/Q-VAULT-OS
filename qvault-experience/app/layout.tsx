import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://qvault.dev'),
  title: 'Q-VAULT | Sovereign Infrastructure Film',
  description:
    'A deterministic cinematic record of post-quantum trust architecture. Autonomous playback of the civilizational infrastructure preservation sequence.',
  keywords: [
    'post-quantum cryptography',
    'sovereign film',
    'ML-KEM-768',
    'infrastructure documentary',
    'NIST FIPS 203',
    'archival record',
    'cryptographic continuity',
  ],
  authors: [{ name: 'Q-VAULT AUTHORITY' }],
  creator: 'Q-VAULT AUTHORITY',
  openGraph: {
    title: 'Q-VAULT — Sovereign Infrastructure Film',
    description:
      'The definitive cinematic record of post-quantum trust preservation. Autonomous playback mode.',
    type: 'video.movie',
    locale: 'en_US',
    images: [
      {
        url: '/og-preview.jpg',
        width: 1200,
        height: 630,
        alt: 'Q-VAULT — Sovereign Infrastructure Film',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Q-VAULT | Sovereign Infrastructure Film',
    description: 'Autonomous cinematic record of post-quantum trust.',
    images: ['/og-preview.jpg'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export function generateViewport() {
  return {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  };
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <meta name="theme-color" content="#000000" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body>{children}</body>
    </html>
  );
}
