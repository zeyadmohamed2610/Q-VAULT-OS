'use client';

import { useEffect, useRef, useState } from 'react';

// ── Feature data ─────────────────────────────────────────────
const FEATURES = [
  {
    title: 'Post-Quantum Encryption',
    body: 'ML-KEM-768 (NIST FIPS 203) provides cryptographic security resilient against quantum adversaries. Key encapsulation runs entirely on-device.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <rect x="3" y="11" width="18" height="11" rx="1" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        <circle cx="12" cy="16" r="1.5" />
      </svg>
    ),
  },
  {
    title: 'Hardware-Bound Identity',
    body: 'Every cryptographic key is permanently fused to the ESP32-S3 silicon. No key ever leaves the device. No software extraction possible.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </svg>
    ),
  },
  {
    title: 'Zero Network Exposure',
    body: 'Air-gapped by design. No WiFi. No Bluetooth. No cloud dependency. The vault operates in absolute isolation from any network surface.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <line x1="2" y1="2" x2="22" y2="22" />
        <path d="M8.5 16.5a5 5 0 0 1 7 0" opacity="0.3" />
        <path d="M5 12.5a10 10 0 0 1 5.17-2.83" opacity="0.3" />
        <path d="M19.07 12.5A10 10 0 0 0 12 10c-.57 0-1.13.05-1.67.14" opacity="0.3" />
        <path d="M2.07 9A17 17 0 0 1 12 6c2.84 0 5.5.73 7.8 2" opacity="0.3" />
        <circle cx="12" cy="20" r="1" />
      </svg>
    ),
  },
  {
    title: 'Sovereign OS Integration',
    body: 'Q-VAULT OS runs on hardened Linux with memory-safe userspace. Verified boot chain. Immutable read-only root filesystem.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <rect x="2" y="3" width="20" height="14" rx="1" />
        <path d="M8 21h8" />
        <path d="M12 17v4" />
        <path d="M7 10h2" />
        <path d="M11 10h6" />
        <path d="M7 13h10" />
      </svg>
    ),
  },
  {
    title: 'Zero-Knowledge Proofs',
    body: 'Prove identity and access rights without revealing any secret. Our ZKP layer enables sovereign authentication with mathematical guarantees.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4l3 3" />
        <path d="M8.5 8.5a5 5 0 0 1 7 0" opacity="0.5" />
      </svg>
    ),
  },
  {
    title: 'Physical Trust Anchor',
    body: 'Tamper-evident enclosure with cryptographic attestation. Physical intrusion voids the key material. The hardware IS the trust boundary.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.2} strokeLinecap="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
];

const SECURITY_ITEMS = [
  'ML-KEM-768 key encapsulation — NIST FIPS 203 compliant',
  'SL-DSA digital signatures — post-quantum authenticated',
  'AES-256-GCM symmetric encryption for data at rest',
  'BLAKE3 cryptographic hashing — hardware-accelerated',
  'Secure boot with verified chain of trust',
  'Hardware random number generator (TRNG)',
  'Anti-tamper detection with automatic key zeroization',
  'Read-only root filesystem — immutable OS image',
];

const STATS = [
  { number: '768', unit: '-bit', label: 'Quantum Security Level' },
  { number: '0', unit: '', label: 'Network Attack Surface' },
  { number: '256', unit: '-bit', label: 'Symmetric Key Strength' },
  { number: '100', unit: '%', label: 'Air-Gapped Operation' },
];

// ── Scroll reveal hook ───────────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in-view');
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

