import type { Metadata } from 'next';
import { Inter, Space_Grotesk, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
  weight: ['300', '400'],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://qvault.dev'),
  title: 'Q-VAULT — Sovereign Hardware Security',
  description:
    'Post-quantum secure infrastructure. Hardware-bound identity. Zero network. Zero compromise. The sovereign cryptographic core.',
  keywords: [
    'post-quantum cryptography',
    'sovereign hardware security',
    'ML-KEM-768',
    'hardware security module',
    'ESP32-S3',
    'air-gapped security',
    'zero-knowledge proofs',
    'NIST FIPS 203',
  ],
  authors: [{ name: 'Q-VAULT' }],
  creator: 'Q-VAULT',
  openGraph: {
    title: 'Q-VAULT — Sovereign Hardware Security',
    description: 'Post-quantum secure infrastructure. Hardware-bound identity. Zero network.',
    type: 'website',
    locale: 'en_US',
    images: [{ url: '/og-preview.jpg', width: 1200, height: 630, alt: 'Q-VAULT' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Q-VAULT | Sovereign Hardware Security',
    description: 'Post-quantum secure infrastructure.',
    images: ['/og-preview.jpg'],
  },
  robots: { index: true, follow: true },
};

export function generateViewport() {
  return { width: 'device-width', initialScale: 1, maximumScale: 5 };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable}`}>
      <head>
        <meta name="theme-color" content="#000000" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body>{children}</body>
    </html>
  );
}
