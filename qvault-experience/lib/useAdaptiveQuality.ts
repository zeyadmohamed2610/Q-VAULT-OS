// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Adaptive Quality System
// Monitors GPU frame timing and adjusts quality tier
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect, useRef } from 'react';
import { useExperienceStore } from './store';
import type { QualityTier, QualitySettings } from './types';

export const QUALITY_CONFIGS: Record<QualityTier, QualitySettings> = {
  ultra:  { shadows: true,  bloom: true,  particles: 5000, dpr: 2.0, postfx: true  },
  high:   { shadows: true,  bloom: true,  particles: 2000, dpr: 1.5, postfx: true  },
  medium: { shadows: false, bloom: true,  particles: 1000, dpr: 1.0, postfx: false },
  low:    { shadows: false, bloom: false, particles: 0,    dpr: 1.0, postfx: false },
};

const TIER_ORDER: QualityTier[] = ['ultra', 'high', 'medium', 'low'];
const FRAME_BUDGET_MS = 20; // ~50fps threshold before downgrade
const CONSECUTIVE_SLOW_FRAMES = 5;

export function useAdaptiveQuality(): QualitySettings {
  const qualityTier = useExperienceStore((s) => s.qualityTier);
  const setQualityTier = useExperienceStore((s) => s.setQualityTier);
  const slowFrames = useRef(0);
  const rafId = useRef<number>(0);
  const lastTime = useRef(performance.now());

  useEffect(() => {
    const measure = () => {
      const now = performance.now();
      const delta = now - lastTime.current;
      lastTime.current = now;

      if (delta > FRAME_BUDGET_MS) {
        slowFrames.current++;
      } else {
        slowFrames.current = Math.max(0, slowFrames.current - 1);
      }

      if (slowFrames.current >= CONSECUTIVE_SLOW_FRAMES) {
        const currentIndex = TIER_ORDER.indexOf(qualityTier);
        if (currentIndex < TIER_ORDER.length - 1) {
          setQualityTier(TIER_ORDER[currentIndex + 1]);
          slowFrames.current = 0;
        }
      }

      rafId.current = requestAnimationFrame(measure);
    };

    rafId.current = requestAnimationFrame(measure);
    return () => cancelAnimationFrame(rafId.current);
  }, [qualityTier, setQualityTier]);

  return QUALITY_CONFIGS[qualityTier];
}
