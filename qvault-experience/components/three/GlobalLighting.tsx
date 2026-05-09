'use client';

// ═══════════════════════════════════════════════════════════════
// GLOBAL LIGHTING — PHASE XL
// Scene atmospheric base ONLY. Ambient floor + mood color.
// 3-point rig lives entirely inside CommercialProductFilm.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';

const AMBIENT: Record<number, { intensity: number; color: string }> = {
  0: { intensity: 0.02, color: '#050810' },
  1: { intensity: 0.04, color: '#080e18' },
  2: { intensity: 0.05, color: '#080e18' },
  3: { intensity: 0.05, color: '#081018' },
  4: { intensity: 0.05, color: '#081018' },
  5: { intensity: 0.06, color: '#090f1a' },
  6: { intensity: 0.05, color: '#080f18' },
  7: { intensity: 0.05, color: '#080e16' },
  8: { intensity: 0.04, color: '#080d15' },
  9: { intensity: 0.02, color: '#05080f' },
};

export function GlobalLighting() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const profile     = AMBIENT[activeScene] ?? AMBIENT[0];
  return <ambientLight intensity={profile.intensity} color={profile.color} />;
}
