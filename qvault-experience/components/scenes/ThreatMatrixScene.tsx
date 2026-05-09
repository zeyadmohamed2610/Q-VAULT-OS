// ═══════════════════════════════════════════════════════════════
// SCENE 9: THREAT MATRIX
// Live post-quantum attack interception system.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { ThreatVectors } from '@/components/three/ThreatVectors';
import { InterceptionField } from '@/components/three/InterceptionField';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function ThreatMatrixScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  const isVisible = activeScene === 9;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 9}>
      
      <group>
        <ambientLight intensity={0.08} color={PALETTE.coldSteel} />
        <pointLight 
          position={[0, 0, 0]} 
          intensity={1.4} 
          color={PALETTE.threatAmber} 
          distance={32} 
        />
      </group>


      <ThreatVectors progress={activeScene === 9 ? progress : 1} />
      <InterceptionField progress={activeScene === 9 ? progress : 1} />

    </group>
  );
}
