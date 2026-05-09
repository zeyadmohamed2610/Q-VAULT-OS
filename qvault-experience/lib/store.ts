// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Zustand Global Store
// Single source of truth for the entire experience runtime
// ═══════════════════════════════════════════════════════════════

import { create } from 'zustand';
import type { ExperienceState } from './types';

const DEFAULT_CAMERA = {
  position: [0, 0, 50] as [number, number, number],
  lookAt: [0, 0, 0] as [number, number, number],
  fov: 45,
};

export const useExperienceStore = create<ExperienceState>((set) => ({
  // ── Scroll ──
  activeScene: 0,
  sceneProgress: 0,
  globalProgress: 0,
  scrollDirection: 'down',

  // ── Quality ──
  qualityTier: 'high',
  reducedMotion: false,

  // ── Interaction ──
  hoveredThreat: null,
  activeProtocolStep: 0,
  hardwareState: 'setup',

  // ── 3D ──
  cameraState: DEFAULT_CAMERA,
  scenesLoaded: {},

  // ── Audio ──
  audioEnabled: false,

  // ── Actions ──
  setActiveScene: (scene) => set({ activeScene: scene }),
  setSceneProgress: (progress) => set({ sceneProgress: progress }),
  setGlobalProgress: (progress) => set({ globalProgress: progress }),
  setScrollDirection: (dir) => set({ scrollDirection: dir }),
  setQualityTier: (tier) => set({ qualityTier: tier }),
  setReducedMotion: (reduced) => set({ reducedMotion: reduced }),
  setHoveredThreat: (threat) => set({ hoveredThreat: threat }),
  setActiveProtocolStep: (step) => set({ activeProtocolStep: step }),
  setHardwareState: (state) => set({ hardwareState: state }),
  setCameraState: (state) => set({ cameraState: state }),
  markSceneLoaded: (sceneId) =>
    set((prev) => ({
      scenesLoaded: { ...prev.scenesLoaded, [sceneId]: true },
    })),
  setAudioEnabled: (enabled) => set({ audioEnabled: enabled }),
}));
