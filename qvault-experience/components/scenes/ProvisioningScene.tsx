// ═══════════════════════════════════════════════════════════════
// SCENE 6: PROVISIONING
// A cinematic chamber visualizing hardware onboarding.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { ProvisioningChamber } from '@/components/three/ProvisioningChamber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function ProvisioningScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 5 && activeScene <= 7;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 6 || activeScene === 7}>
      
      {/* 
        CLEAN-ROOM LIGHTING 
        Surgical, sharp rim lights, deep contrast.
      */}
      <group>
        <spotLight
          position={[0, 10, 0]}
          angle={0.4}
          penumbra={0.5}
          intensity={10.0}
          color={PALETTE.institutionalWhite}
          castShadow
        />
        <spotLight
          position={[-5, 5, -5]}
          angle={0.5}
          penumbra={1}
          intensity={6.0}
          color={PALETTE.threatAmber}
        />
        <spotLight
          position={[5, 5, 5]}
          angle={0.5}
          penumbra={1}
          intensity={4.0}
          color={PALETTE.coldSteel}
        />
        <ambientLight intensity={0.04} color={PALETTE.coldSteel} />
      </group>

      {/* Controlled low-density fog — enclave hardware must remain visible */}

      <ProvisioningChamber progress={activeScene === 6 ? progress : 1} />

    </group>
  );
}
