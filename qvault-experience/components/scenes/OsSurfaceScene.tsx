// ═══════════════════════════════════════════════════════════════
// SCENE 7: OS SURFACE
// The Central Mind: Military cyber command operating system.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { FloatingPanels } from '@/components/three/FloatingPanels';
import { OsEnvironment } from '@/components/three/OsEnvironment';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function OsSurfaceScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 6 && activeScene <= 8;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 7 || activeScene === 8}>
      
      {/* 
        CYBER COMMAND LIGHTING 
        Institutional, monochromatic, high contrast.
      */}
      <group>
        <ambientLight intensity={0.05} color={PALETTE.institutionalWhite} />
        <pointLight position={[0, 5, 0]} color={PALETTE.sovereignCyan} intensity={1.1} distance={30} />
        <pointLight position={[-10, -5, -10]} color={PALETTE.coldSteel} intensity={1.2} distance={40} />
        <pointLight position={[10, 5, 10]} color={PALETTE.institutionalWhite} intensity={0.8} distance={30} />
      </group>


      <OsEnvironment progress={activeScene === 7 ? progress : 1} />
      <FloatingPanels progress={activeScene === 7 ? progress : 1} />

    </group>
  );
}
