// ═══════════════════════════════════════════════════════════════
// MASTERING PIPELINE — PHASE OMEGA: CINEMATIC REBIRTH
//
// SOVEREIGN COLOR IDENTITY:
//   Base World:    Deep Graphite, Gunmetal, Dark Titanium
//   Primary Accent: Sovereign Cyan #7FE8FF
//   Threat Accent:  Burnt Amber, Emergency Red
//   Luxury Accent:  Subtle Violet, Royal Blue shadows
//
// PACING: Aggressive. No dead scenes.
// BLOOM: Filmic. Edges only. Not sci-fi.
// VIGNETTE: frames device. Never crushes it.
// ═══════════════════════════════════════════════════════════════

// ── SOVEREIGN COLOR PALETTE ───────────────────────────────────
export const PALETTE = {
  // Base world
  deepGraphite:      '#050507',   // nearly-black with blue tint
  gunmetal:          '#101418',   // darker steel
  darkTitanium:      '#1a1e22',   // surface base

  // Primary accent
  sovereignCyan:     '#7FE8FF',   // electric ice blue — identity
  electricBlue:      '#4FC3F7',   // secondary highlight
  coldWhite:         '#E8F4FF',   // edge highlights

  // Threat
  burntAmber:        '#FF8C00',   // danger, urgency
  emergencyRed:      '#CC2200',   // critical threat
  threatAmber:       '#FF8C00',   // backward-compat alias

  // Luxury
  subtleViolet:      '#8866FF',   // depth, premium
  royalBlueShadow:   '#1A1A4A',   // shadow pools

  // Legacy aliases — required by existing scene components
  institutionalWhite: '#E8F4FF',
  coldSteel:          '#9AA4AE',
  graphite:           '#101418',   // legacy alias → gunmetal
} as const;

// ── Scene accent — one dominant color per scene ───────────────
export const SCENE_ACCENT: Record<number, string> = {
  // ACT I — THE SIGNAL: deep cyan, mystery
  0:  PALETTE.sovereignCyan,
  1:  PALETTE.sovereignCyan,
  2:  PALETTE.sovereignCyan,
  3:  PALETTE.electricBlue,

  // ACT II — ENGINEERED OBJECT: cold white metallic
  4:  PALETTE.coldWhite,
  5:  PALETTE.coldWhite,
  6:  PALETTE.sovereignCyan,
  7:  PALETTE.sovereignCyan,

  // ACT III — FULL REVEAL: sovereign authority
  8:  PALETTE.sovereignCyan,
  9:  PALETTE.coldWhite,
  10: PALETTE.sovereignCyan,

  // ACT IV — THE THREAT: amber/red emergency
  11: PALETTE.burntAmber,
  12: PALETTE.emergencyRed,
  13: PALETTE.burntAmber,
  14: PALETTE.emergencyRed,
  15: PALETTE.sovereignCyan,   // ZK confirmation — cyan returns

  // ACT V — IMMORTALITY: sovereign cyan, eternal
  16: PALETTE.sovereignCyan,
  17: PALETTE.sovereignCyan,
  18: PALETTE.sovereignCyan,
};

// ── Scene exposure — ACES filmic calibrated ───────────────────
// Range 0.0–2.0. Product requires ≥ 0.50 to be readable.
export const SCENE_EXPOSURE: Record<number, number> = {
  // ACT I — mystery, underexposed but not black
  0:  0.55,
  1:  0.65,
  2:  0.60,
  3:  0.68,

  // ACT II — telephoto clarity
  4:  0.72,
  5:  0.74,
  6:  0.68,
  7:  0.75,

  // ACT III — FULL PREMIUM LIGHT
  8:  0.95,   // HERO: maximum exposure
  9:  0.88,
  10: 0.85,

  // ACT IV — darkened for drama, never pure-black
  11: 0.62,
  12: 0.58,
  13: 0.60,
  14: 0.65,
  15: 0.72,

  // ACT V — cinematic fade toward immortal dark
  16: 0.80,
  17: 0.78,
  18: 0.55,   // Final seal: fades toward darkness
};

