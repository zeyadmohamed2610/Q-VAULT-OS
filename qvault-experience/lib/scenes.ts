// ═══════════════════════════════════════════════════════════════
// SCENE REGISTRY — PHASE OMEGA: CINEMATIC REBIRTH
//
// Camera philosophy: premium product cinematography.
// Every shot feels like it costs $50,000.
//
// 19 scenes (0–18) across 5 acts.
// Camera positions calibrated for:
//   ACT I:   extreme macro — overflows frame, crops to mystery
//   ACT II:  telephoto compression — feels expensive
//   ACT III: full authority — 70-85% fill, centered
//   ACT IV:  aggressive angles — kinetic, urgent
//   ACT V:   monumental stillness — legendary
// ═══════════════════════════════════════════════════════════════

export type ActId =
  | 'signal'      // ACT I  — darkness, obsession
  | 'object'      // ACT II — fragments, desire
  | 'reveal'      // ACT III — full hero
  | 'threat'      // ACT IV — kinetic urgency
  | 'immortality' // ACT V  — legend

export interface SceneConfig {
  id:      string;
  index:   number;
  name:    string;
  label:   string;
  act:     ActId;
  camPos:  [number, number, number];
  camLook: [number, number, number];
  fov:     number;
  cameraKeyframes: Array<{
    progress: number;
    state: { position: [number,number,number]; lookAt: [number,number,number]; fov: number };
  }>;
}

function makeScene(
  index: number,
  id: string,
  name: string,
  label: string,
  act: ActId,
  camPos: [number, number, number],
  camLook: [number, number, number],
  fov: number,
): SceneConfig {
  return {
    index, id, name, label, act, camPos, camLook, fov,
    cameraKeyframes: [{ progress: 0, state: { position: camPos, lookAt: camLook, fov } }],
  };
}

