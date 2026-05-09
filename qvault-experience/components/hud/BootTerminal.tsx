// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Boot Terminal
// Tactical monospace boot text overlay for Scene 0.
// Each line fades in with slight upward motion and opacity flicker,
// synced to scroll progress via the Zustand store.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useMemo } from 'react';
import { useExperienceStore } from '@/lib/store';

const BOOT_LINES = [
  { text: 'INITIALIZING Q-VAULT CORE...', start: 0.45, end: 0.52, status: 'process' },
  { text: 'LOADING CRYPTOGRAPHIC RUNTIME...', start: 0.52, end: 0.58, status: 'process' },
  { text: 'MOUNTING SECURE SANDBOX...', start: 0.58, end: 0.64, status: 'process' },
  { text: 'ESTABLISHING HARDWARE TRUST...', start: 0.64, end: 0.70, status: 'process' },
  { text: 'ML-KEM-768', start: 0.70, end: 0.77, status: 'ready' },
  { text: 'AES-256-GCM', start: 0.77, end: 0.83, status: 'ready' },
  { text: 'SYSTEM READY', start: 0.83, end: 0.90, status: 'complete' },
] as const;

type LineStatus = 'process' | 'ready' | 'complete';

function getStatusPrefix(status: LineStatus, isComplete: boolean): string {
  if (status === 'ready') return isComplete ? '[ ✓ ]' : '[ · ]';
  if (status === 'complete') return isComplete ? '[ ✓ ]' : '[ · ]';
  return isComplete ? '[ OK ]' : '[ .... ]';
}

function getStatusColor(status: LineStatus, isComplete: boolean): string {
  if (!isComplete) return 'var(--text-muted)';
  if (status === 'ready') return 'var(--success)';
  if (status === 'complete') return 'var(--cyan-bright)';
  return 'var(--cyan-dim)';
}

export function BootTerminal() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Only render during Scene 0
  if (activeScene !== 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '8vh',
        left: '50%',
        transform: 'translateX(-50%)',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        letterSpacing: '0.08em',
        lineHeight: '2.2',
        textTransform: 'uppercase',
        pointerEvents: 'none',
        userSelect: 'none',
        zIndex: 12,
        width: 'max-content',
        maxWidth: '90vw',
      }}
    >
      {BOOT_LINES.map((line, i) => {
        const lineProgress = Math.max(0, Math.min(1, (progress - line.start) / (line.end - line.start)));
        const isVisible = progress >= line.start;
        const isComplete = progress >= line.end;

        if (!isVisible) return null;

        // Flicker effect: opacity oscillates slightly during materialization
        const flicker = isComplete ? 1 : 0.7 + Math.sin(lineProgress * Math.PI * 4) * 0.15;
        const translateY = isComplete ? 0 : (1 - lineProgress) * 8;

        return (
          <div
            key={i}
            style={{
              opacity: lineProgress * flicker,
              transform: `translateY(${translateY}px)`,
              transition: 'none',
              color: getStatusColor(line.status, isComplete),
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{ color: 'var(--steel)', marginRight: '8px' }}>
              {getStatusPrefix(line.status, isComplete)}
            </span>
            {line.text}
          </div>
        );
      })}
    </div>
  );
}
