// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Scroll Progress Bar
// Vertical cyan bar on right edge showing global progress
// ═══════════════════════════════════════════════════════════════

'use client';

import { useExperienceStore } from '@/lib/store';

export function ScrollProgress() {
  const progress = useExperienceStore((s) => s.globalProgress);

  return (
    <div
      className="fixed right-3 top-1/2 -translate-y-1/2 w-[2px] select-none"
      style={{
        height: '30vh',
        background: 'var(--steel)',
        opacity: 0.2,
        borderRadius: '1px',
      }}
    >
      <div
        className="w-full rounded-full transition-all"
        style={{
          height: `${progress * 100}%`,
          background: 'var(--cyan)',
          boxShadow: 'var(--glow-cyan)',
          transitionDuration: 'var(--motion-instant)',
        }}
      />
    </div>
  );
}
