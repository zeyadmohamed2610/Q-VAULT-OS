// ═══════════════════════════════════════════════════════════════
// PROTOCOL CORE
// The central cylinder inside the Protocol Chamber.
// Uses custom encryptionField shader to simulate the handshake.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { encryptionFieldVert, encryptionFieldFrag } from '@/shaders/protocolShaders';
import { Materials } from '@/lib/materials';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface ProtocolCoreProps {
  progress: number;
}

export function ProtocolCore({ progress }: ProtocolCoreProps) {
  const shaderRef = useRef<THREE.ShaderMaterial>(null);
  const ringGroupRef = useRef<THREE.Group>(null);
  
  // Calculate discrete protocol stage (0 to 5)
  // Maps continuous progress [0, 1] to 6 stages
  const stageIndex = Math.min(5, Math.floor(progress * 6));
  const stageProgress = progress; // continuous

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uStage: { value: 0 },
    uColorStable: { value: new THREE.Color(PALETTE.graphite) },
    uColorActive: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  useFrame((state) => {
    if (shaderRef.current) {
      shaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      // Smoothly approach the current stage value for color transition
      shaderRef.current.uniforms.uStage.value += (stageProgress - shaderRef.current.uniforms.uStage.value) * 0.1;
    }
    
    if (ringGroupRef.current) {
      // Rotate the mechanical rings
      ringGroupRef.current.rotation.y = state.clock.elapsedTime * 0.3;
    }
  });

  return (
    <group>
      {/* Central Quantum Core Cylinder */}
      <mesh>
        <cylinderGeometry args={[2, 2, 12, 64]} />
        <shaderMaterial
          ref={shaderRef}
          vertexShader={encryptionFieldVert}
          fragmentShader={encryptionFieldFrag}
          uniforms={uniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Solid inner ceramic core to give it physical weight */}
      <mesh material={Materials.darkCeramic} scale={[1.9, 11.8, 1.9]}>
        <cylinderGeometry args={[1, 1, 1, 32]} />
      </mesh>

      {/* 6 Mechanical Rings wrapping the core */}
      <group ref={ringGroupRef}>
        {Array.from({ length: 6 }).map((_, i) => {
          // Each ring represents a stage
          const isRingActive = stageIndex >= i;
          const yPos = 5 - i * 2;
          
          return (
            <group key={`ring-${i}`} position={[0, yPos, 0]}>
              <mesh material={Materials.machinedSteel} castShadow receiveShadow>
                <torusGeometry args={[2.5, 0.2, 16, 64]} />
              </mesh>
              
              {/* Emissive trigger on the ring */}
              <mesh rotation={[Math.PI/2, 0, 0]}>
                <torusGeometry args={[2.4, 0.05, 8, 32]} />
                <meshStandardMaterial 
                  color={Materials.emissiveInstitutional.color}
                  emissive={Materials.emissiveInstitutional.emissive}
                  emissiveIntensity={isRingActive ? 0.42 : 0}
                  toneMapped={true}
                />
              </mesh>
            </group>
          );
        })}
      </group>
    </group>
  );
}
