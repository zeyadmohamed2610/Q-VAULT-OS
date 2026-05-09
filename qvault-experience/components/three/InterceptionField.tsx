// ═══════════════════════════════════════════════════════════════
// INTERCEPTION FIELD
// Defensive barriers and containment systems (Scene 9).
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { interceptionPulseVert, interceptionPulseFrag, containmentFieldVert, containmentFieldFrag } from '@/shaders/threatMatrixShaders';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface InterceptionFieldProps {
  progress: number;
}

export function InterceptionField({ progress }: InterceptionFieldProps) {
  const pulseShaderRef = useRef<THREE.ShaderMaterial>(null);
  const containmentShaderRef = useRef<THREE.ShaderMaterial>(null);

  const pulseUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.threatAmber) }
  }), []);

  const containmentUniforms = useMemo(() => ({
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.emergencyRed) }
  }), []);

  useFrame((state) => {
    if (pulseShaderRef.current) {
      pulseShaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      pulseShaderRef.current.uniforms.uProgress.value += (progress - pulseShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
    if (containmentShaderRef.current) {
      containmentShaderRef.current.uniforms.uProgress.value += (progress - containmentShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <group>
      {/* Interception pulses */}
      <mesh>
        <sphereGeometry args={[4, 32, 32]} />
        <shaderMaterial
          ref={pulseShaderRef}
          vertexShader={interceptionPulseVert}
          fragmentShader={interceptionPulseFrag}
          uniforms={pulseUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Final containment shield */}
      <mesh>
        <icosahedronGeometry args={[5, 3]} />
        <shaderMaterial
          ref={containmentShaderRef}
          vertexShader={containmentFieldVert}
          fragmentShader={containmentFieldFrag}
          uniforms={containmentUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          wireframe={true}
        />
      </mesh>
    </group>
  );
}
