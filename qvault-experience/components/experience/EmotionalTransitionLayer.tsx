'use client';

// ═══════════════════════════════════════════════════════════════
// EMOTIONAL TRANSITION LAYER — PHASE XL: PERFORMANCE
//
// 3 transition types only (was 6 in OMEGA).
// Simpler logic = fewer setTimeout chains = less GC.
//
//   ACT CHANGE: black veil (400ms) + cyan bloom
//   STANDARD:   subtle optical flash (25ms decay)
//   FINAL SEAL: slow fade to deep dark (monument)
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState, useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { PALETTE, SCENE_ACCENT } from '@/lib/MasteringPipeline';

const ACT_STARTS = new Set([1, 2, 5, 6, 8, 9]);

export function EmotionalTransitionLayer() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const prevScene   = useRef(-1);
  const [flash, setFlash]           = useState(0);
  const [veil, setVeil]             = useState(0);
  const [flashColor, setFlashColor] = useState<string>(PALETTE.sovereignCyan);

  useEffect(() => {
    if (activeScene === prevScene.current) return;
    prevScene.current = activeScene;

    const isActStart = ACT_STARTS.has(activeScene);
    const isFinal    = activeScene === 9;
    const accent     = SCENE_ACCENT[activeScene] ?? PALETTE.sovereignCyan;
    setFlashColor(accent);

    if (isFinal) {
      // Monument: slow fade to 50% darkness, then recover slightly
      setVeil(0.55);
      setTimeout(() => setVeil(0.20), 1800);
      setTimeout(() => setVeil(0),    5000);

    } else if (isActStart) {
      // Act change: elegant black sweep + bloom
      setVeil(1);
      setFlash(0);
      setTimeout(() => {
        setVeil(0);
        setFlash(0.55);
        setTimeout(() => setFlash(0), 60);
      }, 400);

    } else {
      // Standard cut: optical flash, 25ms then fade 2.5s
      setFlash(0.40);
      setTimeout(() => setFlash(0), 25);
    }
  }, [activeScene]);

  return (
    <>
      {/* Optical bloom */}
      <div
        className="fixed inset-0 z-50 pointer-events-none mix-blend-screen"
        style={{
          backgroundColor: flashColor,
          opacity: flash,
          transition: flash > 0 ? 'none' : 'opacity 2.5s cubic-bezier(0.1,0.8,0.2,1)',
        }}
      />
      {/* Darkness veil */}
      <div
        className="fixed inset-0 z-[60] pointer-events-none bg-black"
        style={{
          opacity: veil,
          transition: veil > 0 ? 'opacity 0.3s ease-out' : 'opacity 1.8s ease-in',
        }}
      />
    </>
  );
}
