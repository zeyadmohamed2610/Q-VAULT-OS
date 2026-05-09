// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — HUD Overlay
// Persistent heads-up display layer above canvas and scroll.
// Scene-specific overlays are conditionally rendered.
// ═══════════════════════════════════════════════════════════════

'use client';

import { SceneIndicator } from './SceneIndicator';
import { ScrollProgress } from './ScrollProgress';
import { ActMarker } from './ActMarker';
import { BootTerminal } from './BootTerminal';
import { ScanlineOverlay } from './ScanlineOverlay';
import { IrisTransition } from './IrisTransition';
import { ThreatOverlay } from './ThreatOverlay';
import { HardwareOverlay } from './HardwareOverlay';
import { TrustStackOverlay } from './TrustStackOverlay';
import { ProtocolOverlay } from './ProtocolOverlay';
import { ProofOverlay } from './ProofOverlay';
import { ProvisioningOverlay } from './ProvisioningOverlay';
import { OsOverlay } from './OsOverlay';
import { GovernanceOverlay } from './GovernanceOverlay';
import { ThreatMatrixOverlay } from './ThreatMatrixOverlay';
import { LifecycleOverlay } from './LifecycleOverlay';
import { RoadmapOverlay } from './RoadmapOverlay';
import { SealOverlay } from './SealOverlay';

export function HUDOverlay() {
  return (
    <div className="hud-overlay">
      {/* Persistent HUD elements */}
      <SceneIndicator />
      <ScrollProgress />
      <ActMarker />

      {/* Scene 0: Void Boot overlays */}
      <BootTerminal />
      <ScanlineOverlay />
      <IrisTransition />

      {/* Scene 1: Threat Horizon overlays */}
      <ThreatOverlay />

      {/* Scene 2: The Object (Hardware) overlays */}
      <HardwareOverlay />

      {/* Scene 3: Trust Stack overlays */}
      <TrustStackOverlay />

      {/* Scene 4: Protocol Lab overlays */}
      <ProtocolOverlay />

      {/* Scene 5: Zero Knowledge overlays */}
      <ProofOverlay />

      {/* Scene 6: Provisioning overlays */}
      <ProvisioningOverlay />

      {/* Scene 7: OS Surface overlays */}
      <OsOverlay />

      {/* Scene 8: Governance overlays */}
      <GovernanceOverlay />

      {/* Scene 9: Threat Matrix overlays */}
      <ThreatMatrixOverlay />

      {/* Scene 10: Hardware Lifecycle overlays */}
      <LifecycleOverlay />

      {/* Scene 11: Roadmap overlays */}
      <RoadmapOverlay />

      {/* Scene 12: Seal overlays */}
      <SealOverlay />
    </div>
  );
}
