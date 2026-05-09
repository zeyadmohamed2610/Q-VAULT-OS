// ═══════════════════════════════════════════════════════════════
// SCENE 5: ZERO KNOWLEDGE
// A sealed cryptographic state visualizing invisible proof.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { SecretCore } from '@/components/three/SecretCore';
import { ProofField } from '@/components/three/ProofField';
import { VerificationRing } from '@/components/three/VerificationRing';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function ZeroKnowledgeScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 4 && activeScene <= 6;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 5 || activeScene === 6}>
      
      {/* 
        BLACK-SITE LIGHTING 
        Only the verification pulses and proof trails provide light.
        Deep darkness.
      */}
      <group>
        <spotLight
          position={[0, 10, 0]}
          angle={0.2}
          penumbra={1.0}
          intensity={1.2}
          color={PALETTE.sovereignCyan}
        />
        <ambientLight intensity={0.04} color={PALETTE.coldSteel} />
      </group>

      <SecretCore progress={activeScene === 5 ? progress : 1} />
      <ProofField progress={activeScene === 5 ? progress : 1} />
      <VerificationRing progress={activeScene === 5 ? progress : 1} />

    </group>
  );
}
