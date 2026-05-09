'use client';

// ═══════════════════════════════════════════════════════════════
// SCENE DISPATCHER — PHASE OMEGA: CINEMATIC REBIRTH
//
// Architecture: Product is the ONLY hero. Everything else is atmosphere.
//   CommercialProductFilm — always mounted (handles own visibility)
//   GlobalOperationalLayer — shown ONLY in Act III (scenes 8-10)
//   Background + fog driven by TransitionDirector
// ═══════════════════════════════════════════════════════════════

import { useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { transitionDirector } from '@/lib/TransitionDirector';
import { PALETTE } from '@/lib/MasteringPipeline';
import { CommercialProductFilm } from '@/components/three/CommercialProductFilm';
import { GlobalOperationalLayer } from '@/components/three/GlobalOperationalLayer';

// ── Scene atmosphere — background + fog only ──────────────────
function SceneAtmosphere() {
  const scene       = useThree((s) => s.scene);
  const activeScene = useExperienceStore((s) => s.activeScene);

  useEffect(() => {
    // Threat scenes: very slight reddish tint to void
    const isThreat = activeScene >= 11 && activeScene <= 15;
    const bg = isThreat ? '#060402' : PALETTE.deepGraphite;
    scene.background = new THREE.Color(bg);
    scene.fog = new THREE.FogExp2(bg, 0.0002);
  }, [scene, activeScene]);

  useFrame(() => {
    if (scene.fog instanceof THREE.FogExp2) {
      const target = transitionDirector.state.fogDensity;
      scene.fog.density += (target - scene.fog.density) * 0.035;
    }
  });

  return null;
}

// ─────────────────────────────────────────────────────────────
export function SceneDispatcher() {
  const activeScene = useExperienceStore((s) => s.activeScene);

  // GlobalOperationalLayer only in Act III (reveal scenes 8-10)
  // Far back at z=-24 — NEVER competes with hero product
  const showGlobal = activeScene >= 8 && activeScene <= 10;

  return (
    <>
      <SceneAtmosphere />

      {/* ══ HERO — ALWAYS MOUNTED ════════════════════════════ */}
      <CommercialProductFilm />

      {/* ══ ATMOSPHERE — ACT III ONLY ════════════════════════ */}
      {showGlobal && (
        <GlobalOperationalLayer
          position={[0, 0, -24]}
          scale={1.5}
        />
      )}
    </>
  );
}
