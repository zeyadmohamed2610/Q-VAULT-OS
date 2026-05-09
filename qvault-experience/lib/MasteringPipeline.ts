// ═══════════════════════════════════════════════════════════════
// MASTERING PIPELINE — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// Calibrated for 10-scene structure.
// Values set conservatively — effect intensity budget is LEAN.
// ═══════════════════════════════════════════════════════════════

export const PALETTE = {
  // ── Core world ─────────────────────────────────────────────
  deepGraphite:      '#050507',
  gunmetal:          '#0f1214',
  darkTitanium:      '#1a1e22',

  // ── Primary accent ─────────────────────────────────────────
  sovereignCyan:     '#7FE8FF',
  electricBlue:      '#4FC3F7',
  coldWhite:         '#E8F4FF',

  // ── Threat ─────────────────────────────────────────────────
  burntAmber:        '#FF8C00',
  emergencyRed:      '#CC2200',

  // ── Legacy aliases ─────────────────────────────────────────
  institutionalWhite: '#E8F4FF',
  coldSteel:          '#9AA4AE',
  graphite:           '#0f1214',
  threatAmber:        '#FF8C00',
  emergencyred:       '#CC2200',
} as const;

export const SCENE_ACCENT: Record<number, string> = {
  0: PALETTE.sovereignCyan,
  1: PALETTE.sovereignCyan,
  2: PALETTE.coldWhite,
  3: PALETTE.sovereignCyan,
  4: PALETTE.coldWhite,
  5: PALETTE.sovereignCyan,
  6: PALETTE.sovereignCyan,
  7: PALETTE.sovereignCyan,
  8: PALETTE.coldWhite,
  9: PALETTE.sovereignCyan,
};

// Exposure: ACES-tuned. Product readable at ≥ 0.60.
export const SCENE_EXPOSURE: Record<number, number> = {
  0: 0.45,   // void — very dark
  1: 0.80,   // emerge — hero lift
  2: 0.72,
  3: 0.70,
  4: 0.72,
  5: 0.90,   // full hero — maximum
  6: 0.80,
  7: 0.78,
  8: 0.75,
  9: 0.60,   // final — fades toward monument
};

export const SCENE_FOG: Record<number, number> = {
  0: 0.0005,
  1: 0.0002,
  2: 0.0002,
  3: 0.0002,
  4: 0.0002,
  5: 0.0001,  // hero — crystal clear
  6: 0.0002,
  7: 0.0002,
  8: 0.0002,
  9: 0.0005,
};

export const SCENE_BLOOM: Record<number, { intensity: number; threshold: number }> = {
  0: { intensity: 0.05, threshold: 0.92 },
  1: { intensity: 0.12, threshold: 0.88 },
  2: { intensity: 0.10, threshold: 0.90 },
  3: { intensity: 0.14, threshold: 0.86 },
  4: { intensity: 0.10, threshold: 0.90 },
  5: { intensity: 0.14, threshold: 0.86 },
  6: { intensity: 0.12, threshold: 0.88 },
  7: { intensity: 0.12, threshold: 0.88 },
  8: { intensity: 0.10, threshold: 0.90 },
  9: { intensity: 0.08, threshold: 0.92 },
};

export const SCENE_VIGNETTE: Record<number, { offset: number; darkness: number }> = {
  0: { offset: 0.44, darkness: 0.42 },
  1: { offset: 0.55, darkness: 0.25 },
  2: { offset: 0.58, darkness: 0.22 },
  3: { offset: 0.55, darkness: 0.25 },
  4: { offset: 0.56, darkness: 0.24 },
  5: { offset: 0.62, darkness: 0.18 },
  6: { offset: 0.58, darkness: 0.22 },
  7: { offset: 0.56, darkness: 0.24 },
  8: { offset: 0.55, darkness: 0.25 },
  9: { offset: 0.42, darkness: 0.50 },
};

export const MOTION_RHYTHM = {
  sceneEnter: { duration: 0.9,  easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  sceneExit:  { duration: 0.6,  easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  titleCard:  { duration: 0.75, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  hudElement: { duration: 0.40, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
};

export const FILM_MOTION_SCALE = 1.0;
