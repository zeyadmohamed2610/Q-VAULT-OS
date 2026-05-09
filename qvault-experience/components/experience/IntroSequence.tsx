'use client';

import { useEffect, useRef, useState } from 'react';
import { PALETTE } from '@/lib/MasteringPipeline';

const BOOT_LINES = [
  { delay: 160, text: 'QVAULT::KERNEL v4.1.0-sovereign' },
  { delay: 340, text: 'ENTROPY_SOURCE........... /dev/qrng0' },
  { delay: 520, text: 'ATTESTATION_ROOT......... verified' },
  { delay: 700, text: 'HW_VERIFICATION.......... NIST_PQC_COMPLIANT' },
  { delay: 920, text: 'HSM_BIND................. LOCKED' },
  { delay: 1160, text: 'TRUST_ANCHOR............. ESTABLISHED' },
  { delay: 1440, text: 'INITIALIZING CRYPTOGRAPHIC SUBSYSTEM...' },
];

interface IntroSequenceProps {
  onComplete: () => void;
}

export function IntroSequence({ onComplete }: IntroSequenceProps) {
  const [phase, setPhase] = useState<'boot' | 'logo' | 'fade' | 'done'>('boot');
  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);
  const completed = useRef(false);

  useEffect(() => {
    const timers = timerRefs.current;

    BOOT_LINES.forEach(({ delay, text }) => {
      timers.push(setTimeout(() => setVisibleLines((prev) => [...prev, text]), delay));
    });

    timers.push(setTimeout(() => setPhase('logo'), 1650));
    timers.push(setTimeout(() => setPhase('fade'), 2350));
    timers.push(
      setTimeout(() => {
        setPhase('done');
        if (!completed.current) {
          completed.current = true;
          onComplete();
        }
      }, 3250)
    );

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  if (phase === 'done') return null;

  const logoVisible = phase === 'logo' || phase === 'fade';
  const fading = phase === 'fade';

  return (
    <div
      className="fixed inset-0 z-[190] pointer-events-none flex flex-col items-center justify-center bg-black"
      style={{
        opacity: fading ? 0 : 1,
        transition: 'opacity 1.1s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(245,247,250,0.018) 2px, rgba(245,247,250,0.018) 4px)',
          opacity: phase === 'boot' ? 0.28 : 0,
          transition: 'opacity 0.25s',
        }}
      />

      <div
        className="absolute left-12 bottom-24 md:left-16 md:bottom-28 font-mono text-[10px] md:text-xs tracking-widest"
        style={{ opacity: phase === 'boot' ? 1 : 0, transition: 'opacity 0.35s', color: PALETTE.coldSteel }}
      >
        {visibleLines.map((line, i) => (
          <div
            key={`boot-line-${i}`}
            style={{
              animation: 'fade-in-slow 0.45s cubic-bezier(0.4, 0, 0.2, 1) both',
              letterSpacing: i === BOOT_LINES.length - 1 ? '0.45em' : '0.22em',
              opacity: i === BOOT_LINES.length - 1 ? 0.78 : 0.38,
            }}
          >
            {line}
          </div>
        ))}
      </div>

      <div
        className="flex flex-col items-center gap-3"
        style={{
          opacity: logoVisible ? 1 : 0,
          transform: logoVisible ? 'translateY(0)' : 'translateY(8px)',
          transition:
            'opacity 0.7s cubic-bezier(0.4, 0, 0.2, 1), transform 0.7s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <div className="font-mono text-4xl md:text-5xl tracking-[0.9em] font-extralight" style={{ color: PALETTE.institutionalWhite }}>
          Q-VAULT
        </div>
        <div className="font-mono text-[10px] tracking-[0.45em] uppercase mt-2" style={{ color: PALETTE.sovereignCyan, opacity: 0.32 }}>
          SOVEREIGN INFRASTRUCTURE AUTHORITY
        </div>
      </div>

      <div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent, ${PALETTE.sovereignCyan}, transparent)`,
          opacity: logoVisible ? 0.45 : 0,
          transition: 'opacity 0.7s 0.2s',
        }}
      />
    </div>
  );
}
