// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Core Type Definitions
// ═══════════════════════════════════════════════════════════════

export type QualityTier = 'ultra' | 'high' | 'medium' | 'low';

export type ScrollDirection = 'up' | 'down';

export type HardwareState = 'setup' | 'vault' | 'reset';

export type ActId = 'contact' | 'mechanism' | 'command' | 'horizon';

// ── Camera ──

export interface CameraState {
  position: [number, number, number];
  lookAt: [number, number, number];
  fov: number;
}

export interface CameraKeyframe {
  progress: number;
  state: CameraState;
  easing?: string;
}

// ── Scenes ──

export interface SceneConfig {
  id: string;
  index: number;
  name: string;
  act: ActId;
  scrollVH: number;
  pin: boolean;
  scrub: true | number;
  cameraKeyframes: CameraKeyframe[];
}

export interface SceneProps {
  sceneIndex: number;
  isActive: boolean;
  progress: number;
  qualityTier: QualityTier;
  reducedMotion: boolean;
}

export interface ThreeSceneProps extends SceneProps {
  cameraState: CameraState;
  onLoad?: () => void;
}

// ── Quality ──

export interface QualitySettings {
  shadows: boolean;
  bloom: boolean;
  particles: number;
  dpr: number;
  postfx: boolean;
}

// ── Store ──

export interface ExperienceState {
  // Scroll
  activeScene: number;
  sceneProgress: number;
  globalProgress: number;
  scrollDirection: ScrollDirection;

  // Quality
  qualityTier: QualityTier;
  reducedMotion: boolean;

  // Interaction
  hoveredThreat: string | null;
  activeProtocolStep: number;
  hardwareState: HardwareState;

  // 3D
  cameraState: CameraState;
  scenesLoaded: Record<string, boolean>;

  // Audio
  audioEnabled: boolean;

  // Actions
  setActiveScene: (scene: number) => void;
  setSceneProgress: (progress: number) => void;
  setGlobalProgress: (progress: number) => void;
  setScrollDirection: (dir: ScrollDirection) => void;
  setQualityTier: (tier: QualityTier) => void;
  setReducedMotion: (reduced: boolean) => void;
  setHoveredThreat: (threat: string | null) => void;
  setActiveProtocolStep: (step: number) => void;
  setHardwareState: (state: HardwareState) => void;
  setCameraState: (state: CameraState) => void;
  markSceneLoaded: (sceneId: string) => void;
  setAudioEnabled: (enabled: boolean) => void;
}
