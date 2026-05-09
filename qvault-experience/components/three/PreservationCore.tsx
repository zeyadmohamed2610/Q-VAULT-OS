// ═══════════════════════════════════════════════════════════════
// PRESERVATION CORE
// The aged, battle-tested hardware artifact suspended in time.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

interface PreservationCoreProps {
  progress: number;
}

export function PreservationCore({ progress }: PreservationCoreProps) {
  const groupRef = useRef<THREE.Group>(null);

  const timeRef = useRef(0);

  useFrame((state, delta) => {
    if (groupRef.current) {
      const speed = 1.0 - Math.pow(Math.min(1, Math.max(0, progress - 0.8) / 0.2), 2) * 0.95;
      timeRef.current += delta * speed;
      
      // Extremely slow, reverent rotation
      groupRef.current.rotation.y = timeRef.current * 0.02;
      groupRef.current.position.y = Math.sin(timeRef.current * 0.1) * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      {/* 
        The global HardwareModel from SceneDispatcher is present here.
        We rely on the scene's cryogenic lighting to give it an aged, preserved look. 
      */}
      
      {/* Preservation Glow Base */}
      <mesh position={[0, -2, 0]}>
        <cylinderGeometry args={[2, 2.5, 0.5, 32]} />
        <meshStandardMaterial color={PALETTE.graphite} roughness={0.8} metalness={0.6} />
      </mesh>
      
      {/* Subtle emissive ring holding the hardware */}
      <mesh position={[0, -1.7, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.8, 2.0, 64]} />
        <meshBasicMaterial color={PALETTE.sovereignCyan} transparent opacity={0.12} />
      </mesh>
    </group>
  );
}
