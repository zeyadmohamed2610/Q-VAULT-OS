// ═══════════════════════════════════════════════════════════════
// STACK LAYER (TRUST STACK)
// A single floating architectural layer in the Trust Stack.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Materials } from '@/lib/materials';

interface StackLayerProps {
  position: [number, number, number];
  index: number;
  label: string;
  progress: number; // Overall scene progress
}

export function StackLayer({ position, index, label, progress }: StackLayerProps) {
  const groupRef = useRef<THREE.Group>(null);
  const ringMaterialRef = useRef<THREE.MeshStandardMaterial>(null);
  
  // Calculate specific activation progress for this layer
  // Bottom layer activates first, top layer last
  const activationThreshold = 0.1 + (index * 0.15); // 0.1 to 0.85
  const isActivated = progress > activationThreshold;

  // Each layer rotates slowly at a slightly different speed/direction
  const rotSpeed = useMemo(() => (index % 2 === 0 ? 1 : -1) * (0.05 + Math.random() * 0.05), [index]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    
    // Idle rotation
    groupRef.current.rotation.y += rotSpeed * delta;
    
    // Slight vertical floating
    const floatOffset = Math.sin(state.clock.elapsedTime * 0.5 + index) * 0.1;
    groupRef.current.position.y = position[1] + floatOffset;

    // Emissive activation
    if (ringMaterialRef.current) {
      const targetIntensity = isActivated ? 0.75 : 0.08;
      ringMaterialRef.current.emissiveIntensity += (targetIntensity - ringMaterialRef.current.emissiveIntensity) * 0.05;
    }
  });

  return (
    <group ref={groupRef} position={position}>
      {/* Main Base Ring */}
      <mesh material={Materials.machinedSteel} castShadow receiveShadow>
        <torusGeometry args={[3, 0.4, 16, 64]} />
      </mesh>
      
      {/* Inner Data Ring */}
      <mesh material={Materials.carbonAnodized} rotation={[Math.PI / 2, 0, 0]} receiveShadow>
        <cylinderGeometry args={[2.5, 2.5, 0.2, 32]} />
      </mesh>

      {/* Emissive Edge Channel */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[2.4, 0.05, 8, 32]} />
        <meshStandardMaterial 
          ref={ringMaterialRef}
          color={Materials.emissiveInstitutional.color}
          emissive={Materials.emissiveInstitutional.emissive}
          emissiveIntensity={0}
          toneMapped={true}
        />
      </mesh>

      {/* Outer Structural Nodes */}
      {Array.from({ length: 6 }).map((_, i) => {
        const angle = (i * Math.PI * 2) / 6;
        return (
          <mesh 
            key={`node-${i}`} 
            position={[Math.cos(angle) * 3.6, 0, Math.sin(angle) * 3.6]}
            material={Materials.darkCeramic}
            castShadow
          >
            <boxGeometry args={[0.5, 0.6, 0.5]} />
          </mesh>
        );
      })}
    </group>
  );
}