// ═══════════════════════════════════════════════════════════════
// SCENE REGISTRY — PHASE OMEGA
//
// Frame fill formula:
//   visible_h = 2 * camZ * tan(fov/2)
//   fill% = PRODUCT_HEIGHT(~2.1wu) / visible_h
//
// ACT I (0-3):   macro/hidden → crop, mystery
// ACT II (4-7):  telephoto fragments → desire
// ACT III (8-10): HERO → 70-85% fill
// ACT IV (11-15): threat → aggressive, off-center
// ACT V (16-18): monument → centered, massive
// ═══════════════════════════════════════════════════════════════
export const SCENE_REGISTRY: SceneConfig[] = [

  // ────────────────────────────────────────────────────────────
  // ACT I — THE SIGNAL (0–12s)
  // Obsession. Curiosity. First contact.
  // ────────────────────────────────────────────────────────────

  // 0: Pure void. Camera at safe distance. Product invisible.
  //    Only a deep bass pulse tells us something exists.
  makeScene(0, 'void-boot', 'VOID', 'SIGNAL BOOT',
    'signal', [0.0, 0.0, 7.0], [0, 0, 0], 20),

  // 1: LED BLINK — ultra macro. Camera almost touching the board.
  //    We see nothing but a blue LED orb. Device breathes.
  //    rotY configured in product to show PCB surface.
  makeScene(1, 'led-blink', 'LED', 'FIRST CONTACT',
    'signal', [0.2, 0.8, 1.2], [0.03, 0.12, 0], 14),

  // 2: EDGE MACRO — cyan rim cuts the void.
  //    Camera crushes in from the right. Only rim visible.
  makeScene(2, 'edge-macro', 'EDGE', 'HARDWARE DETECTED',
    'signal', [3.2, -0.2, 1.6], [0.45, -0.03, 0], 16),

  // 3: BOOT GLYPHS — surface texture, circuit geography.
  //    Camera above-right, shallow angle, sees enclosure top.
  makeScene(3, 'boot-texture', 'SURFACE', 'IDENTITY INITIALIZING',
    'signal', [1.5, 2.5, 2.8], [0.22, 0.40, 0], 18),

  // ────────────────────────────────────────────────────────────
  // ACT II — ENGINEERED OBJECT (12–26s)
  // Premium fragments. Desire. "This is expensive."
  // ────────────────────────────────────────────────────────────

  // 4: USB-C PORT — extreme telephoto compression.
  //    Camera far-left, tight fov. Physical trust interface.
  makeScene(4, 'usbc-port', 'USB-C', 'PHYSICAL TRUST INTERFACE',
    'object', [-3.0, 0.1, 2.2], [-0.42, 0.02, 0], 15),

  // 5: ENCLOSURE SEAM — diagonal downward, chamfered edge.
  //    Light rakes along the seam between top/bottom shells.
  makeScene(5, 'enclosure-seam', 'SEAM', 'MACHINED PRECISION',
    'object', [1.8, 1.4, 1.9], [0.25, 0.20, 0], 16),

  // 6: PCB SILICON CORE — overhead telephoto.
  //    Camera directly above, rotX configured in product.
  makeScene(6, 'pcb-core', 'SILICON', 'CLASSIFIED ARCHITECTURE',
    'object', [0.0, 4.5, 2.0], [0.0, 0.08, 0], 17),

  // 7: REFLECTION SWEEP — light rakes across the shell.
  //    Camera at 3/4 angle, sees metallic reflections cascade.
  makeScene(7, 'reflection-sweep', 'REFLECTION', 'MACHINED SOVEREIGNTY',
    'object', [-2.0, 0.8, 3.2], [-0.28, 0.12, 0], 20),

  // ────────────────────────────────────────────────────────────
  // ACT III — FULL REVEAL (26–40s)
  // FIRST TRUE HERO SHOT. Assembled. Dominant. Sovereign.
  // ────────────────────────────────────────────────────────────

  // 8: HERO SHOT — dead center. Low-angle authority.
  //    Camera slightly below product. 80% frame fill.
  //    ZERO product rotation. Absolute frontal face.
  makeScene(8, 'hero-reveal', 'HERO', 'SOVEREIGN CORE',
    'reveal', [0.0, -0.5, 5.2], [0.0, 0.0, 0], 23),

  // 9: EXPLODED VIEW — shells separate with ballistic authority.
  //    Camera at 3/4 elevated angle. Full assembly visible.
  makeScene(9, 'exploded-lock', 'ASSEMBLY', 'PRECISION ASSEMBLY',
    'reveal', [0.6, 1.8, 6.0], [0.08, 0.20, 0], 27),

  // 10: LOW-ANGLE PEDESTAL — camera looks UP at the device.
  //     Monumental. Emperor framing. Sovereign monument.
  makeScene(10, 'pedestal', 'PEDESTAL', 'ZERO NETWORK',
    'reveal', [-0.3, -2.2, 5.5], [-0.04, -0.25, 0], 25),

  // ────────────────────────────────────────────────────────────
  // ACT IV — THE THREAT (40–52s)
  // RAPID CUTS. Kinetic. Aggressive. Addictive.
  // 2.5s scenes — pure urgency.
  // ────────────────────────────────────────────────────────────

  // 11: THREAT IMPACT — amber flash. Attack begins. Close tight.
  makeScene(11, 'threat-impact', 'THREAT', 'THREAT INTERCEPTED',
    'threat', [0.8, 0.6, 4.2], [0.10, 0.08, 0], 22),

  // 12: SHOCKWAVE — device holds firm. Camera shakes. Unshaken.
  makeScene(12, 'shockwave', 'SHOCKWAVE', 'QUANTUM ATTACK SURFACE: ZERO',
    'threat', [-1.2, -0.4, 4.0], [-0.16, -0.05, 0], 24),

  // 13: INTERCEPTION — hard diagonal. Military precision.
  makeScene(13, 'intercept', 'INTERCEPT', 'ZERO-KNOWLEDGE ACTIVE',
    'threat', [2.2, -0.8, 3.8], [0.30, -0.10, 0], 21),

  // 14: CONTAINMENT — device centered, threat neutralized.
  //     Camera backs off slightly. Breathing returns.
  makeScene(14, 'containment', 'CONTAINED', 'ML-KEM-768 ACTIVE',
    'threat', [-0.4, 0.4, 4.5], [-0.06, 0.06, 0], 23),

  // 15: ZERO KNOWLEDGE — confirmation flash. Cyan pulse.
  makeScene(15, 'zero-knowledge', 'ZK', 'IMMUTABLE MEMORY SEALED',
    'threat', [0.0, 0.0, 4.8], [0.0, 0.0, 0], 22),

  // ────────────────────────────────────────────────────────────
  // ACT V — IMMORTALITY (52–72s)
  // Slowdown. Monumental. Timeless. Unforgettable.
  // ────────────────────────────────────────────────────────────

  // 16: MAJESTIC RISE — device ascends from void.
  //     Slow celestial upward drift. Infinite space behind.
  makeScene(16, 'majestic-rise', 'MAJESTIC', 'HARDWARE IMMORTALITY',
    'immortality', [0.5, 1.2, 6.5], [0.06, 0.14, 0], 26),

  // 17: LOGO REVEAL — slow push to centered frontal.
  //     Typography emerges: "Q-VAULT"
  makeScene(17, 'logo-reveal', 'LOGO', 'CRYPTOGRAPHIC CONTINUITY',
    'immortality', [0.0, 0.0, 5.8], [0.0, 0.0, 0], 24),

  // 18: FINAL SEAL — absolute stillness. Black void. Monument.
  //     The last frame the viewer sees. Unforgettable.
  makeScene(18, 'final-seal', 'SEALED', 'Q-VAULT',
    'immortality', [0.0, 0.0, 5.0], [0.0, 0.0, 0], 22),
];

// ── Act metadata ──────────────────────────────────────────────
export const ACTS: Array<{ id: ActId; name: string; scenes: number[] }> = [
  { id: 'signal',      name: 'THE SIGNAL',          scenes: [0,1,2,3] },
  { id: 'object',      name: 'ENGINEERED OBJECT',   scenes: [4,5,6,7] },
  { id: 'reveal',      name: 'FULL REVEAL',          scenes: [8,9,10] },
  { id: 'threat',      name: 'THE THREAT',           scenes: [11,12,13,14,15] },
  { id: 'immortality', name: 'IMMORTALITY',          scenes: [16,17,18] },
];
