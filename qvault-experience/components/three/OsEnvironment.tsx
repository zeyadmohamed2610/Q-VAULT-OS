// ═══════════════════════════════════════════════════════════════
// OS ENVIRONMENT
// The Brutalist 3D Grid and volumetric space for the OS Surface.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { environmentGridVert, environmentGridFrag } from '@/shaders/osSurfaceShaders';
import { PALETTE } from '@/lib/MasteringPipeline';

interface OsEnvironmentProps {
  progress: number;
}

export function OsEnvironment({ progress }: OsEnvironmentProps) {
  const gridShaderRef = useRef<THREE.ShaderMaterial>(null);

  const gridUniforms = useMemo(() => ({
    uProgress: { value: 0.08 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  useFrame(() => {
    if (gridShaderRef.current) {
      gridShaderRef.current.uniforms.uProgress.value += (progress - gridShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <group>
      {/* Massive Room Box */}
      <mesh scale={50}>
        <boxGeometry args={[1, 1, 1]} />
        <shaderMaterial
          ref={gridShaderRef}
          vertexShader={environmentGridVert}
          fragmentShader={environmentGridFrag}
          uniforms={gridUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}
