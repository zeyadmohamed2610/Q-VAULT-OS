// ═══════════════════════════════════════════════════════════════
// GOVERNANCE CORE
// The sovereign cryptographic authority monolith.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

interface GovernanceCoreProps {
  progress: number;
}

export function GovernanceCore({ progress }: GovernanceCoreProps) {
  const coreRef = useRef<THREE.Group>(null);
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const time = state.clock.elapsedTime;
    
    if (coreRef.current) {
      coreRef.current.rotation.y = time * 0.075;
    }
    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = time * 0.15;
      ring1Ref.current.rotation.y = time * 0.22;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x = -time * 0.22;
      ring2Ref.current.rotation.z = time * 0.15;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.y = -time * 0.08;
      ring3Ref.current.rotation.z = -time * 0.3;
    }
  });

  return (
    <group ref={coreRef}>
      {/* Central Monolith */}
      <mesh>
        <octahedronGeometry args={[4, 0]} />
        <meshStandardMaterial 
          color={PALETTE.deepGraphite} 
          metalness={0.9} 
          roughness={0.1} 
          emissive={PALETTE.sovereignCyan}
          emissiveIntensity={0.08}
          wireframe={false}
        />
      </mesh>
      <mesh scale={1.01}>
        <octahedronGeometry args={[4, 0]} />
        <meshBasicMaterial 
          color={PALETTE.coldSteel} 
          wireframe 
          transparent 
          opacity={0.18} 
          blending={THREE.AdditiveBlending} 
        />
      </mesh>

      {/* Authority Rings */}
      <mesh ref={ring1Ref}>
        <torusGeometry args={[6, 0.05, 16, 100]} />
        <meshBasicMaterial color={PALETTE.institutionalWhite} transparent opacity={0.28} />
      </mesh>
      <mesh ref={ring2Ref}>
        <torusGeometry args={[8, 0.02, 16, 100]} />
        <meshBasicMaterial color={PALETTE.sovereignCyan} transparent opacity={0.08} />
      </mesh>
      <mesh ref={ring3Ref}>
        <torusGeometry args={[10, 0.1, 16, 100]} />
        <meshBasicMaterial color={PALETTE.institutionalWhite} transparent opacity={0.16} />
      </mesh>
    </group>
  );
}
