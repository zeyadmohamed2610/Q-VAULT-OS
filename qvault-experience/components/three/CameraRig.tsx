'use client';

// ═══════════════════════════════════════════════════════════════
// CAMERA RIG — PHASE XXXIII: COMMERCIAL ENERGY
//
// Motion philosophy:
//   - Heavy spring-damper with deliberate speed boost
//   - Arc motion per scene (camera orbits slightly during hold)
//   - Push-in on hero reveal (z slowly decreases during scene)
//   - FOV breathing: 0.8° ± — lens feels alive
//   - Micro-drift: 0.3% sinusoidal parallax per axis
//   - Scene switch: fast jump then settle (interrupt spring)
// ═══════════════════════════════════════════════════════════════

import { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { safeComposition, COMPOSITION } from '@/lib/SafeCompositionSystem';
import { useExperienceStore } from '@/lib/store';
import * as THREE from 'three';

// ── Spring constants ──────────────────────────────────────────
// Increased from Phase XXXI (was POS_SPRING=6) → more energy
const POS_SPRING   = 9.0;   // Snappier position settling
const POS_DAMPING  = 5.0;
const LOOK_SPRING  = 11.0;  // Faster gaze tracking
const LOOK_DAMPING = 5.5;
const FOV_SPEED    = 3.5;

// ── Arc motion — camera orbits slightly during hold ───────────
// Each scene: camera traces a slow arc (sinusoidal X/Y offset)
// Makes the static shot feel alive without being obvious
const ARC_AMP   = 0.08;  // world units — subtle lateral drift
const ARC_HZ    = 0.18;  // cycles/sec — very slow arc

// ── FOV breathing — lens feels alive ─────────────────────────
const FOV_BREATH_AMP = 0.8;  // ±0.8° (was ±0.4°)
const FOV_BREATH_HZ  = 0.4;

// ── Push-in — hero shots dolly forward during scene ───────────
// sceneProgress 0→1: camera moves 0.3wu closer
const PUSH_IN_AMOUNT = 0.3; // wu — subtle forward motion

// ── Pre-allocated — no GC per frame ──────────────────────────
const _tPos    = new THREE.Vector3();
const _tLook   = new THREE.Vector3();
const _pVel    = new THREE.Vector3();
const _lVel    = new THREE.Vector3();
const _diff    = new THREE.Vector3();
const _accel   = new THREE.Vector3();
const _lookRef = new THREE.Vector3(0, 0, 0);
const _arcOff  = new THREE.Vector3();
const _fwdDir  = new THREE.Vector3();

// ── Scene arc config — unique motion per scene ───────────────
// [arcPhaseX, arcPhaseY, arcSpeedMult, pushInEnabled]
// ACT I/II macro scenes: minimal arc (camera already extreme close)
// ACT III hero: gentle rise, push-in for reveal
// ACT IV threat: maximum speed urgency
// ACT V: slow celestial motion
type ArcCfg = [number, number, number, boolean];
const SCENE_ARC: Record<number, ArcCfg> = {
  0:  [0.00, 0.00, 0.0,  false], // Void — absolute stillness
  1:  [0.20, 0.10, 0.5,  true],  // Edge macro — very slow drift, push in
  2:  [0.40, 0.20, 0.6,  true],  // Silhouette — slow arc right
  3:  [0.00, 0.00, 0.3,  false], // USB-C macro — barely moves (already extreme)
  4:  [0.30, 0.10, 0.4,  false], // Corner macro — tiny lateral
  5:  [0.10, 0.00, 0.3,  false], // PCB overhead — micro drift
  6:  [0.00, 0.40, 0.5,  true],  // HERO REVEAL — gentle vertical rise + push in
  7:  [0.20, 0.50, 0.7,  false], // Exploded — diagonal arc
  8:  [0.60, 0.10, 0.8,  true],  // Authority — slow right arc + push
  9:  [0.10, 0.20, 1.5,  true],  // Threat — fast urgency push
  10: [0.40, 0.30, 1.6,  true],  // Intercept — aggressive diagonal
  11: [0.00, 0.80, 0.6,  true],  // Majestic — slow celestial rise
  12: [0.00, 0.00, 0.0,  false], // Sealed — locked still, final monument
};

// ─────────────────────────────────────────────────────────────
export function CameraRig() {
  const camera      = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const invalidate  = useThree((s) => s.invalidate);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);
  const prevScene   = useRef(-1);

  // Initialize camera at scene 0 immediately
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

    // ── Detect scene change → inject velocity for snappy entry ─
    if (prevScene.current !== activeScene) {
      prevScene.current = activeScene;
      // Impulse: slight velocity kick toward new position
      // creates that "camera snaps and settles" luxury feel
      _tPos.set(...cfg.camPos);
      _diff.subVectors(_tPos, camera.position);
      _pVel.copy(_diff).multiplyScalar(0.35); // 35% impulse
    }

    // 1. Base target position from scene registry
    _tPos.set(...cfg.camPos);
    _tLook.set(...cfg.camLook);

    // 2. Arc motion — sinusoidal drift during scene hold
    const arc = SCENE_ARC[idx] ?? [0, 0, 0.8, false];
    const arcPhX = arc[0], arcPhY = arc[1], arcSpd = arc[2], pushIn = arc[3];
    if (arcSpd > 0) {
      const tx = Math.sin((t * ARC_HZ * arcSpd + arcPhX) * Math.PI * 2) * ARC_AMP;
      const ty = Math.sin((t * ARC_HZ * arcSpd * 0.7 + arcPhY) * Math.PI * 2) * ARC_AMP * 0.6;
      _arcOff.set(tx, ty, 0);
      _tPos.add(_arcOff);
    }

    // 3. Push-in — camera slowly dolls forward during hero shots
    if (pushIn) {
      // Smoothstep the progress for elegant easing
      const sp = progress * progress * (3 - 2 * progress);
      _fwdDir.subVectors(_tLook, _tPos).normalize();
      _tPos.addScaledVector(_fwdDir, sp * PUSH_IN_AMOUNT);
    }

    // 4. SafeCompositionSystem — auto-compensate if product too small
    const minFill = idx <= 1 ? 0 : idx <= 4 ? COMPOSITION.HERO_MIN : COMPOSITION.ENGINEERING_MIN;
    const compensation = safeComposition.getCameraCompensation(minFill);
    if (Math.abs(compensation) > 0.01) {
      _fwdDir.subVectors(_tPos, _tLook).normalize();
      _tPos.addScaledVector(_fwdDir, compensation);
    }

    // 5. Spring-damper position
    _diff.subVectors(_tPos, camera.position);
    _accel.copy(_diff).multiplyScalar(POS_SPRING);
    _accel.addScaledVector(_pVel, -POS_DAMPING);
    _pVel.addScaledVector(_accel, dt);
    camera.position.addScaledVector(_pVel, dt);

    // 6. Spring-damper lookAt
    _diff.subVectors(_tLook, _lookRef);
    _accel.copy(_diff).multiplyScalar(LOOK_SPRING);
    _accel.addScaledVector(_lVel, -LOOK_DAMPING);
    _lVel.addScaledVector(_accel, dt);
    _lookRef.addScaledVector(_lVel, dt);

    // 7. FOV — lerp + breathing. Sealed scene: holds perfectly still.
    const breathAmp = idx === 12 ? 0 : FOV_BREATH_AMP;
    const breath    = Math.sin(t * FOV_BREATH_HZ * Math.PI * 2) * breathAmp;
    const targetFov = cfg.fov + breath;
    camera.fov += (targetFov - camera.fov) * dt * FOV_SPEED;
    camera.updateProjectionMatrix();

    // 8. Apply lookAt — ALWAYS last
    camera.lookAt(_lookRef);

    invalidate();
  });

  return null;
}
