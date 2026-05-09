'use client';

// ═══════════════════════════════════════════════════════════════
// EMOTIONAL TRANSITION LAYER — PHASE OMEGA
//
// Every cut must feel PHYSICAL.
//
// Transition types:
//   STANDARD CUT:      subtle optical flash (15ms → 2.5s decay)
//   ACT CHANGE:        deep black veil (300ms darkness) + bloom reveal
//   THREAT CUT:        amber/red flash — instant, aggressive
//   THREAT→IMMORTALITY: slow blackout + deep cyan bloom (premium payoff)
//   FINAL SEAL:        gradual darkness — device fades to monument
//
// All transitions use CSS only — no Three.js overhead.
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState, useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { PALETTE, SCENE_ACCENT } from '@/lib/MasteringPipeline';

// Act boundaries (inclusive from/to)
const ACT_FIRST_SCENES = new Set([0, 4, 8, 11, 16]);
const THREAT_SCENES    = new Set([11, 12, 13, 14, 15]);

export function EmotionalTransitionLayer() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const prevScene   = useRef(-1);

  const [flash, setFlash]     = useState(0);  // Additive bloom
  const [veil, setVeil]       = useState(0);  // Black veil opacity
  const [flashColor, setFlashColor] = useState<string>(PALETTE.sovereignCyan);

  useEffect(() => {
    if (activeScene === prevScene.current) return;
    const prev = prevScene.current;
    prevScene.current = activeScene;

    const isActChange    = ACT_FIRST_SCENES.has(activeScene) && activeScene !== 0;
    const isThreatCut    = THREAT_SCENES.has(activeScene);
    const isThreatEntry  = activeScene === 11; // First threat scene
    const isImmortalEntry = activeScene === 16; // Act V begins
    const isFinalSeal    = activeScene === 18;

    const accent = SCENE_ACCENT[activeScene] ?? PALETTE.sovereignCyan;
    setFlashColor(accent);

    if (isFinalSeal) {
      // Slow fade to near-black. Device becomes monument.
      setVeil(0.65);
      setFlash(0);
      setTimeout(() => setVeil(0.30), 2000);
      setTimeout(() => setVeil(0),    5000);

    } else if (isImmortalEntry) {
      // Act IV → V: deep dramatic blackout + sovereign cyan reveal
      setVeil(1);
      setFlash(0);
      setTimeout(() => {
        setVeil(0);
        setFlashColor(PALETTE.sovereignCyan);
        setFlash(0.70);
        setTimeout(() => setFlash(0), 80);
      }, 800);

    } else if (isThreatEntry) {
      // First threat scene: amber slam + fast veil
      setVeil(0.95);
      setFlash(0);
      setFlashColor(PALETTE.burntAmber);
      setTimeout(() => {
        setVeil(0);
        setFlash(0.90);
        setTimeout(() => setFlash(0), 60);
      }, 180);

    } else if (isThreatCut) {
      // Rapid threat cuts: instant flash, no veil needed
      const color = activeScene % 2 === 0 ? PALETTE.emergencyRed : PALETTE.burntAmber;
      setFlashColor(color);
      setFlash(0.75);
      setTimeout(() => setFlash(0), 40);

    } else if (isActChange) {
      // Normal act changes: elegant veil + bloom
      setVeil(1);
      setFlash(0);
      setTimeout(() => {
        setVeil(0);
        setFlash(0.60);
        setTimeout(() => setFlash(0), 80);
      }, 500);

    } else {
      // Standard scene cut: subtle optical flash
      setFlash(0.45);
      setTimeout(() => setFlash(0), 30);
    }

    void prev;
  }, [activeScene]);

  return (
    <>
      {/* ── Optical Bloom — additive color ── */}
      <div
        className="fixed inset-0 z-50 pointer-events-none mix-blend-screen"
        style={{
          backgroundColor: flashColor,
          opacity: flash,
          transition: flash > 0 ? 'none' : 'opacity 2.8s cubic-bezier(0.1, 0.8, 0.2, 1)',
        }}
      />

      {/* ── Psychological Darkness Veil ── */}
      <div
        className="fixed inset-0 z-[60] pointer-events-none bg-black"
        style={{
          opacity: veil,
          transition: veil > 0
            ? 'opacity 0.25s ease-out'
            : 'opacity 1.8s cubic-bezier(0.2, 0.6, 0.2, 1)',
        }}
      />
    </>
  );
}
