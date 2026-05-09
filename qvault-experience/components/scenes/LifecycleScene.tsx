// ═══════════════════════════════════════════════════════════════
// SCENE 10: HARDWARE LIFECYCLE
// Visualizing continuity and sovereign infrastructure across decades.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { LifecycleChamber } from '@/components/three/LifecycleChamber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function LifecycleScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 9 && activeScene <= 11;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 10 || activeScene === 11}>
      
      {/* 
        CRYOGENIC PRESERVATION LIGHTING 
        Deep space cold, reverent illumination.
      */}
      <group>
        <ambientLight intensity={0.04} color={PALETTE.coldSteel} />
        <directionalLight position={[0, 30, 0]} intensity={2.2} color={PALETTE.institutionalWhite} castShadow />
        <directionalLight position={[0, -30, 0]} intensity={0.8} color={PALETTE.coldSteel} />
        <pointLight position={[0, 0, 0]} intensity={0.75} color={PALETTE.sovereignCyan} distance={30} />
      </group>


      <LifecycleChamber progress={activeScene === 10 ? progress : 1} />

    </group>
  );
}
