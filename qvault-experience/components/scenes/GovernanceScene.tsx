// ═══════════════════════════════════════════════════════════════
// SCENE 8: RUNTIME GOVERNANCE
// A sovereign cryptographic governance core.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { GovernanceCore } from '@/components/three/GovernanceCore';
import { GovernanceNetwork } from '@/components/three/GovernanceNetwork';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function GovernanceScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 7 && activeScene <= 9;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 8 || activeScene === 9}>
      
      {/* 
        SATELLITE INTELLIGENCE LIGHTING 
        Deep space feel, sharp high-contrast lights.
      */}
      <group>
        <ambientLight intensity={0.05} color={PALETTE.coldSteel} />
        <directionalLight position={[10, 20, 10]} intensity={2.3} color={PALETTE.institutionalWhite} castShadow />
        <pointLight position={[0, 0, 0]} intensity={0.8} color={PALETTE.sovereignCyan} distance={40} />
      </group>


      <GovernanceCore progress={activeScene === 8 ? progress : 1} />
      <GovernanceNetwork progress={activeScene === 8 ? progress : 1} />

    </group>
  );
}
