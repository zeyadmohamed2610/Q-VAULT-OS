// ═══════════════════════════════════════════════════════════════
// SCENES — PHASE XXXV: CINEMATIC RE-DIRECTION
//
// Camera philosophy: Earn the reveal.
//   ACT I   darkness, macro, mystery — wide/dark, product hidden
//   ACT II  extreme macro close-ups  — z=1.8–3.0, telephoto
//   ACT III FULL HERO REVEAL         — z=4.8–6.5, dominant fill
//   ACT IV  threat, aggressive       — z=3.8–4.5, sharp angles
//   ACT V   legendary stillness      — z=5.0–6.0, centered
// ═══════════════════════════════════════════════════════════════

export type ActId = 'signal' | 'object' | 'system' | 'threat' | 'immortality';

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

// ── SCENE REGISTRY — PHASE XXXV ───────────────────────────────
//
// Frame fill math:
//   visible_h = 2 * camZ * tan(fov/2)
//   fill% = TARGET_HEIGHT(2.2wu) / visible_h
//
// Target fills:
//   ACT I/II macro:   camera so close product overflows frame  → mystery
//   ACT III hero:     95–99% fill                              → dominance
//   ACT IV threat:    75–90% fill                              → urgency
//   ACT V immortal:   80–95% fill                              → legend
//
export const SCENE_REGISTRY: SceneConfig[] = [

  // ── ACT I — THE SIGNAL ────────────────────────────────────────
  // Scene 0: Pure void — product invisible. Camera watches the dark.
  makeScene(0, 'void-signal',     'VOID',       'SIGNAL BOOT',              'signal',
    [0.0,  0.0, 6.5], [0, 0, 0], 24),

  // Scene 1: Metal edge macro — camera crushes in from right, sees
  // only the rim-lit right edge. Product fills frame but only the EDGE.
  makeScene(1, 'edge-macro',      'EDGE MACRO', 'HARDWARE DETECTED',        'signal',
    [2.8, -0.1, 1.8], [0.4, 0.0, 0], 17),

  // Scene 2: Silhouette reveal — camera slightly off-axis, product
  // dark with thin cyan halo. Identity before engineering.
  makeScene(2, 'silhouette',      'SILHOUETTE', 'IDENTITY EMERGENCE',       'signal',
    [0.5,  0.2, 4.5], [0.05, 0.05, 0], 20),

  // ── ACT II — THE OBJECT ───────────────────────────────────────
  // Scene 3: USB-C port macro — camera dives into the left side,
  // extreme telephoto compression. Physical trust interface.
  makeScene(3, 'usbc-macro',      'USB-C',      'PHYSICAL TRUST INTERFACE', 'object',
    [-2.5, 0.0, 2.0], [-0.35, 0.0, 0], 16),

  // Scene 4: Corner/chamfer diagonal — elevated right angle,
  // light reflects off the machined enclosure edge.
  makeScene(4, 'corner-macro',    'CHAMFER',    'MACHINED PRECISION',       'object',
    [2.0,  1.2, 2.2], [0.28, 0.18, 0], 17),

  // Scene 5: PCB overhead telephoto — looking straight down at
  // the silicon core. ESP32-S3 as the heart of the device.
  makeScene(5, 'pcb-core',        'SILICON',    'SECURE CORE',              'object',
    [0.1,  3.8, 2.5], [0.02, 0.08, 0], 18),

  // ── ACT III — THE SYSTEM ──────────────────────────────────────
  // Scene 6: FIRST FULL HERO REVEAL. Dead center. Maximum fill.
  // Product appears assembled for the FIRST TIME at full scale.
  makeScene(6, 'hero-reveal',     'HERO',       'SOVEREIGN CORE',           'system',
    [0.0,  0.0, 4.8], [0, 0.0, 0], 25),

  // Scene 7: Exploded view — shells separate to reveal interior.
  // Elevated orbital angle shows the precision assembly.
  makeScene(7, 'assembly',        'ASSEMBLY',   'PRECISION ASSEMBLY',       'system',
    [0.4,  1.6, 6.0], [0, 0.15, 0], 28),

  // Scene 8: Low-angle authority — camera looks slightly up at
  // the assembled device. Sovereign and monumental.
  makeScene(8, 'authority',       'AUTHORITY',  'ZERO NETWORK',             'system',
    [-0.2,-1.0, 5.5], [-0.04,-0.18, 0], 26),

  // ── ACT IV — THE THREAT ───────────────────────────────────────
  // Scene 9: Threat close — camera advances, amber side-light,
  // product slightly angled. Urgency and physical threat response.
  makeScene(9, 'threat',          'THREAT',     'THREAT INTERCEPTED',       'threat',
    [0.5,  0.4, 4.0], [0.06, 0.08, 0], 22),

  // Scene 10: Interception — hard diagonal approach angle.
  // Product remains center but camera attitude is aggressive.
  makeScene(10,'intercept',       'INTERCEPT',  'ZERO-KNOWLEDGE ACTIVE',    'threat',
    [-1.0, 0.3, 4.2], [-0.14, 0.06, 0], 23),

  // ── ACT V — IMMORTALITY ───────────────────────────────────────
  // Scene 11: Majestic pass — slow elevated wide. Device ascends
  // from the darkness like a sovereign monument.
  makeScene(11,'majestic',        'MAJESTIC',   'HARDWARE IMMORTALITY',     'immortality',
    [0.8,  1.4, 6.2], [0.1, 0.12, 0], 27),

  // Scene 12: Final seal — dead center, absolute stillness.
  // Maximum presence. The last thing the viewer sees.
  makeScene(12,'final-seal',      'SEALED',     'Q-VAULT',                  'immortality',
    [0.0,  0.0, 5.2], [0, 0.0, 0], 24),
];

// ── Act descriptor array ──────────────────────────────────────
export const ACTS: Array<{ id: ActId; name: string }> = [
  { id: 'signal',      name: 'ACT I — THE SIGNAL' },
  { id: 'object',      name: 'ACT II — THE OBJECT' },
  { id: 'system',      name: 'ACT III — THE SYSTEM' },
  { id: 'threat',      name: 'ACT IV — THE THREAT' },
  { id: 'immortality', name: 'ACT V — IMMORTALITY' },
];
