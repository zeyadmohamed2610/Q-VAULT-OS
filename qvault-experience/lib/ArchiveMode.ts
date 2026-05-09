// ═══════════════════════════════════════════════════════════════
// ARCHIVE MODE
// NEXT_PUBLIC_QVAULT_ARCHIVE=true
// Transforms the experience into a preserved sovereign artifact.
// Deterministic playback. Locked pacing. Immutable pipeline.
// ═══════════════════════════════════════════════════════════════

export const IS_ARCHIVE = process.env.NEXT_PUBLIC_QVAULT_ARCHIVE === 'true';
export const IS_RELEASE  = process.env.NEXT_PUBLIC_QVAULT_RELEASE  === 'true';

export interface ArchiveModeConfig {
  // Playback
  autoCycle: boolean;          // Auto-advance through scenes
  cycleDwellMs: number;        // Time per scene in archive loop
  allowUserInterrupt: boolean; // Can user scroll/navigate?

  // Rendering
  lockedExposure: number;      // Fixed middleGrey
  lockedBloom: number;         // Fixed bloom multiplier
  forcedDPR: number;           // Pixel ratio locked

  // Audio
  archivalAudioMastering: boolean;
  muteSFX: boolean;

  // HUD
  showArchiveWatermark: boolean;
  hideAllDebug: boolean;
  hideDeploymentCommand: boolean;
}

export const ARCHIVE_CONFIG: ArchiveModeConfig = IS_ARCHIVE
  ? {
      autoCycle: true,
      cycleDwellMs: 18_000,     // 18 seconds per scene
      allowUserInterrupt: false,
      lockedExposure: 0.48,
      lockedBloom: 1.05,
      forcedDPR: 2,
      archivalAudioMastering: true,
      muteSFX: true,
      showArchiveWatermark: true,
      hideAllDebug: true,
      hideDeploymentCommand: true,
    }
  : {
      autoCycle: false,
      cycleDwellMs: 0,
      allowUserInterrupt: true,
      lockedExposure: 0.5,
      lockedBloom: 1.0,
      forcedDPR: 2,
      archivalAudioMastering: false,
      muteSFX: false,
      showArchiveWatermark: false,
      hideAllDebug: IS_RELEASE,
      hideDeploymentCommand: IS_RELEASE,
    };
