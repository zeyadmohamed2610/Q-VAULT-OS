'use client';

// ═══════════════════════════════════════════════════════════════
// POST FX — PHASE XXXI: COMMERCIAL MASTERING
//
// Bloom:   optical diffusion only (low intensity, high threshold)
// DOF:     subtle macro realism — hardware always in focus
// Vignette: cinematic frame, collapses to blackout on ACT V seal
// Tone:    ACES filmic is set on Canvas gl config (ExperienceLayout)
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState } from 'react';
import { useThree } from '@react-three/fiber';
import {
  EffectComposer,
  Bloom,
  DepthOfField,
  Vignette,
} from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import { useExperienceStore } from '@/lib/store';
import { transitionDirector } from '@/lib/TransitionDirector';

export function PostFX() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);
  const camera      = useThree((s) => s.camera);

  const [td, setTd] = useState(() => transitionDirector.state);
  useEffect(() => { const unsub = transitionDirector.subscribe(setTd); return () => { unsub(); }; }, []);

  // ── DOF — focus on product at world z=0 ─────────────────────
  // At z=6, far=200: focusDist = 6/200 = 0.03 (well-focused on product)
  const camZ      = camera.position.z;
  const focusDist = Math.max(0.01, camZ / 200);

  // ACT I macro: slightly wider DOF for silhouette look
  // ACT II reveal: tightest DOF for premium macro feel
  // ACT V seal: very tight, pulls into isolation
  const focalLen = activeScene <= 1 ? 0.010
    : activeScene <= 4 ? 0.020
    : activeScene === 12 ? 0.028
    : 0.016;

  // ── Vignette — frames the product, deepens on final seal ─────
  const isSeal = activeScene === 12;
  const vigOff  = Math.max(0.08, isSeal ? 0.42 - progress * 0.36 : td.vignetteOffset);
  const vigDark = Math.min(0.95, isSeal ? 0.45 + progress * 0.50 : td.vignetteDarkness);

  // ── Bloom — optical diffusion, never gamer-neon ──────────────
  // Threshold 0.85+: only the brightest metallic highlights bloom
  // Intensity 0.18: subtle halo, not a glow effect
  const bloomInt  = Math.min(0.20, td.bloomIntensity * 0.65);
  const bloomThr  = Math.max(0.84, td.bloomThreshold);

  return (
    <EffectComposer multisampling={4}>
      {/* Depth of field — macro realism, never blurs product */}
      <DepthOfField
        focusDistance={focusDist}
        focalLength={focalLen}
        bokehScale={activeScene <= 1 ? 0.8 : 1.6}
        height={720}
      />

      {/* Bloom — optical specular diffusion only */}
      <Bloom
        blendFunction={BlendFunction.ADD}
        intensity={bloomInt}
        luminanceThreshold={bloomThr}
        luminanceSmoothing={0.75}
        mipmapBlur
        levels={7}
        radius={0.60}
      />

      {/* Vignette — cinematic frame shaping */}
      <Vignette
        eskil={false}
        offset={vigOff}
        darkness={vigDark}
      />
    </EffectComposer>
  );
}
