'use client';

// ═══════════════════════════════════════════════════════════════
// SCENE DISPATCHER — PHASE XXXI: COMMERCIAL PRODUCT FILM
//
// PHILOSOPHY: The product IS the scene. Scene components are
// subordinate atmosphere only — they may not overpower the hero.
//
// Architecture:
//  1. CommercialProductFilm — always mounted, handles all product
//  2. SceneAtmosphere — background color/fog only
//  3. Scene components — disabled by default; only minimal atmosphere
//     components are permitted on a per-scene basis.
// ═══════════════════════════════════════════════════════════════

import { useEffect, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { transitionDirector } from '@/lib/TransitionDirector';
import { PALETTE } from '@/lib/MasteringPipeline';
import { CommercialProductFilm } from '@/components/three/CommercialProductFilm';
import { GlobalOperationalLayer } from '@/components/three/GlobalOperationalLayer';

// ── Scene atmosphere (background + fog only) ───────────────────
function SceneAtmosphere() {
  const scene       = useThree((s) => s.scene);
  const activeScene = useExperienceStore((s) => s.activeScene);

  useEffect(() => {
    scene.background = new THREE.Color(PALETTE.deepGraphite);
    scene.fog = new THREE.FogExp2(PALETTE.deepGraphite, 0.0002);
  }, [scene]);

  useFrame(() => {
    if (scene.fog instanceof THREE.FogExp2) {
      const target = transitionDirector.state.fogDensity;
      scene.fog.density += (target - scene.fog.density) * 0.04;
    }
  });

  void activeScene;
  return null;
}

// ─────────────────────────────────────────────────────────────
export function SceneDispatcher() {
  const activeScene = useExperienceStore((s) => s.activeScene);

  // GlobalOperationalLayer only shown in ACT III scenes (6-8: THE SYSTEM)
  // Positioned at z=-22 — never competes with product hero at z=0
  const showGlobal = activeScene >= 6 && activeScene <= 8;

  return (
    <>
      <SceneAtmosphere />

      {/* ══ HERO — ALWAYS MOUNTED ══════════════════════════════ */}
      {/* CommercialProductFilm owns all product rendering.       */}
      {/* It handles its own visibility per scene (scene 0: hidden) */}
      <CommercialProductFilm />

      {/* ══ ATMOSPHERE — ACT III ONLY ══════════════════════════ */}
      {/* GlobalOperationalLayer: far background, 50% dimmer than Phase XXX */}
      {/* Positioned at z=-22 so it NEVER competes with product.  */}
      {showGlobal && (
        <GlobalOperationalLayer
          position={[0, 0, -22]}
          scale={1.4}
        />
      )}
    </>
  );
}