// ── Main page ────────────────────────────────────────────────
export default function Page() {
  const videoRef   = useRef<HTMLVideoElement>(null);
  const [loaded,   setLoaded]   = useState(false);
  const [ended,    setEnded]    = useState(false);
  const [textIn,   setTextIn]   = useState(false);

  useScrollReveal();

  // Fade in text after video starts playing
  useEffect(() => {
    const t = setTimeout(() => setTextIn(true), 900);
    return () => clearTimeout(t);
  }, []);

  const handleCanPlay = () => {
    setLoaded(true);
    videoRef.current?.play().catch(() => {});
  };

  const handleEnded = () => setEnded(true);

  return (
    <main>
      {/* ══════════════════════════════════════════════════════
          SECTION 1 — HERO VIDEO
         ══════════════════════════════════════════════════════ */}
      <section className="hero" aria-label="Q-VAULT cinematic introduction">

        {/* The film */}
        <video
          ref={videoRef}
          className={`hero-video${loaded ? ' loaded' : ''}`}
          src="/models/VIDEO.mp4"
          playsInline
          muted
          autoPlay
          preload="auto"
          onCanPlay={handleCanPlay}
          onEnded={handleEnded}
          aria-hidden="true"
        />

        {/* Cinematic grade overlays */}
        <div className="hero-overlay-top"  aria-hidden="true" />
        <div className="hero-overlay-bottom" aria-hidden="true" />
        <div className="hero-vignette"    aria-hidden="true" />
        <div className="hero-accent"      aria-hidden="true" />

        {/* Video-ended darkening */}
        <div className={`video-ended-overlay${ended ? ' active' : ''}`} aria-hidden="true" />

        {/* Hero copy */}
        <div className="hero-content">
          <div className={`hero-logo${textIn ? ' visible' : ''}`} aria-label="Q-VAULT">
            Q-VAULT
          </div>

          <h1 className={`hero-headline${textIn ? ' visible' : ''}`}>
            Sovereign<br /><em>Hardware</em> Security
          </h1>

          <p className={`hero-sub${textIn ? ' visible' : ''}`}>
            Post-Quantum Secure Infrastructure &nbsp;·&nbsp; Air-Gapped &nbsp;·&nbsp; Zero Compromise
          </p>

          <div className={`hero-cta-row${textIn ? ' visible' : ''}`}>
            <a href="#features" className="btn-primary">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              Enter the Vault
            </a>
            <a href="#security" className="btn-secondary">
              Security Architecture ↓
            </a>
          </div>
        </div>

        {/* Scroll hint */}
        <div className={`scroll-hint${textIn ? ' visible' : ''}`} aria-hidden="true">
          <span>Scroll</span>
          <div className="scroll-hint-line" />
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
          SECTION 2 — FEATURES
         ══════════════════════════════════════════════════════ */}
      <section id="features" style={{ background: 'var(--c-gunmetal)', padding: '0 0 var(--sp-2xl)' }}>
        <div className="section">
          <div className="reveal">
            <div className="section-label">Capabilities</div>
            <h2 className="section-title">
              Every layer<br />hardened by design.
            </h2>
            <p className="section-body">
              Q-VAULT is not software patched onto standard hardware.
              It is a ground-up sovereign cryptographic core — built for operators
              who cannot afford a single point of failure.
            </p>
          </div>

          <div className="feature-grid">
            {FEATURES.map((f, i) => (
              <div key={f.title} className={`feature-card reveal reveal-delay-${(i % 4) + 1}`}>
                <div className="feature-icon" aria-hidden="true">{f.icon}</div>
                <div className="feature-title">{f.title}</div>
                <p className="feature-body">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="divider" aria-hidden="true" />

      {/* ══════════════════════════════════════════════════════
          SECTION 3 — SECURITY ARCHITECTURE
         ══════════════════════════════════════════════════════ */}
      <section id="security">
        <div className="section">
          <div className="security-layout">
            <div className="reveal">
              <div className="section-label">Security</div>
              <h2 className="section-title">
                Quantum-proof.<br />By necessity.
              </h2>
              <p className="section-body">
                Classical cryptography is a countdown. Q-VAULT implements
                the NIST-standardized post-quantum algorithms today — because
                tomorrow&apos;s quantum threat is already being harvested now.
              </p>

              <div style={{ marginTop: '2.4rem', display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
                {['NIST FIPS 203', 'ML-KEM-768', 'SL-DSA', 'AES-256-GCM', 'BLAKE3'].map((b) => (
                  <div key={b} className="security-badge">{b}</div>
                ))}
              </div>
            </div>

            <ul className="security-list reveal reveal-delay-2">
              {SECURITY_ITEMS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          {/* Stats */}
          <div className="stat-row">
            {STATS.map((s, i) => (
              <div key={s.label} className={`stat-item reveal reveal-delay-${i + 1}`}>
                <div className="stat-number">
                  {s.number}
                  <span className="stat-unit">{s.unit}</span>
                </div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="divider" aria-hidden="true" />

      {/* ══════════════════════════════════════════════════════
          SECTION 4 — HARDWARE
         ══════════════════════════════════════════════════════ */}
      <section id="hardware" style={{ background: 'var(--c-gunmetal)' }}>
        <div className="section">
          <div className="reveal">
            <div className="section-label">Hardware</div>
            <h2 className="section-title">
              Silicon you<br />can trust.
            </h2>
          </div>

          <div className="security-layout" style={{ marginTop: 'var(--sp-xl)' }}>
            <div>
              <ul className="security-list reveal">
                {[
                  'ESP32-S3 dual-core Xtensa LX7 @ 240 MHz',
                  '8 MB PSRAM — cryptographic scratchpad',
                  'Hardware AES / SHA / RSA / ECC accelerators',
                  'True Random Number Generator (TRNG)',
                  'Secure boot ROM with eFuse key storage',
                  'Flash encryption at-rest',
                  'JTAG disabled at production fuse',
                  'Military-grade anodized enclosure',
                ].map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="reveal reveal-delay-2">
              <div style={{
                border: '1px solid var(--c-border-hi)',
                padding: '2.4rem',
                background: 'rgba(127,232,255,0.02)',
                borderRadius: '1px',
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.62rem',
                  letterSpacing: '0.22em',
                  color: 'var(--c-cyan-dim)',
                  marginBottom: '1.4rem',
                  textTransform: 'uppercase',
                }}>
                  Device Profile
                </div>

                {[
                  ['Chip',       'ESP32-S3'],
                  ['Cores',      '2× Xtensa LX7'],
                  ['Clock',      '240 MHz'],
                  ['RAM',        '512 KB + 8 MB PSRAM'],
                  ['Flash',      '16 MB encrypted'],
                  ['Crypto',     'AES / SHA / RSA / ECC'],
                  ['Network',    'DISABLED (air-gapped)'],
                  ['OS',         'Q-VAULT OS 1.0'],
                ].map(([k, v]) => (
                  <div key={k} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.65rem 0',
                    borderBottom: '1px solid var(--c-border)',
                    gap: '1rem',
                  }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--c-white-lo)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>{k}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--c-white)', textAlign: 'right' }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="divider" aria-hidden="true" />

      {/* ══════════════════════════════════════════════════════
          SECTION 5 — OS INTEGRATION
         ══════════════════════════════════════════════════════ */}
      <section id="os">
        <div className="section">
          <div className="reveal">
            <div className="section-label">OS Integration</div>
            <h2 className="section-title">
              The operating system<br />is the vault.
            </h2>
            <p className="section-body">
              Q-VAULT OS is a hardened, minimal Linux distribution purpose-built
              for cryptographic sovereignty. No package manager. No shell access.
              No attack surface beyond the defined cryptographic API.
            </p>
          </div>

          <div className="feature-grid" style={{ marginTop: 'var(--sp-xl)', gridTemplateColumns: 'repeat(auto-fill, minmax(240px,1fr))' }}>
            {[
              { title: 'Immutable Root FS',     body: 'SquashFS read-only root. No runtime modification possible. Verified on every boot.' },
              { title: 'Secure Boot Chain',     body: 'UEFI Secure Boot with custom keys. Every binary signature verified before execution.' },
              { title: 'Memory Isolation',       body: 'Address space layout randomization + mandatory access control on all processes.' },
              { title: 'Cryptographic API',      body: 'Single hardened endpoint for all cryptographic operations. No raw key material exposed.' },
            ].map((c, i) => (
              <div key={c.title} className={`feature-card reveal reveal-delay-${i + 1}`}>
                <div className="feature-title">{c.title}</div>
                <p className="feature-body">{c.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
          FOOTER
         ══════════════════════════════════════════════════════ */}
      <footer className="footer" style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div className="footer-logo">Q-VAULT</div>
        <div className="footer-copy">
          © {new Date().getFullYear()} Q-VAULT. Sovereign Hardware Security.
          Post-Quantum Certified.
        </div>
      </footer>
    </main>
  );
}
