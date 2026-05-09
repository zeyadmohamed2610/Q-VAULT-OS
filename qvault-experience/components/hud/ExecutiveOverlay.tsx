'use client';

// ═══════════════════════════════════════════════════════════════
// EXECUTIVE OVERLAY — PHASE XXXIV: DIRECTOR'S CUT
//
// HUD philosophy:
//   - Whisper, never shout.
//   - The product owns the screen.
//   - This overlay is institutional watermark, not dashboard.
//   - Maximum opacity: 65%. Never competes with product.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { PALETTE, SCENE_ACCENT } from '@/lib/MasteringPipeline';

// Scenes where the HUD is nearly invisible (hero product shots)
// — product dominance takes absolute precedence.
const HERO_SCENES = new Set([1, 2, 7, 8, 11, 12]);

export function ExecutiveOverlay() {
  const activeScene    = useExperienceStore((s) => s.activeScene);
  const globalProgress = useExperienceStore((s) => s.globalProgress);
  const sceneConfig    = SCENE_REGISTRY[activeScene];
  const accent         = SCENE_ACCENT[activeScene] ?? PALETTE.sovereignCyan;

  // HUD fades back during hero shots so product dominates
  const hudOpacity = HERO_SCENES.has(activeScene) ? 0.35 : 0.65;

  return (
    <div
      className="fixed inset-0 z-[100] pointer-events-none select-none"
      style={{
        opacity: hudOpacity,
        transition: 'opacity 1.2s cubic-bezier(0.4,0,0.2,1)',
        fontFamily: 'var(--font-jetbrains), monospace',
        color: PALETTE.institutionalWhite,
      }}
    >
      {/* ── Top-left: Sovereign identifier ────────────────────── */}
      <div className="absolute top-8 left-10 flex flex-col gap-1">
        <span style={{
          fontSize: '0.55rem',
          letterSpacing: '0.30em',
          fontWeight: 500,
          textTransform: 'uppercase',
          opacity: 0.90,
        }}>
          Q-VAULT // SECURE CORE
        </span>
        <span style={{
          fontSize: '0.40rem',
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: PALETTE.coldSteel,
          opacity: 0.38,
        }}>
          SOVEREIGN INFRASTRUCTURE ASSET
        </span>
      </div>

      {/* ── Bottom-left: Scene label ───────────────────────────── */}
      <div className="absolute bottom-10 left-10 flex flex-col gap-1.5">
        <span style={{
          fontSize: '0.38rem',
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: PALETTE.coldSteel,
          opacity: 0.28,
        }}>
          {sceneConfig?.act?.toUpperCase() ?? 'SEQUENCE'}
        </span>
        <h1 style={{
          fontSize: '0.65rem',
          letterSpacing: '0.28em',
          fontWeight: 200,
          textTransform: 'uppercase',
          opacity: 0.85,
          margin: 0,
        }}>
          {sceneConfig?.label ?? 'INITIALIZING'}
        </h1>
      </div>

      {/* ── Bottom-right: Global progress ─────────────────────── */}
      <div className="absolute bottom-10 right-10 flex flex-col items-end gap-1">
        <span style={{
          fontSize: '0.38rem',
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: PALETTE.coldSteel,
          opacity: 0.28,
        }}>
          SYSTEM INTEGRITY
        </span>
        <span style={{
          fontSize: '0.70rem',
          letterSpacing: '0.18em',
          fontWeight: 300,
          color: accent,
          opacity: 0.85,
        }}>
          {(globalProgress * 100).toFixed(2)}%
        </span>
      </div>

      {/* ── Corner brackets — institutional frame ─────────────── */}
      <div className="absolute top-6 left-6   w-3 h-3 border-l border-t" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <div className="absolute top-6 right-6  w-3 h-3 border-r border-t" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <div className="absolute bottom-6 left-6  w-3 h-3 border-l border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <div className="absolute bottom-6 right-6 w-3 h-3 border-r border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }} />
    </div>
  );
}
