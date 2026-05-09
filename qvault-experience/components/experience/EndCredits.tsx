// ═══════════════════════════════════════════════════════════════
// END CREDITS
// Post-seal archival statements.
// Civilization-scale infrastructure survived.
// Ultra-slow. Sacred. Final.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect, useState } from 'react';
import { PALETTE } from '@/lib/MasteringPipeline';
import { useExperienceStore } from '@/lib/store';

const STATEMENTS = [
  { text: 'POST-QUANTUM TRUST PRESERVED.', delay: 250, size: 'text-2xl' },
  { text: 'NO PERSISTENT PLAINTEXT REMAINS.', delay: 850, size: 'text-lg' },
  { text: 'ARCHIVAL STATE: IMMUTABLE.', delay: 1450, size: 'text-lg' },
  { text: 'CRYPTOGRAPHIC LINEAGE: UNBROKEN.', delay: 2050, size: 'text-base' },
  { text: 'SOVEREIGN INFRASTRUCTURE: ENDURES.', delay: 2650, size: 'text-base' },
  { text: 'THE SEAL IS PERMANENT.', delay: 3250, size: 'text-sm' },
  { text: 'Q-VAULT', delay: 3850, size: 'text-4xl' },
];

export function EndCredits() {
  const activeScene  = useExperienceStore((s) => s.activeScene);
  const sceneProgress = useExperienceStore((s) => s.sceneProgress);
  const [active, setActive] = useState(false);
  const [visibleCount, setVisibleCount] = useState(0);
  const [creditsOpacity, setCreditsOpacity] = useState(0);

  // Trigger after the seal has established and before the loop hold.
  useEffect(() => {
    if (activeScene === 12 && sceneProgress > 0.82 && !active) {
      setActive(true);
      setCreditsOpacity(1);
    }
    if (activeScene !== 12 && active) {
      setActive(false);
      setVisibleCount(0);
      setCreditsOpacity(0);
    }
  }, [activeScene, sceneProgress, active]);

  useEffect(() => {
    if (!active) return;

    const timers = STATEMENTS.map(({ delay }, i) =>
      setTimeout(() => setVisibleCount(c => Math.max(c, i + 1)), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [active]);

  if (!active) return null;

  return (
    <div
      className="fixed inset-0 z-[190] pointer-events-none flex flex-col items-center justify-center bg-black"
      style={{
        opacity: creditsOpacity,
        transition: 'opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <div className="flex flex-col items-center gap-8 text-center px-8 max-w-2xl">
        {STATEMENTS.slice(0, visibleCount).map((stmt, i) => (
          <div
            key={i}
            className={`font-mono ${stmt.size} tracking-[0.4em] uppercase`}
            style={{
              color: i === STATEMENTS.length - 1 ? PALETTE.sovereignCyan : PALETTE.institutionalWhite,
              animation: 'fade-in-slow 0.75s cubic-bezier(0.4, 0, 0.2, 1) both',
              letterSpacing: i === STATEMENTS.length - 1 ? '0.8em' : '0.4em',
              opacity: i === STATEMENTS.length - 1 ? 0.7 : 0.2,
            }}
          >
            {stmt.text}
          </div>
        ))}
      </div>

      {/* Architectural bottom line */}
      {visibleCount >= STATEMENTS.length && (
        <div
          className="absolute bottom-12 left-0 right-0 flex justify-center"
          style={{ animation: 'fade-in-slow 3s 0.5s both' }}
        >
          <div
            className="h-px w-32"
            style={{ background: `linear-gradient(90deg, transparent, ${PALETTE.sovereignCyan}, transparent)`, opacity: 0.22 }}
          />
        </div>
      )}
    </div>
  );
}
