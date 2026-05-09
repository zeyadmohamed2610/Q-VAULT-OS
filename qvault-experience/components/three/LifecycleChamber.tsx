// ═══════════════════════════════════════════════════════════════
// LIFECYCLE CHAMBER
// The massive central chamber holding the preservation artifact.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PreservationCore } from '@/components/three/PreservationCore';
import { TemporalRings } from '@/components/three/TemporalRings';
import { ContinuityField } from '@/components/three/ContinuityField';
import { PALETTE } from '@/lib/MasteringPipeline';

interface LifecycleChamberProps {
  progress: number;
}

export function LifecycleChamber({ progress }: LifecycleChamberProps) {
  const groupRef = useRef<THREE.Group>(null);

  const timeRef = useRef(0);

  useFrame((state, delta) => {
    if (groupRef.current) {
      const speed = 1.0 - Math.pow(Math.min(1, Math.max(0, progress - 0.8) / 0.2), 2) * 0.95;
      timeRef.current += delta * speed;
      
      groupRef.current.position.y = Math.sin(timeRef.current * 0.05) * 0.5;
    }
  });

  return (
    <group ref={groupRef}>
      <PreservationCore progress={progress} />
      <TemporalRings progress={progress} />
      <ContinuityField progress={progress} />
      
      {/* Massive Industrial Structure Elements */}
      <group position={[0, -10, 0]}>
        <mesh receiveShadow>
          <cylinderGeometry args={[15, 20, 2, 64]} />
          <meshStandardMaterial color={PALETTE.deepGraphite} roughness={0.9} metalness={0.8} />
        </mesh>
        {/* Docking struts */}
        {[0, 1, 2, 3].map(i => (
          <mesh key={i} position={[Math.cos(i * Math.PI/2) * 8, 4, Math.sin(i * Math.PI/2) * 8]} rotation={[0, -i * Math.PI/2, 0]}>
            <boxGeometry args={[1, 8, 2]} />
            <meshStandardMaterial color={PALETTE.graphite} roughness={0.7} metalness={0.5} />
          </mesh>
        ))}
      </group>
      
      <group position={[0, 10, 0]}>
        <mesh receiveShadow>
          <cylinderGeometry args={[20, 15, 2, 64]} />
          <meshStandardMaterial color={PALETTE.deepGraphite} roughness={0.9} metalness={0.8} />
        </mesh>
      </group>
    </group>
  );
}
