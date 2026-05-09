// ═══════════════════════════════════════════════════════════════
// CAMERA CHOREOGRAPHY HOOK — PHASE XXXI
// Reads camPos/camLook/fov directly from SceneRegistry.
// CameraRig now uses spring-damper; this hook is a lightweight
// shim for any legacy code that still calls useCameraChoreography.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useMemo } from 'react';
import { useExperienceStore } from './store';
import { SCENE_REGISTRY } from './scenes';
import type { CameraState } from './types';

export function useCameraChoreography(): CameraState {
  const activeScene   = useExperienceStore((s) => s.activeScene);
  const sceneProgress = useExperienceStore((s) => s.sceneProgress);

  return useMemo((): CameraState => {
    const scene = SCENE_REGISTRY[activeScene];
    if (!scene) {
      return { position: [0, 0, 8], lookAt: [0, 0, 0], fov: 28 };
    }

    // If there are multiple keyframes, interpolate between them
    const kfs = scene.cameraKeyframes;
    if (!kfs || kfs.length === 0) {
      return { position: scene.camPos, lookAt: scene.camLook, fov: scene.fov };
    }
    if (kfs.length === 1) {
      return { position: kfs[0].state.position, lookAt: kfs[0].state.lookAt, fov: kfs[0].state.fov };
    }

    const clamped = Math.max(0, Math.min(1, sceneProgress));
    let a = kfs[0];
    let b = kfs[kfs.length - 1];
    for (let i = 0; i < kfs.length - 1; i++) {
      if (clamped >= kfs[i].progress && clamped <= kfs[i + 1].progress) {
        a = kfs[i]; b = kfs[i + 1]; break;
      }
    }
    const range = b.progress - a.progress;
    const raw   = range > 0 ? (clamped - a.progress) / range : 0;
    const t     = raw * raw * (3 - 2 * raw); // smoothstep

    return {
      position: [
        a.state.position[0] + (b.state.position[0] - a.state.position[0]) * t,
        a.state.position[1] + (b.state.position[1] - a.state.position[1]) * t,
        a.state.position[2] + (b.state.position[2] - a.state.position[2]) * t,
      ],
      lookAt: [
        a.state.lookAt[0] + (b.state.lookAt[0] - a.state.lookAt[0]) * t,
        a.state.lookAt[1] + (b.state.lookAt[1] - a.state.lookAt[1]) * t,
        a.state.lookAt[2] + (b.state.lookAt[2] - a.state.lookAt[2]) * t,
      ],
      fov: a.state.fov + (b.state.fov - a.state.fov) * t,
    };
  }, [activeScene, sceneProgress]);
}
