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

    // Return scene position directly — CameraRig handles spring interpolation
    void sceneProgress;
    return { position: scene.camPos, lookAt: scene.camLook, fov: scene.fov };
  }, [activeScene, sceneProgress]);
}
