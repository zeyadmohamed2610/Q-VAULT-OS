// ═══════════════════════════════════════════════════════════════
// SCENE 2: THE OBJECT (HARDWARE KEY REVEAL)
// The most important emotional transition. Reveals the physical 
// trust anchor (Q-Vault hardware) inside a cinematic lab environment.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function HardwareKeyScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);

  // Keep it mounted if we are nearby to allow seamless transitions
  const isVisible = activeScene >= 1 && activeScene <= 3;

  return (
    <group ref={groupRef} visible={isVisible}>
      {/* 
        PREMIUM CINEMATIC LIGHTING 
        Key light: Cool, bright, casts shadows
        Rim light: Sharp edge highlight from behind
        Fill light: Very subtle warm bounce 
      */}
      <group>
        <spotLight
          position={[10, 15, 10]}
          angle={0.3}
          penumbra={1}
          intensity={6.0}
          color={PALETTE.institutionalWhite}
          castShadow
          shadow-bias={-0.0001}
        />
        <spotLight
          position={[-10, 5, -15]}
          angle={0.5}
          penumbra={0.5}
          intensity={6.5}
          color={PALETTE.coldSteel}
          castShadow
        />
        <ambientLight intensity={0.1} color={PALETTE.institutionalWhite} />
      </group>
    </group>
  );
}
