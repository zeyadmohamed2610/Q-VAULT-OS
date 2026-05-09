// ═══════════════════════════════════════════════════════════════
// MASTERING PIPELINE — PHASE XXIX
// Documentary color restoration. Institutional realism.
//
// PALETTE HIERARCHY:
//  1. Institutional White  #F5F7FA  — Typography, highlights
//  2. Cold Steel           #9AA4AE  — Metal surfaces, reflections
//  3. Deep Graphite        #050505  — Cinematic black voids
//  4. Sovereign Cyan       #7FDBFF  — Cryptographic identity (LIMITED)
//  5. Threat Amber         #D6A756  — Anomaly / warning states only
//  6. Emergency Red        #8E3B3B  — Critical threat ONLY
//
// COLOR DISCIPLINE:
//  Each scene: one dominant neutral, one restrained accent.
//  NO full-screen color floods.
//  NO RGB gaming look.
//  Institutional. Documentary. Premium.
// ═══════════════════════════════════════════════════════════════

export const PALETTE = {
  institutionalWhite: '#F5F7FA',
  coldSteel:          '#9AA4AE',
  deepGraphite:       '#050505',
  graphite:           '#111111',
  sovereignCyan:      '#7FDBFF',
  threatAmber:        '#D6A756',
  emergencyRed:       '#8E3B3B',
} as const;

// ── Scene accent — restrained, one per scene ──────────────────
export const SCENE_ACCENT: Record<number, string> = {
  0:  PALETTE.sovereignCyan,  // Void Boot     — edge pulse
  1:  PALETTE.sovereignCyan,  // Surveillance  — scan traces
  2:  PALETTE.coldSteel,      // Hardware Root — steel rim
  3:  PALETTE.sovereignCyan,  // Trust Stack   — chain verify
  4:  PALETTE.sovereignCyan,  // Protocol Lab  — sync
  5:  PALETTE.sovereignCyan,  // Encryption    — focal glow
  6:  PALETTE.threatAmber,    // Provisioning  — industrial amber
  7:  PALETTE.sovereignCyan,  // OS Surface    — telemetry
  8:  PALETTE.sovereignCyan,  // Governance    — quorum sync
  9:  PALETTE.threatAmber,    // Threat Matrix — amber tension
  10: PALETTE.sovereignCyan,  // Lifecycle     — heartbeat
  11: PALETTE.coldSteel,      // Roadmap       — sparse steel
  12: PALETTE.sovereignCyan,  // Final Seal    — last pulse
};

// ── Scene exposure — RESTORED for product visibility ──────────
// NOTE: These feed into TransitionDirector which mixes into PostFX.
// The base range is 0.0–2.0. Product visibility requires ≥ 0.4.
export const SCENE_EXPOSURE: Record<number, number> = {
  0:  0.55,   // Void Boot    — mystery, but device is readable
  1:  0.65,   // Surveillance — tension builds, device clear
  2:  0.90,   // Hardware Root — FULL HERO LIGHT
  3:  0.75,   // Trust Stack  — engineered precision
  4:  0.70,   // Protocol Lab — surgical assembly
  5:  0.65,   // Encryption   — controlled, device dominant
  6:  0.85,   // Provisioning — industrial authority
  7:  0.75,   // OS Surface   — command clarity
  8:  0.70,   // Governance   — matte authority
  9:  0.60,   // Threat       — tension dark, device still readable
  10: 0.70,   // Lifecycle    — archival illumination
  11: 0.60,   // Roadmap      — sparse, dignified
  12: 0.45,   // Seal         — reduces toward blackout
};

// ── Fog — DISABLED for hero visibility ───────────────────────
// Fog was the #1 cause of product invisibility.
// All values near zero. Only seal scene has any depth fog.
export const SCENE_FOG: Record<number, number> = {
  0:  0.0005,  // Nearly invisible — just atmospheric depth
  1:  0.0003,
  2:  0.0001,  // Hardware Root — ZERO fog
  3:  0.0004,
  4:  0.0004,
  5:  0.0003,
  6:  0.0001,  // Provisioning — clear authority
  7:  0.0003,
  8:  0.0003,
  9:  0.0004,
  10: 0.0003,
  11: 0.0004,
  12: 0.0008,  // Seal — fog builds gently as light collapses
};

// ── Bloom — filmic, optical, expensive ────────────────────────
// Threshold at 0.85+ means ONLY true highlight edges bloom.
// This creates the "expensive lens" look without sci-fi glow.
export const SCENE_BLOOM: Record<number, { intensity: number; threshold: number }> = {
  0:  { intensity: 0.12, threshold: 0.88 },
  1:  { intensity: 0.15, threshold: 0.86 },
  2:  { intensity: 0.20, threshold: 0.84 },  // Hero — controlled rim bloom
  3:  { intensity: 0.18, threshold: 0.85 },
  4:  { intensity: 0.16, threshold: 0.86 },
  5:  { intensity: 0.14, threshold: 0.87 },
  6:  { intensity: 0.20, threshold: 0.84 },  // Provisioning — amber glow
  7:  { intensity: 0.16, threshold: 0.86 },
  8:  { intensity: 0.14, threshold: 0.87 },
  9:  { intensity: 0.22, threshold: 0.82 },  // Threat — amber pressure bloom
  10: { intensity: 0.15, threshold: 0.86 },
  11: { intensity: 0.12, threshold: 0.88 },
  12: { intensity: 0.10, threshold: 0.90 },  // Seal — final white line only
};

// ── Vignette — frames the device, never crushes it ───────────
// Offset controls how far vignette intrudes.
// Darkness controls how black the perimeter gets.
// Keep offset HIGH and darkness LOW to keep product visible.
export const SCENE_VIGNETTE: Record<number, { offset: number; darkness: number }> = {
  0:  { offset: 0.50, darkness: 0.30 },
  1:  { offset: 0.48, darkness: 0.32 },
  2:  { offset: 0.60, darkness: 0.20 },  // Hardware Root — open frame
  3:  { offset: 0.55, darkness: 0.25 },
  4:  { offset: 0.52, darkness: 0.27 },
  5:  { offset: 0.50, darkness: 0.28 },
  6:  { offset: 0.58, darkness: 0.22 },
  7:  { offset: 0.55, darkness: 0.25 },
  8:  { offset: 0.52, darkness: 0.28 },
  9:  { offset: 0.48, darkness: 0.34 },  // Threat — closed perimeter
  10: { offset: 0.52, darkness: 0.28 },
  11: { offset: 0.50, darkness: 0.30 },
  12: { offset: 0.44, darkness: 0.50 },  // Seal — heavy vignette toward blackout
};

// ── Motion rhythm ─────────────────────────────────────────────
export const MOTION_RHYTHM = {
  sceneEnter: { duration: 1.1,  easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  sceneExit:  { duration: 0.75, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  titleCard:  { duration: 0.85, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
  hudElement: { duration: 0.45, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
};

export const FILM_MOTION_SCALE = 1.2;
