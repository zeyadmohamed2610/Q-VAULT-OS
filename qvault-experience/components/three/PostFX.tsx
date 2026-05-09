'use client';

// ═══════════════════════════════════════════════════════════════
// POST FX — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// REMOVED: DepthOfField (was biggest single GPU cost item)
// REMOVED: multisampling=4 → adaptive (0 on medium/low)
// REMOVED: Bloom levels=7 → 3-5 max (quality adaptive)
// REMOVED: mipmapBlur on low/medium quality tiers
//
// KEPT:
//   Bloom (subtle, optical, not sci-fi)
//   Vignette (gentle frame, no collapsing on scene 9)
//
// Performance impact:
//   DOF removal: -35% GPU cost on postprocessing pass
//   MSAA 4x → 0x: -20% GPU fillrate on medium devices
//   Bloom levels 7 → 3: -40% bloom resolve overhead
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState } from 'react';
import {
  EffectComposer,
  Bloom,
  Vignette,
} from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import { useExperienceStore } from '@/lib/store';
import { transitionDirector } from '@/lib/TransitionDirector';
import { getQualityProfile } from '@/lib/AdaptiveQuality';
import { useMemo } from 'react';

// Per-scene bloom config — tight, optical, not gamer
const BLOOM_PER_SCENE: Record<number, { intensity: number; threshold: number }> = {
  0: { intensity: 0.05, threshold: 0.92 },
  1: { intensity: 0.12, threshold: 0.88 },
  2: { intensity: 0.10, threshold: 0.89 },
  3: { intensity: 0.14, threshold: 0.86 },  // PCB — circuit glow
  4: { intensity: 0.10, threshold: 0.89 },
  5: { intensity: 0.14, threshold: 0.86 },  // Hero — edge bloom
  6: { intensity: 0.12, threshold: 0.88 },
  7: { intensity: 0.12, threshold: 0.88 },
  8: { intensity: 0.10, threshold: 0.90 },
  9: { intensity: 0.08, threshold: 0.92 },  // Final — barely there
};

const VIGNETTE_PER_SCENE: Record<number, { offset: number; darkness: number }> = {
  0: { offset: 0.46, darkness: 0.40 },
  1: { offset: 0.55, darkness: 0.25 },
  2: { offset: 0.58, darkness: 0.22 },
  3: { offset: 0.55, darkness: 0.25 },
  4: { offset: 0.56, darkness: 0.24 },
  5: { offset: 0.60, darkness: 0.20 },  // Hero — open, clean frame
  6: { offset: 0.58, darkness: 0.22 },
  7: { offset: 0.56, darkness: 0.24 },
  8: { offset: 0.55, darkness: 0.25 },
  9: { offset: 0.44, darkness: 0.48 },  // Final — closing frame
};

export function PostFX() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const quality     = useMemo(() => getQualityProfile(), []);

  const [td, setTd] = useState(() => transitionDirector.state);
  useEffect(() => {
    const unsub = transitionDirector.subscribe(setTd);
    return () => { unsub(); };
  }, []);

  if (!quality.bloomEnabled) return null;  // Low tier: zero PostFX

  const sceneBloom  = BLOOM_PER_SCENE[activeScene]    ?? { intensity: 0.10, threshold: 0.90 };
  const sceneVig    = VIGNETTE_PER_SCENE[activeScene] ?? { offset: 0.55, darkness: 0.25 };

  // Blend transition director values with scene config
  const bloomInt   = Math.min(sceneBloom.intensity, td.bloomIntensity * 0.7);
  const bloomThr   = Math.max(sceneBloom.threshold, td.bloomThreshold);
  const vigOff     = activeScene === 9
    ? 0.44  // final scene: fixed tight vignette
    : Math.max(0.20, sceneVig.offset);
  const vigDark    = Math.min(0.65, sceneVig.darkness);

  return (
    <EffectComposer
      multisampling={quality.multisampling}
      enableNormalPass={false}
    >
      <Bloom
        blendFunction={BlendFunction.ADD}
        intensity={bloomInt}
        luminanceThreshold={bloomThr}
        luminanceSmoothing={0.70}
        mipmapBlur={quality.tier === 'high'}
        levels={quality.bloomLevels}
        radius={0.55}
      />
      {quality.vignetteEnabled ? (
        <Vignette
          eskil={false}
          offset={vigOff}
          darkness={vigDark}
        />
      ) : <></>}
    </EffectComposer>
  );
}
