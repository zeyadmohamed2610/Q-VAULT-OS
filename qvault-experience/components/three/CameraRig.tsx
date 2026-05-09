'use client';

// ═══════════════════════════════════════════════════════════════
// CAMERA RIG — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// Performance changes vs OMEGA:
//   × Removed per-frame SafeCompositionSystem calls
//   × Removed shakeOnEnter random impulse (causes GC)
//   × Simplified spring — single spring constant per state
//   × Eliminated arc motion at final scene (scene 9: static)
//
// Motion philosophy:
//   Deliberate. Still. Then moves. Settles. Holds.
//   NOT: constant drift. NOT: endless orbiting.
//
// Spring spec: position spring k=8, damping=5.
//   Settles to ±1% of target in ~0.8s.
//   Fast enough to feel intentional. Slow enough to feel premium.
// ═══════════════════════════════════════════════════════════════

import { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { useExperienceStore } from '@/lib/store';
import * as THREE from 'three';

// ── Spring constants ──────────────────────────────────────────
const K_POS   = 7.0;  // position spring stiffness
const D_POS   = 4.8;  // position damping
const K_LOOK  = 10.0; // gaze spring stiffness
const D_LOOK  = 5.5;  // gaze damping
const K_FOV   = 3.5;  // FOV lerp speed

// ── Arc / micro-drift config per scene ───────────────────────
// [amplitude, frequency, pushInAmount]
// Scene 9 (final): zero motion — absolute stillness
const ARC: Record<number,[number,number,number]> = {
  0: [0.00, 0.00, 0.00],  // Void — locked
  1: [0.06, 0.14, 0.20],  // Emerge — gentle rise push
  2: [0.04, 0.18, 0.12],  // USB-C — hold, tiny drift
  3: [0.05, 0.16, 0.08],  // PCB — almost static
  4: [0.05, 0.18, 0.10],  // Edge — slow arc
  5: [0.05, 0.15, 0.25],  // Hero — slow celestial push
  6: [0.06, 0.14, 0.30],  // Authority — rising push
  7: [0.07, 0.16, 0.15],  // Sovereign — gentle sweep
  8: [0.06, 0.15, 0.10],  // Assembly — easy orbit
  9: [0.00, 0.00, 0.00],  // FINAL — ZERO motion
};

// ── Pre-allocated vectors — GC free ──────────────────────────
const _tPos    = new THREE.Vector3();
const _tLook   = new THREE.Vector3();
const _pVel    = new THREE.Vector3();
const _lVel    = new THREE.Vector3();
const _diff    = new THREE.Vector3();
const _accel   = new THREE.Vector3();
const _lookCur = new THREE.Vector3(0, 0, 0);
const _fwd     = new THREE.Vector3();

// ─────────────────────────────────────────────────────────────
export function CameraRig() {
  const camera      = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const invalidate  = useThree((s) => s.invalidate);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);

  // Initialize at scene 0
  useEffect(() => {
    const cfg = SCENE_REGISTRY[0];
    if (!cfg) return;
    camera.position.set(...cfg.camPos);
    camera.fov = cfg.fov;
    camera.near = 0.1;
    camera.far  = 120;     // Shorter far plane — less fill overhead
    camera.updateProjectionMatrix();
    _lookCur.set(...cfg.camLook);
    camera.lookAt(_lookCur);
    _pVel.set(0, 0, 0);
    _lVel.set(0, 0, 0);
  }, [camera]);

  useFrame((state, delta) => {
    const dt  = Math.min(delta, 0.05);
    const t   = state.clock.elapsedTime;
    const idx = Math.max(0, Math.min(activeScene, SCENE_REGISTRY.length - 1));
    const cfg = SCENE_REGISTRY[idx];
    if (!cfg) return;

    // ── 1. Base target ────────────────────────────────────────
    _tPos.set(...cfg.camPos);
    _tLook.set(...cfg.camLook);

    // ── 2. Micro-arc drift — sinusoidal, per-scene amplitude ──
    const [amp, freq, push] = ARC[idx] ?? [0, 0, 0];
    if (amp > 0 && freq > 0) {
      const tx = Math.sin(t * freq * Math.PI * 2 + 0.3) * amp;
      const ty = Math.sin(t * freq * Math.PI * 1.4 + 1.1) * amp * 0.55;
      _tPos.x += tx;
      _tPos.y += ty;
    }

    // ── 3. Push-in dolly — scene-progress driven ─────────────
    if (push > 0.01) {
      // smoothstep(progress)
      const sp = progress * progress * (3 - 2 * progress);
      _fwd.subVectors(_tLook, _tPos).normalize();
      _tPos.addScaledVector(_fwd, sp * push);
    }

    // ── 4. Position spring ────────────────────────────────────
    _diff.subVectors(_tPos, camera.position);
    _accel.copy(_diff).multiplyScalar(K_POS);
    _accel.addScaledVector(_pVel, -D_POS);
    _pVel.addScaledVector(_accel, dt);
    camera.position.addScaledVector(_pVel, dt);

    // ── 5. LookAt spring ─────────────────────────────────────
    _diff.subVectors(_tLook, _lookCur);
    _accel.copy(_diff).multiplyScalar(K_LOOK);
    _accel.addScaledVector(_lVel, -D_LOOK);
    _lVel.addScaledVector(_accel, dt);
    _lookCur.addScaledVector(_lVel, dt);
    camera.lookAt(_lookCur);

    // ── 6. FOV lerp (no breathing on final scene) ─────────────
    camera.fov += (cfg.fov - camera.fov) * dt * K_FOV;
    camera.updateProjectionMatrix();

    invalidate();
  });

  return null;
}
