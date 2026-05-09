// ═══════════════════════════════════════════════════════════════
// SCENE 4: PROTOCOL LAB
// A cinematic chamber visualizing the Q-Vault cryptographic handshake.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { ProtocolCore } from '@/components/three/ProtocolCore';
import { PacketStreams } from '@/components/three/PacketStreams';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export default function ProtocolLabScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);

  // Mount logic
  const isVisible = activeScene >= 3 && activeScene <= 5;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 4 || activeScene === 5}>
      
      {/* 
        LABORATORY LIGHTING 
        Clinical, high contrast, industrial.
      */}
      <group>
        {/* Core overhead light */}
        <spotLight
          position={[0, 15, 0]}
          angle={0.5}
          penumbra={0.8}
          intensity={7.0}
          color={PALETTE.institutionalWhite}
          castShadow
        />
        {/* Side architectural lights */}
        <spotLight position={[10, 5, 10]} angle={0.4} penumbra={1} intensity={1.1} color={PALETTE.sovereignCyan} />
        <spotLight position={[-10, 0, -10]} angle={0.4} penumbra={1} intensity={1.0} color={PALETTE.coldSteel} />
        <ambientLight intensity={0.08} color={PALETTE.coldSteel} />
      </group>

      {/* Heavy depth fog representing a sealed environment */}

      {/* The Central Chamber Objects */}
      <group scale={0.72}>
        <ProtocolCore progress={activeScene === 4 ? progress : 1} />
        <PacketStreams progress={activeScene === 4 ? progress : 1} />
      </group>
      
      {/* Architectural enclosure (subtle pillars) */}
      {Array.from({ length: 8 }).map((_, i) => {
        const angle = (i * Math.PI * 2) / 8;
        return (
          <mesh key={`pillar-${i}`} position={[Math.cos(angle) * 8, 0, Math.sin(angle) * 8]} receiveShadow>
            <cylinderGeometry args={[0.5, 0.5, 20, 16]} />
            <meshStandardMaterial color={PALETTE.deepGraphite} roughness={0.9} metalness={0.5} />
          </mesh>
        );
      })}

    </group>
  );
}
