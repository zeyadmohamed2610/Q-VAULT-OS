// ═══════════════════════════════════════════════════════════════
// ADAPTIVE QUALITY SYSTEM — PHASE XL
//
// Auto-detects GPU tier and scales quality accordingly.
// Checks: renderer info, canvas benchmark, memory heuristics.
//
// Tiers:
//   HIGH   → full cinematic (dedicated mid-range GPU+)
//   MEDIUM → reduced bloom, DPR cap 1.0
//   LOW    → no PostFX, single light, DPR 0.8, static bg
//
// This is evaluated ONCE at startup, memoized for the session.
// ═══════════════════════════════════════════════════════════════

export type QualityTier = 'high' | 'medium' | 'low';

export interface QualityProfile {
  tier:             QualityTier;
  dpr:              [number, number];   // min/max devicePixelRatio
  multisampling:    number;             // 0 = off, 4 = MSAA 4x
  bloomEnabled:     boolean;
  bloomLevels:      number;
  vignetteEnabled:  boolean;
  dofEnabled:       boolean;
  environmentIBL:   boolean;           // drei <Environment> IBL pass
  maxLights:        number;            // max point/spot lights in scene
  antialias:        boolean;
  shadowMap:        boolean;
}

const PROFILES: Record<QualityTier, QualityProfile> = {
  high: {
    tier:            'high',
    dpr:             [1, 1.5],
    multisampling:   4,
    bloomEnabled:    true,
    bloomLevels:     5,
    vignetteEnabled: true,
    dofEnabled:      false,    // DOF is always off — product must be sharp
    environmentIBL:  true,
    maxLights:       6,
    antialias:       true,
    shadowMap:       false,    // shadows off — product lit by spot, not shadows
  },
  medium: {
    tier:            'medium',
    dpr:             [0.85, 1.0],
    multisampling:   0,
    bloomEnabled:    true,
    bloomLevels:     3,
    vignetteEnabled: true,
    dofEnabled:      false,
    environmentIBL:  false,   // No IBL — big perf win
    maxLights:       4,
    antialias:       false,
    shadowMap:       false,
  },
  low: {
    tier:            'low',
    dpr:             [0.75, 0.85],
    multisampling:   0,
    bloomEnabled:    false,
    bloomLevels:     0,
    vignetteEnabled: false,
    dofEnabled:      false,
    environmentIBL:  false,
    maxLights:       2,
    antialias:       false,
    shadowMap:       false,
  },
};

// ── Simple GPU benchmark via navigator.gpu / memory heuristics ─
function detectTier(): QualityTier {
  if (typeof window === 'undefined') return 'medium';

  // 1. Check device memory (Chrome/Android only)
  const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  if (mem !== undefined && mem < 4) return 'low';

  // 2. Hardware concurrency (CPU core count heuristic)
  const cores = navigator.hardwareConcurrency ?? 4;
  if (cores <= 2) return 'low';

  // 3. WebGL renderer string — detect Intel/software renderers
  try {
    const canvas   = document.createElement('canvas');
    const gl       = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    if (!gl) return 'low';

    const ext      = gl.getExtension('WEBGL_debug_renderer_info');
    if (ext) {
      const renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) as string;
      const r = renderer.toLowerCase();
      // Known low-perf patterns
      if (r.includes('intel') && (r.includes('hd') || r.includes('uhd'))) {
        return cores >= 8 ? 'medium' : 'low';
      }
      if (r.includes('swiftshader') || r.includes('llvm') || r.includes('software')) {
        return 'low';
      }
      // Dedicated GPU: NVIDIA, AMD, Apple M-series
      if (r.includes('nvidia') || r.includes('amd') || r.includes('radeon') ||
          r.includes('geforce') || r.includes('apple')) {
        return 'high';
      }
    }
    // No renderer info → assume medium
    return 'medium';
  } catch {
    return 'medium';
  }
}

// Singleton — computed once at module load
let _tier: QualityTier | null = null;
let _profile: QualityProfile | null = null;

export function getQualityProfile(): QualityProfile {
  if (!_profile) {
    _tier    = detectTier();
    _profile = PROFILES[_tier];
  }
  return _profile;
}

export function getQualityTier(): QualityTier {
  getQualityProfile();
  return _tier!;
}
