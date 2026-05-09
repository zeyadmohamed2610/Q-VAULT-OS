'use client';

// ═══════════════════════════════════════════════════════════════
// GLOBAL LIGHTING — PHASE XXX
// Scene atmospheric base ONLY.
// Full 3-point rig now lives inside RealProductAssembly.
// This file: ambient floor + subtle scene mood color.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';

const AMBIENT: Record<number, { intensity: number; color: string }> = {
  0:  { intensity: 0.03, color: '#0a0d10' }, // VoidBoot — true black
  1:  { intensity: 0.04, color: '#080f14' }, // Perimeter scan
  2:  { intensity: 0.06, color: '#08121a' }, // Hero reveal
  3:  { intensity: 0.06, color: '#091218' }, // Exploded
  4:  { intensity: 0.05, color: '#091015' }, // PCB descent
  5:  { intensity: 0.06, color: '#08121a' }, // Seal
  6:  { intensity: 0.07, color: '#091015' }, // Assembled
  7:  { intensity: 0.05, color: '#090d12' }, // Governance
  8:  { intensity: 0.05, color: '#090d12' }, // Enclave
  9:  { intensity: 0.03, color: '#140c05' }, // Threat — amber undertone
  10: { intensity: 0.05, color: '#08111a' }, // Lifecycle
  11: { intensity: 0.04, color: '#07101a' }, // Roadmap
  12: { intensity: 0.02, color: '#050a0f' }, // Final Seal — deepest black
};

export function GlobalLighting() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const profile     = AMBIENT[activeScene] ?? AMBIENT[0];

  return (
    // Ambient ONLY — 3-point rig is in RealProductAssembly
    <ambientLight intensity={profile.intensity} color={profile.color} />
  );
}
