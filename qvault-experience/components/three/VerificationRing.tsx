// ═══════════════════════════════════════════════════════════════
// VERIFICATION RING
// Pulses across the chamber to simulate proof verification.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { verificationRingVert, verificationRingFrag } from '@/shaders/zkShaders';
import { FILM_MOTION_SCALE } from '@/lib/MasteringPipeline';

interface VerificationRingProps {
  progress: number;
}

export function VerificationRing({ progress }: VerificationRingProps) {
  const shaderRef = useRef<THREE.ShaderMaterial>(null);

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 }
  }), []);

  useFrame((state) => {
    if (shaderRef.current) {
      shaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      shaderRef.current.uniforms.uProgress.value += (progress - shaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <group>
      {/* Expanding Spherical Pulse */}
      <mesh scale={15}>
        <sphereGeometry args={[1, 64, 64]} />
        <shaderMaterial
          ref={shaderRef}
          vertexShader={verificationRingVert}
          fragmentShader={verificationRingFrag}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}
