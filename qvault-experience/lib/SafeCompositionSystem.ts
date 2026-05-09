// ═══════════════════════════════════════════════════════════════
// SAFE COMPOSITION SYSTEM — PHASE XXXI
// Hardware visibility tracking. Cinematic framing enforcement.
// Subject dominance scoring. Automatic camera compensation.
// ═══════════════════════════════════════════════════════════════

import * as THREE from 'three';

// ── Scoring thresholds ──────────────────────────────────────────
export const COMPOSITION = {
  HERO_MIN:        0.65,  // hero shots: 65% fill minimum
  MACRO_MIN:       0.82,  // macro shots: 82% fill minimum
  ENGINEERING_MIN: 0.55,  // engineering/exploded: 55% minimum
  CLIP_MARGIN:     0.05,  // 5% safety margin before edge clip
} as const;

// ── Internal state ──────────────────────────────────────────────
interface CompositionState {
  dominanceScore: number;    // 0–1: how much screen the product fills
  isClipping:     boolean;   // any corner outside viewport?
  ndcBounds:      { min: THREE.Vector2; max: THREE.Vector2 };
  lastUpdate:     number;
}

const _state: CompositionState = {
  dominanceScore: 0,
  isClipping:     false,
  ndcBounds:      { min: new THREE.Vector2(), max: new THREE.Vector2() },
  lastUpdate:     0,
};

// ── Pre-allocated helpers ───────────────────────────────────────
const _box      = new THREE.Box3();
const _corners  = Array.from({ length: 8 }, () => new THREE.Vector3());
const _ndcPt    = new THREE.Vector3();
const _cam      = new THREE.Matrix4();

/**
 * Call once per frame from CommercialProductFilm.useFrame()
 * Lightweight: only projects 8 AABB corners, no GPU reads.
 */
function reportProductGroup(group: THREE.Group, scale: number): void {
  const now = performance.now();
  // Throttle: update at most every 3 frames (~50ms @ 60fps)
  if (now - _state.lastUpdate < 48) return;
  _state.lastUpdate = now;

  try {
    _box.setFromObject(group);
    if (_box.isEmpty()) return;

    // Extract 8 corners of AABB
    const mn = _box.min, mx = _box.max;
    _corners[0].set(mn.x, mn.y, mn.z);
    _corners[1].set(mx.x, mn.y, mn.z);
    _corners[2].set(mn.x, mx.y, mn.z);
    _corners[3].set(mx.x, mx.y, mn.z);
    _corners[4].set(mn.x, mn.y, mx.z);
    _corners[5].set(mx.x, mn.y, mx.z);
    _corners[6].set(mn.x, mx.y, mx.z);
    _corners[7].set(mx.x, mx.y, mx.z);

    // Project to NDC using camera stored in group.userData
    const camera: THREE.Camera | undefined = group.userData._camera;
    if (!camera) return;

    _cam.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let anyOutside = false;

    for (const corner of _corners) {
      _ndcPt.copy(corner).applyMatrix4(_cam);
      if (_ndcPt.x < -1 || _ndcPt.x > 1 || _ndcPt.y < -1 || _ndcPt.y > 1) {
        anyOutside = true;
      }
      minX = Math.min(minX, _ndcPt.x);
      minY = Math.min(minY, _ndcPt.y);
      maxX = Math.max(maxX, _ndcPt.x);
      maxY = Math.max(maxY, _ndcPt.y);
    }

    const spanX = Math.min(maxX, 1) - Math.max(minX, -1);
    const spanY = Math.min(maxY, 1) - Math.max(minY, -1);
    _state.dominanceScore = Math.max(0, Math.min(1, (spanX / 2) * (spanY / 2)));
    _state.isClipping     = anyOutside;
    _state.ndcBounds.min.set(minX, minY);
    _state.ndcBounds.max.set(maxX, maxY);
  } catch {
    // Never crash the render loop
  }
}

/** Attach camera to product group so SafeCompositionSystem can access it */
function attachCamera(group: THREE.Group, camera: THREE.Camera): void {
  group.userData._camera = camera;
}

/** Current dominance score 0–1 */
function getDominance(): number { return _state.dominanceScore; }

/** Whether product is clipping outside viewport */
function isClipping(): boolean { return _state.isClipping; }

/**
 * Compute recommended camera z-distance compensation.
 * Returns delta to add to current camera z if product is too small/large.
 */
function getCameraCompensation(targetDominance: number): number {
  const current = _state.dominanceScore;
  if (current <= 0) return 0;
  // If product is 30% smaller than target, pull camera in by proportional amount
  const ratio = targetDominance / current;
  if (ratio > 1.05) return -(ratio - 1) * 1.5; // move closer
  if (ratio < 0.92) return  (1 - ratio) * 1.5; // move further
  return 0;
}

export const safeComposition = {
  reportProductGroup,
  attachCamera,
  getDominance,
  isClipping,
  getCameraCompensation,
  get state() { return _state; },
};
