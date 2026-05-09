// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Iris Transition
// Expanding cyan ring that reveals Scene 1 at the end of Scene 0.
//
// Fires at progress > 0.88.
// A circle mask grows from center until the viewport is fully open.
// Feels like: "ACCESS GRANTED — entering classified threat space."
// ═══════════════════════════════════════════════════════════════

'use client';

import { useExperienceStore } from '@/lib/store';

export function IrisTransition() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Only activate during Scene 0 end phase
  if (activeScene !== 0 || progress < 0.85) return null;

  // Map 0.85-1.0 to 0-1 iris opening
  const irisProgress = Math.max(0, Math.min(1, (progress - 0.85) / 0.15));

  // Circle radius: starts small, expands to cover viewport diagonal
  // viewport diagonal ≈ 150vmax is safe
  const radius = irisProgress * 150;

  // Ring glow intensity
  const glowOpacity = irisProgress < 0.5
    ? irisProgress * 2    // Fade in
    : 2 - irisProgress * 2; // Fade out as it covers everything

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 15,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Iris ring */}
      <div
        style={{
          width: `${radius}vmax`,
          height: `${radius}vmax`,
          borderRadius: '50%',
          border: `2px solid rgba(0, 230, 255, ${glowOpacity * 0.6})`,
          boxShadow: `
            0 0 30px rgba(0, 230, 255, ${glowOpacity * 0.3}),
            0 0 60px rgba(0, 230, 255, ${glowOpacity * 0.15}),
            inset 0 0 30px rgba(0, 230, 255, ${glowOpacity * 0.1})
          `,
          transition: 'none',
        }}
      />

      {/* "ACCESS GRANTED" text appears briefly */}
      {irisProgress > 0.3 && irisProgress < 0.85 && (
        <div
          style={{
            position: 'absolute',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            letterSpacing: '0.3em',
            textTransform: 'uppercase',
            color: 'var(--cyan)',
            opacity: Math.min(1, (irisProgress - 0.3) * 3) * Math.max(0, 1 - (irisProgress - 0.6) * 4),
            userSelect: 'none',
          }}
        >
          ACCESS GRANTED
        </div>
      )}
    </div>
  );
}
