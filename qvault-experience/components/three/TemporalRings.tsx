// ═══════════════════════════════════════════════════════════════
// TEMPORAL RINGS
// Orbital synchronization rings representing the passage of time.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { temporalRingVert, temporalRingFrag } from '@/shaders/lifecycleShaders';
import { PALETTE } from '@/lib/MasteringPipeline';

interface TemporalRingsProps {
  progress: number;
}

export function TemporalRings({ progress }: TemporalRingsProps) {
  const ring1ShaderRef = useRef<THREE.ShaderMaterial>(null);
  const ring2ShaderRef = useRef<THREE.ShaderMaterial>(null);
  const ring3ShaderRef = useRef<THREE.ShaderMaterial>(null);
  const groupRef = useRef<THREE.Group>(null);

  const createUniforms = (color: string) => useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(color) }
  }), [color]);

  const uniforms1 = createUniforms(PALETTE.institutionalWhite);
  const uniforms2 = createUniforms(PALETTE.sovereignCyan);
  const uniforms3 = createUniforms(PALETTE.coldSteel);

  const timeRef = useRef(0);

  useFrame((state, delta) => {
    // Slow down motion significantly as progress approaches 1.0
    const speed = 1.0 - Math.pow(Math.min(1, Math.max(0, progress - 0.8) / 0.2), 2) * 0.95;
    timeRef.current += delta * speed;
    const time = timeRef.current;
    
    [ring1ShaderRef, ring2ShaderRef, ring3ShaderRef].forEach(ref => {
      if (ref.current) {
        ref.current.uniforms.uTime.value = time;
        ref.current.uniforms.uProgress.value += (progress - ref.current.uniforms.uProgress.value) * 0.1;
      }
    });

    if (groupRef.current) {
      groupRef.current.children[0].rotation.x = time * 0.05;
      groupRef.current.children[0].rotation.y = time * 0.03;
      
      groupRef.current.children[1].rotation.x = -time * 0.04;
      groupRef.current.children[1].rotation.z = time * 0.06;
      
      groupRef.current.children[2].rotation.y = -time * 0.02;
      groupRef.current.children[2].rotation.z = -time * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      <mesh>
        <cylinderGeometry args={[6, 6, 0.35, 48, 1, true]} />
        <shaderMaterial
          ref={ring1ShaderRef}
          vertexShader={temporalRingVert}
          fragmentShader={temporalRingFrag}
          uniforms={uniforms1}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh>
        <cylinderGeometry args={[9, 9, 0.7, 48, 1, true]} />
        <shaderMaterial
          ref={ring2ShaderRef}
          vertexShader={temporalRingVert}
          fragmentShader={temporalRingFrag}
          uniforms={uniforms2}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh>
        <cylinderGeometry args={[13, 13, 1.1, 48, 1, true]} />
        <shaderMaterial
          ref={ring3ShaderRef}
          vertexShader={temporalRingVert}
          fragmentShader={temporalRingFrag}
          uniforms={uniforms3}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}
