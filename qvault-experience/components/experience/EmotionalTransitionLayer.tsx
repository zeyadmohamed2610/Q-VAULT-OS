// ═══════════════════════════════════════════════════════════════
// EMOTIONAL TRANSITION LAYER
// Act-based black screens, cinematic sweeps, and optical blooms
// to bridge scenes with psychological weight.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect, useState, useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { PALETTE, SCENE_ACCENT } from '@/lib/MasteringPipeline';

export function EmotionalTransitionLayer() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const prevScene = useRef(activeScene);
  
  // Cinematic transition states
  const [flash, setFlash] = useState(0); // Additive white/cyan bloom
  const [veil, setVeil] = useState(0);   // Subtractive black crush
  
  const targetColor = useRef<string>(PALETTE.sovereignCyan);

  useEffect(() => {
    if (activeScene === prevScene.current) return;
    
    // Determine emotional weight of transition
    const prev = prevScene.current;
    const isActChange = (prev <= 2 && activeScene > 2) || 
                        (prev <= 6 && activeScene > 6) || 
                        (prev <= 9 && activeScene > 9);
    
    targetColor.current = SCENE_ACCENT[activeScene] ?? PALETTE.institutionalWhite;

    if (isActChange) {
      // Act changes get a deep black veil followed by a bloom reveal
      setVeil(1);
      setFlash(0);
      
      setTimeout(() => {
        setVeil(0);
        setFlash(0.8);
        setTimeout(() => setFlash(0), 100);
      }, 1200); // 1.2s of darkness
    } else {
      // Standard scene cuts get a subtle optical flash
      setFlash(0.6);
      setTimeout(() => setFlash(0), 50);
    }

    prevScene.current = activeScene;
  }, [activeScene]);

  return (
    <>
      {/* ── Cinematic Optical Bloom ── */}
      <div 
        className="fixed inset-0 z-50 pointer-events-none mix-blend-screen"
        style={{
          backgroundColor: targetColor.current,
          opacity: flash,
          transition: flash > 0 ? 'none' : 'opacity 2.5s cubic-bezier(0.2, 0.8, 0.2, 1)',
        }}
      />
      
      {/* ── Psychological Darkness Veil ── */}
      <div 
        className="fixed inset-0 z-[60] pointer-events-none bg-black"
        style={{
          opacity: veil,
          transition: veil > 0 ? 'opacity 0.3s ease-out' : 'opacity 1.5s ease-in',
        }}
      />
    </>
  );
}
