'use client';

// ═══════════════════════════════════════════════════════════════
// CAMERA RIG — PHASE OMEGA: CINEMATIC REBIRTH
//
// Motion philosophy: "The camera costs $50,000."
//
// Shot types by act:
//   ACT I (0-3):   robotic dolly push-in, slow macro drift
//   ACT II (4-7):  telephoto compression, minimal arc
//   ACT III (8-10): authority push-in, gentle vertical rise
//   ACT IV (11-15): AGGRESSIVE — fast spring, diagonal sweeps,
//                   camera shake impulses on each threat cut
//   ACT V (16-18): cinematic slowdown, majestic rise, seal lock
//
// Technical:
//   Spring-damper system — high energy, cinematic settling
//   Velocity impulse on scene change → "snap and settle" feel
//   Arc motion per scene (sinusoidal drift = alive camera)
//   Push-in dolly during hero and immortality scenes
//   FOV breathing: ±1.2° on threat, ±0.6° on hero
// ═══════════════════════════════════════════════════════════════

import { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { safeComposition, COMPOSITION } from '@/lib/SafeCompositionSystem';
import { useExperienceStore } from '@/lib/store';
import * as THREE from 'three';

// ── Spring constants ──────────────────────────────────────────
const POS_SPRING   = 10.0;   // Snappy position settling
const POS_DAMPING  = 5.5;
const LOOK_SPRING  = 13.0;   // Fast gaze tracking
const LOOK_DAMPING = 6.0;
const FOV_SPEED    = 4.0;

// ── Arc motion ────────────────────────────────────────────────
const ARC_AMP = 0.09;  // world units lateral drift
const ARC_HZ  = 0.16;  // cycles/sec — premium slow

// ── FOV breathing ─────────────────────────────────────────────
const FOV_BREATH_HZ = 0.38;

// ── Push-in dolly ─────────────────────────────────────────────
const PUSH_IN_AMOUNT = 0.35; // world units

// ── Pre-allocated vectors — no GC per frame ───────────────────
const _tPos    = new THREE.Vector3();
const _tLook   = new THREE.Vector3();
const _pVel    = new THREE.Vector3();
const _lVel    = new THREE.Vector3();
const _diff    = new THREE.Vector3();
const _accel   = new THREE.Vector3();
const _lookRef = new THREE.Vector3(0, 0, 0);
const _arcOff  = new THREE.Vector3();
const _fwdDir  = new THREE.Vector3();

// ── Scene arc config ──────────────────────────────────────────
// [arcPhaseX, arcPhaseY, arcSpeedMult, pushInEnabled, breathAmp, shakeOnEnter]
// shakeOnEnter → injects velocity impulse for kinetic "cut" feel
type ArcCfg = [number, number, number, boolean, number, boolean];
const SCENE_ARC: Record<number, ArcCfg> = {
  // ── ACT I — slow, deliberate, cinematic push ──────────────
  0:  [0.00, 0.00, 0.0,  false, 0.4,  false], // Void — absolute stillness
  1:  [0.15, 0.10, 0.4,  true,  0.5,  false], // LED — slow macro drift
  2:  [0.25, 0.15, 0.5,  true,  0.5,  false], // Edge — gentle push
  3:  [0.40, 0.20, 0.5,  true,  0.5,  false], // Texture — slow diagonal

  // ── ACT II — telephoto hold, minimal arc ──────────────────
  4:  [0.00, 0.00, 0.25, false, 0.4,  false], // USB-C — almost locked
  5:  [0.20, 0.10, 0.35, false, 0.4,  false], // Seam — tiny lateral
  6:  [0.10, 0.00, 0.25, false, 0.4,  false], // PCB — micro drift only
  7:  [0.50, 0.25, 0.55, true,  0.5,  false], // Reflection — sweeping arc

  // ── ACT III — authority push, vertical rise ───────────────
  8:  [0.00, 0.35, 0.45, true,  0.7,  false], // HERO — gentle rise + push
  9:  [0.20, 0.45, 0.65, false, 0.6,  false], // Exploded — diagonal arc
  10: [0.55, 0.10, 0.75, true,  0.7,  false], // Pedestal — side sweep + push

  // ── ACT IV — AGGRESSIVE, KINETIC, ADDICTIVE ───────────────
  11: [0.10, 0.20, 2.0,  true,  1.4,  true ], // Threat — fast urgency + shake
  12: [0.45, 0.35, 2.2,  true,  1.5,  true ], // Shockwave — diagonal + shake
  13: [0.20, 0.50, 2.3,  true,  1.4,  true ], // Intercept — aggressive
  14: [0.35, 0.15, 1.8,  true,  1.2,  true ], // Containment — heavy + shake
  15: [0.00, 0.00, 1.2,  false, 0.8,  false], // ZK — settling, breath

  // ── ACT V — majestic slowdown, monument ───────────────────
  16: [0.00, 0.75, 0.55, true,  0.6,  false], // Majestic — celestial rise
  17: [0.00, 0.30, 0.40, true,  0.5,  false], // Logo — slow push in
  18: [0.00, 0.00, 0.0,  false, 0.0,  false], // SEAL — locked forever
};

// ─────────────────────────────────────────────────────────────
export function CameraRig() {
  const camera      = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const invalidate  = useThree((s) => s.invalidate);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);
  const prevScene   = useRef(-1);

  // Initialize camera at scene 0
  useEffect(() => {
    const cfg = SCENE_REGISTRY[0];
    if (!cfg) return;
    camera.position.set(...cfg.camPos);
    camera.fov = cfg.fov;
    camera.updateProjectionMatrix();
    _lookRef.set(...cfg.camLook);
    camera.lookAt(_lookRef);
  }, [camera]);

  useFrame((state, delta) => {
    const dt  = Math.min(delta, 0.05);
    const t   = state.clock.elapsedTime;
    const idx = Math.max(0, Math.min(activeScene, SCENE_REGISTRY.length - 1));
    const cfg = SCENE_REGISTRY[idx];
    if (!cfg) return;

    // ── Scene change: velocity impulse for cinematic snap ────
    if (prevScene.current !== activeScene) {
      prevScene.current = activeScene;

      _tPos.set(...cfg.camPos);
      _diff.subVectors(_tPos, camera.position);

      const arc = SCENE_ARC[idx] ?? [0, 0, 0.8, false, 0.5, false];
      const shake = arc[5] as boolean;

      if (shake) {
        // Threat cuts: inject directional impulse for "shockwave" feel
        _pVel.set(
          (Math.random() - 0.5) * 1.8,
          (Math.random() - 0.5) * 1.2,
          (Math.random() - 0.5) * 0.6
        );
        // Strong toward target
        _pVel.addScaledVector(_diff.normalize(), 2.0);
      } else {
        // Standard: 30% impulse toward new position
        _pVel.copy(_diff).multiplyScalar(0.30);
      }
    }

    // ── 1. Base target from scene registry ───────────────────
    _tPos.set(...cfg.camPos);
    _tLook.set(...cfg.camLook);

    // ── 2. Arc motion — sinusoidal drift ─────────────────────
    const arc = SCENE_ARC[idx] ?? [0, 0, 0.8, false, 0.5, false];
    const [arcPhX, arcPhY, arcSpd, pushIn, breathAmp] = arc;
    if (arcSpd > 0) {
      const tx = Math.sin((t * ARC_HZ * arcSpd + arcPhX) * Math.PI * 2) * ARC_AMP;
      const ty = Math.sin((t * ARC_HZ * arcSpd * 0.7 + arcPhY) * Math.PI * 2) * ARC_AMP * 0.65;
      _arcOff.set(tx, ty, 0);
      _tPos.add(_arcOff);
    }

    // ── 3. Push-in dolly ─────────────────────────────────────
    if (pushIn) {
      const sp = progress * progress * (3 - 2 * progress); // smoothstep
      _fwdDir.subVectors(_tLook, _tPos).normalize();
      _tPos.addScaledVector(_fwdDir, sp * PUSH_IN_AMOUNT);
    }

    // ── 4. SafeCompositionSystem compensation ─────────────────
    const minFill = idx <= 3 ? 0 : idx <= 7 ? COMPOSITION.HERO_MIN : COMPOSITION.ENGINEERING_MIN;
    const compensation = safeComposition.getCameraCompensation(minFill);
    if (Math.abs(compensation) > 0.01) {
      _fwdDir.subVectors(_tPos, _tLook).normalize();
      _tPos.addScaledVector(_fwdDir, compensation);
    }

    // ── 5. Spring-damper position ─────────────────────────────
    _diff.subVectors(_tPos, camera.position);
    _accel.copy(_diff).multiplyScalar(POS_SPRING);
    _accel.addScaledVector(_pVel, -POS_DAMPING);
    _pVel.addScaledVector(_accel, dt);
    camera.position.addScaledVector(_pVel, dt);

    // ── 6. Spring-damper lookAt ───────────────────────────────
    _diff.subVectors(_tLook, _lookRef);
    _accel.copy(_diff).multiplyScalar(LOOK_SPRING);
    _accel.addScaledVector(_lVel, -LOOK_DAMPING);
    _lVel.addScaledVector(_accel, dt);
    _lookRef.addScaledVector(_lVel, dt);

    // ── 7. FOV breathing ─────────────────────────────────────
    // Final seal (18): locked. Threat scenes: exaggerated breath.
    const fovBreathAmp = idx === 18 ? 0 : (breathAmp as number) * 0.6;
    const breath       = Math.sin(t * FOV_BREATH_HZ * Math.PI * 2) * fovBreathAmp;
    const targetFov    = cfg.fov + breath;
    camera.fov += (targetFov - camera.fov) * dt * FOV_SPEED;
    camera.updateProjectionMatrix();

    // ── 8. LookAt — always last ───────────────────────────────
    camera.lookAt(_lookRef);

    invalidate();
  });

  return null;
}
