// ═══════════════════════════════════════════════════════════════
// SECRET CORE
// The cryptographic payload that must remain invisible.
// Uses complex refraction, noise, and procedural masking to hide it.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { entropyDistortionVert, entropyDistortionFrag } from '@/shaders/zkShaders';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface SecretCoreProps {
  progress: number;
}

export function SecretCore({ progress }: SecretCoreProps) {
  const shaderRef = useRef<THREE.ShaderMaterial>(null);
  const meshRef = useRef<THREE.Mesh>(null);

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColorBase: { value: new THREE.Color(PALETTE.deepGraphite) },
    uColorVapor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  useFrame((state) => {
    if (shaderRef.current) {
      shaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      // Smooth progress update for distortion mechanics
      shaderRef.current.uniforms.uProgress.value += (progress - shaderRef.current.uniforms.uProgress.value) * 0.1;
    }
    
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.45;
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.22;
    }
  });

  return (
    <group>
      {/* Outer Obscuring Shell */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[2, 16]} />
        <shaderMaterial
          ref={shaderRef}
          vertexShader={entropyDistortionVert}
          fragmentShader={entropyDistortionFrag}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* 
        The "Actual" Secret. 
        It is purely black, absorbing light, representing the sealed cryptographic state.
        As the progress increases, it shrinks into nothingness (vaporization).
      */}
      <mesh scale={1.8 * Math.max(0, 1.0 - Math.pow(progress, 3.0))}>
        <icosahedronGeometry args={[1, 4]} />
        <meshBasicMaterial color={PALETTE.deepGraphite} />
      </mesh>
    </group>
  );
}
