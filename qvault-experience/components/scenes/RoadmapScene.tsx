// ═══════════════════════════════════════════════════════════════
// SCENE 11: ROADMAP
// Strategic Cryptographic Horizon Visualization.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { SovereignPaths } from '@/components/three/SovereignPaths';
import { FutureMilestones } from '@/components/three/FutureMilestones';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function RoadmapScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 10 && activeScene <= 12;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 11 || activeScene === 12}>
      
      <group>
        <ambientLight intensity={0.04} color={PALETTE.coldSteel} />
        <directionalLight position={[0, 50, -40]} intensity={2.4} color={PALETTE.institutionalWhite} />
      </group>


      <SovereignPaths progress={activeScene === 11 ? progress : 1} />
      <FutureMilestones progress={activeScene === 11 ? progress : 1} />

    </group>
  );
}
