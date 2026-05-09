// ═══════════════════════════════════════════════════════════════
// SCENE REGISTRY — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// 10 scenes. Clean, intentional camera positions.
// Every shot is a deliberate directorial decision.
//
// Camera philosophy:
//   - Product ALWAYS visible from scene 1 onward
//   - Scene 0: void — pure black, no product
//   - Scenes 1–5: progressive reveal
//   - Scenes 6–9: sovereignty/authority framing
//
// Performance notes:
//   - Far plane 100 (was 200) — shorter depth range = less fill
//   - FOV range: 16–32° — telephoto = less overdraw, tight crop
// ═══════════════════════════════════════════════════════════════

export type ActId = 'identity' | 'hardware' | 'security' | 'assembly' | 'authority';

export interface SceneConfig {
  id:      string;
  index:   number;
  name:    string;
  label:   string;
  act:     ActId;
  camPos:  [number, number, number];
  camLook: [number, number, number];
  fov:     number;
}

function s(
  index: number, id: string, name: string, label: string, act: ActId,
  camPos: [number, number, number], camLook: [number, number, number], fov: number,
): SceneConfig {
  return { index, id, name, label, act, camPos, camLook, fov };
}

// ── SCENE REGISTRY — 10 scenes ───────────────────────────────
// Camera z=5-6 at fov=24-28° → product fills 70-85% of frame.
// Telephoto shots (fov≤18°): camera further back, product still large.
export const SCENE_REGISTRY: SceneConfig[] = [

  // ── ACT I — IDENTITY (0–5s) ──────────────────────────────────
  // Scene 0: absolute void. No product. Bass pulse only.
  s(0, 'void',     'VOID',     'SIGNAL BOOT',         'identity',
    [0, 0, 7.0], [0, 0, 0], 20),

  // Scene 1: hero emergence. Product rises from black. Frontal.
  // fov=26° at z=5.5 → ~80% frame fill. Maximum presence.
  s(1, 'emerge',   'EMERGE',   'HARDWARE DETECTED',   'identity',
    [0, -0.3, 5.5], [0, 0, 0], 26),

  // ── ACT II — HARDWARE REVEAL (5–18s) ─────────────────────────
  // Scene 2: USB-C port. Telephoto. Physical trust interface.
  s(2, 'usbc',     'USB-C',    'PHYSICAL TRUST',      'hardware',
    [-3.2, 0.1, 2.5], [-0.44, 0.01, 0], 16),

  // Scene 3: PCB overhead. Silicon classified core.
  s(3, 'pcb',      'PCB',      'SILICON CORE',        'hardware',
    [0, 4.0, 2.2], [0, 0.08, 0], 18),

  // Scene 4: enclosure edge. Machined precision, anodized rim.
  s(4, 'edge',     'EDGE',     'MACHINED PRECISION',  'hardware',
    [3.0, 1.2, 2.0], [0.40, 0.16, 0], 17),

  // Scene 5: full hero shot. Device assembled. Dead center.
  // Lowest possible FOV for assembled shot — maximum authority.
  s(5, 'hero',     'HERO',     'SOVEREIGN CORE',      'hardware',
    [0, 0, 5.2], [0, 0, 0], 24),

  // ── ACT III — SECURITY (18–32s) ──────────────────────────────
  // Scene 6: low-angle authority. Camera looks up. Monument.
  s(6, 'authority','AUTHORITY','POST-QUANTUM SEALED',  'security',
    [-0.4, -2.0, 5.8], [-0.05, -0.22, 0], 26),

  // Scene 7: 3/4 angle. Device as sovereign object.
  s(7, 'sovereign','SOVEREIGN','ZERO NETWORK · NO CLOUD', 'security',
    [2.2, 0.8, 5.5], [0.28, 0.10, 0], 28),

  // ── ACT IV — ASSEMBLY (32–44s) ───────────────────────────────
  // Scene 8: exploded view. Engineering precision. 3/4 elevated.
  s(8, 'assembly', 'ASSEMBLY', 'PRECISION ASSEMBLY',  'assembly',
    [0.8, 2.0, 6.5], [0.10, 0.22, 0], 30),

  // ── ACT V — AUTHORITY (44–55s) ───────────────────────────────
  // Scene 9: FINAL. Assembled. Perfect center. Absolute stillness.
  s(9, 'final',    'SEALED',   'Q-VAULT',             'authority',
    [0, 0, 5.0], [0, 0, 0], 22),
];

export const ACTS = [
  { id: 'identity',  name: 'IDENTITY',  scenes: [0, 1] },
  { id: 'hardware',  name: 'HARDWARE',  scenes: [2, 3, 4, 5] },
  { id: 'security',  name: 'SECURITY',  scenes: [6, 7] },
  { id: 'assembly',  name: 'ASSEMBLY',  scenes: [8] },
  { id: 'authority', name: 'AUTHORITY', scenes: [9] },
];