// ── Scene fog ─────────────────────────────────────────────────
// Near-zero. Only act boundaries get atmospheric depth fog.
export const SCENE_FOG: Record<number, number> = {
  0:  0.0004,
  1:  0.0002,
  2:  0.0002,
  3:  0.0002,
  4:  0.0002,
  5:  0.0002,
  6:  0.0002,
  7:  0.0002,
  8:  0.0001,  // HERO — zero fog. Absolute clarity.
  9:  0.0002,
  10: 0.0002,
  11: 0.0005,  // Threat — slight atmospheric density
  12: 0.0006,
  13: 0.0005,
  14: 0.0004,
  15: 0.0003,
  16: 0.0003,
  17: 0.0002,
  18: 0.0008,  // Final seal — fog rises toward blackout
};

// ── Bloom — filmic optical, not sci-fi ────────────────────────
// Threshold 0.82+ = only highlight edges bloom
// Hero and threat scenes get slight boost
export const SCENE_BLOOM: Record<number, { intensity: number; threshold: number }> = {
  0:  { intensity: 0.10, threshold: 0.90 },
  1:  { intensity: 0.18, threshold: 0.84 },  // LED glow
  2:  { intensity: 0.16, threshold: 0.85 },
  3:  { intensity: 0.14, threshold: 0.87 },

  4:  { intensity: 0.16, threshold: 0.86 },
  5:  { intensity: 0.15, threshold: 0.86 },
  6:  { intensity: 0.18, threshold: 0.84 },  // PCB circuit glow
  7:  { intensity: 0.20, threshold: 0.83 },  // Reflection peak

  8:  { intensity: 0.22, threshold: 0.82 },  // HERO — controlled bloom
  9:  { intensity: 0.18, threshold: 0.84 },
  10: { intensity: 0.16, threshold: 0.85 },

  11: { intensity: 0.28, threshold: 0.78 },  // Threat — amber pressure
  12: { intensity: 0.32, threshold: 0.76 },  // Shockwave — maximum
  13: { intensity: 0.26, threshold: 0.80 },
  14: { intensity: 0.24, threshold: 0.81 },
  15: { intensity: 0.20, threshold: 0.83 },  // ZK — cyan pulse

  16: { intensity: 0.16, threshold: 0.85 },
  17: { intensity: 0.14, threshold: 0.87 },
  18: { intensity: 0.10, threshold: 0.90 },  // Seal — final line only
};

// ── Vignette — frames device, never crushes ───────────────────
// offset HIGH + darkness LOW = open frame with device dominant
// Threat: closed perimeter for emergency pressure
export const SCENE_VIGNETTE: Record<number, { offset: number; darkness: number }> = {
  0:  { offset: 0.48, darkness: 0.35 },
  1:  { offset: 0.50, darkness: 0.30 },
  2:  { offset: 0.50, darkness: 0.32 },
  3:  { offset: 0.52, darkness: 0.28 },

  4:  { offset: 0.55, darkness: 0.25 },
  5:  { offset: 0.54, darkness: 0.26 },
  6:  { offset: 0.52, darkness: 0.28 },
  7:  { offset: 0.56, darkness: 0.24 },

  8:  { offset: 0.62, darkness: 0.18 },  // HERO — open, airy frame
  9:  { offset: 0.58, darkness: 0.22 },
  10: { offset: 0.60, darkness: 0.20 },  // Pedestal — wide, monumental

  11: { offset: 0.44, darkness: 0.42 },  // Threat — tight, claustrophobic
  12: { offset: 0.40, darkness: 0.48 },  // Shockwave — extreme closed
  13: { offset: 0.42, darkness: 0.44 },
  14: { offset: 0.44, darkness: 0.40 },
  15: { offset: 0.48, darkness: 0.34 },

  16: { offset: 0.55, darkness: 0.25 },
  17: { offset: 0.58, darkness: 0.22 },
  18: { offset: 0.40, darkness: 0.60 },  // Seal — heavy closing vignette
};

// ── Motion rhythm ─────────────────────────────────────────────
export const MOTION_RHYTHM = {
  sceneEnter: { duration: 0.9,  easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  sceneExit:  { duration: 0.6,  easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  titleCard:  { duration: 0.75, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  hudElement: { duration: 0.40, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
};

export const FILM_MOTION_SCALE = 1.3;
