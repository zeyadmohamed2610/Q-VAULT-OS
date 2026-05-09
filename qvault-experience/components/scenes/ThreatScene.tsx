// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Scene 1: Threat Horizon
// Introduces the existential quantum threat. The encryption
// protecting the modern world is already dying.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { LatticeField } from '@/components/three/LatticeField';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function ThreatScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);

  // Only render or update heavily if we are in or near Scene 1
  const isVisible = activeScene === 1 || activeScene === 0 || activeScene === 2;

  return (
    <group ref={groupRef} visible={isVisible}>
      {/* Dynamic ambient lighting for the threat scene */}
      {/* Dynamic ambient lighting for the threat scene */}
      <ambientLight intensity={0.04} color={PALETTE.coldSteel} />
      <pointLight position={[0, 0, 10]} intensity={0.65} color={PALETTE.sovereignCyan} />
      
      {/* Deep volumetric fog for depth fading */}

      {/* The main quantum lattice structure */}
      <LatticeField />
      
      {/* 
        NOTE: Future GLB Asset imports go here.
        Example: The silhouette of the Q-Vault hardware preparing for Scene 2 
        will be lazy-loaded in the background using the asset pipeline 
        established in lib/loaders.ts.
      */}
    </group>
  );
}
