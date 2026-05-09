// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Scanline Overlay
// CSS-based CRT scanline effect for Scene 0.
//
// Design: Classified military hardware display, NOT retro arcade.
// Two layers:
//   1. Static scanline grid — subtle repeating gradient
//   2. Moving scan bar — a bright horizontal sweep
//
// Intensity is driven by scroll progress via the store.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useEffect } from 'react';
import { useExperienceStore } from '@/lib/store';

export function ScanlineOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const scanbarRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number>(0);

  // Only active during Scene 0
  const isActive = activeScene === 0;

  // Animate the scan bar independently for smooth motion
  useEffect(() => {
    if (!isActive) return;

    const animate = () => {
      if (scanbarRef.current) {
        const t = performance.now() * 0.0008;
        const y = ((Math.sin(t) * 0.5 + 0.5) * 100);
        scanbarRef.current.style.top = `${y}%`;
      }
      frameRef.current = requestAnimationFrame(animate);
    };

    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [isActive]);

  if (!isActive) return null;

  // Scanline intensity ramps up through the scene, peaks near end
  const baseIntensity = 0.015 + progress * 0.03;
  const peakIntensity = progress > 0.88 ? (progress - 0.88) / 0.12 * 0.08 : 0;
  const intensity = baseIntensity + peakIntensity;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 11,
        mixBlendMode: 'screen',
      }}
    >
      {/* Static scanline grid */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(0, 230, 255, ${intensity}) 2px,
            rgba(0, 230, 255, ${intensity}) 3px
          )`,
          opacity: 0.6,
        }}
      />

      {/* Moving scan bar */}
      <div
        ref={scanbarRef}
        style={{
          position: 'absolute',
          left: 0,
          width: '100%',
          height: '2px',
          background: `linear-gradient(
            90deg,
            transparent 0%,
            rgba(0, 230, 255, ${0.06 + progress * 0.1}) 20%,
            rgba(0, 230, 255, ${0.12 + progress * 0.15}) 50%,
            rgba(0, 230, 255, ${0.06 + progress * 0.1}) 80%,
            transparent 100%
          )`,
          boxShadow: `0 0 12px rgba(0, 230, 255, ${0.05 + progress * 0.08})`,
          transition: 'none',
        }}
      />

      {/* Subtle horizontal noise lines (static interference) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `repeating-linear-gradient(
            0deg,
            transparent,
            transparent 4px,
            rgba(0, 180, 220, ${intensity * 0.3}) 4px,
            transparent 5px
          )`,
          opacity: 0.3,
          animation: isActive ? 'scanlineShift 8s linear infinite' : 'none',
        }}
      />
    </div>
  );
}
