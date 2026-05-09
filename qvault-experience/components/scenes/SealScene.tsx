// ═══════════════════════════════════════════════════════════════
// SCENE 12: SEAL
// Ritualistic system closure.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { SealMechanism } from '@/components/three/SealMechanism';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function SealScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const lightRef = useRef<THREE.PointLight>(null);

  // Mount logic
  const isVisible = activeScene >= 11;

  useFrame(() => {
    if (activeScene === 12 && lightRef.current) {
      lightRef.current.intensity = Math.max(0.45, 2.2 * (1.0 - progress / 1.15));
    }
  });

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 12} position={[0, 14, -100]}>
      
      <group>
        <ambientLight intensity={0.05} color={PALETTE.coldSteel} />
        <pointLight ref={lightRef} position={[0, 0, 50]} intensity={3.0} color={PALETTE.sovereignCyan} distance={200} />
      </group>


      <SealMechanism progress={activeScene === 12 ? progress : 0} />

    </group>
  );
}
