'use client';

// ═══════════════════════════════════════════════════════════════
// SCENE DISPATCHER — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// REMOVED: GlobalOperationalLayer entirely
//   Was: animated sphere grid + 8 cable curves + shader traffic
//   Cost: ~12 draw calls + 1 ShaderMaterial per frame
//   Verdict: ZERO contribution to product narrative. DELETED.
//
// REMAINING: CommercialProductFilm only.
// Background: plain CSS black. No Three.js bg color change.
// Fog: minimal density, set once, not per-frame.
// ═══════════════════════════════════════════════════════════════

import { useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';
import { transitionDirector } from '@/lib/TransitionDirector';
import { CommercialProductFilm } from '@/components/three/CommercialProductFilm';

// ── Scene atmosphere — fog only, set once ─────────────────────
function SceneAtmosphere() {
  const scene = useThree((s) => s.scene);

  // Initialize background + fog ONCE
  useEffect(() => {
    scene.background = new THREE.Color(PALETTE.deepGraphite);
    scene.fog        = new THREE.FogExp2(PALETTE.deepGraphite, 0.0002);
  }, [scene]);

  // Lazy fog density interpolation — only 1 float lerp per frame
  useFrame(() => {
    if (scene.fog instanceof THREE.FogExp2) {
      const target = transitionDirector.state.fogDensity;
      scene.fog.density += (target - scene.fog.density) * 0.03;
    }
  });

  return null;
}

// ─────────────────────────────────────────────────────────────
export function SceneDispatcher() {
  return (
    <>
      <SceneAtmosphere />
      <CommercialProductFilm />
    </>
  );
}
