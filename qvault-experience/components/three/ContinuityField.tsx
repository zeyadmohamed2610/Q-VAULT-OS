// ═══════════════════════════════════════════════════════════════
// CONTINUITY FIELD
// Cryogenic haze and archival scan fields representing longevity.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { cryogenicHazeVert, cryogenicHazeFrag, continuityScanVert, continuityScanFrag } from '@/shaders/lifecycleShaders';
import { PALETTE } from '@/lib/MasteringPipeline';

interface ContinuityFieldProps {
  progress: number;
}

export function ContinuityField({ progress }: ContinuityFieldProps) {
  const hazeShaderRef = useRef<THREE.ShaderMaterial>(null);
  const scanShaderRef = useRef<THREE.ShaderMaterial>(null);

  const hazeUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.graphite) }
  }), []);

  const scanUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  const timeRef = useRef(0);

  useFrame((state, delta) => {
    const speed = 1.0 - Math.pow(Math.min(1, Math.max(0, progress - 0.8) / 0.2), 2) * 0.95;
    timeRef.current += delta * speed;
    const time = timeRef.current;
    
    if (hazeShaderRef.current) {
      hazeShaderRef.current.uniforms.uTime.value = time;
      hazeShaderRef.current.uniforms.uProgress.value += (progress - hazeShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
    if (scanShaderRef.current) {
      scanShaderRef.current.uniforms.uTime.value = time;
      scanShaderRef.current.uniforms.uProgress.value += (progress - scanShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <group>
      {/* Cryogenic Volumetric Haze */}
      <mesh>
        <boxGeometry args={[40, 40, 40]} />
        <shaderMaterial
          ref={hazeShaderRef}
          vertexShader={cryogenicHazeVert}
          fragmentShader={cryogenicHazeFrag}
          uniforms={hazeUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Continuity Scan Field */}
      <mesh>
        <cylinderGeometry args={[20, 20, 40, 32, 1, true]} />
        <shaderMaterial
          ref={scanShaderRef}
          vertexShader={continuityScanVert}
          fragmentShader={continuityScanFrag}
          uniforms={scanUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}
