// ═══════════════════════════════════════════════════════════════
// THREAT VECTORS
// Instanced attack particles simulating hostile intrusion streams.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { attackVectorVert, attackVectorFrag } from '@/shaders/threatMatrixShaders';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface ThreatVectorsProps {
  progress: number;
}

export function ThreatVectors({ progress }: ThreatVectorsProps) {
  const shaderRef = useRef<THREE.ShaderMaterial>(null);
  
  const COUNT = 1800;

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    
    // Base positions (at the center, will be offset by shader)
    const positions = new Float32Array(COUNT * 3);
    const offsets = new Float32Array(COUNT);
    const trajectories = new Float32Array(COUNT * 3);
    
    for (let i = 0; i < COUNT; i++) {
      positions[i*3] = 0;
      positions[i*3+1] = 0;
      positions[i*3+2] = 0;
      
      offsets[i] = Math.random();
      
      // Random direction pointing OUTWARDS (shader will reverse this to point INWARDS)
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      
      trajectories[i*3] = Math.sin(phi) * Math.cos(theta);
      trajectories[i*3+1] = Math.sin(phi) * Math.sin(theta);
      trajectories[i*3+2] = Math.cos(phi);
    }
    
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('aOffset', new THREE.BufferAttribute(offsets, 1));
    geo.setAttribute('aTrajectory', new THREE.BufferAttribute(trajectories, 3));
    
    return geo;
  }, []);

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.threatAmber) }
  }), []);

  useFrame((state) => {
    if (shaderRef.current) {
      shaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      shaderRef.current.uniforms.uProgress.value += (progress - shaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <points geometry={geometry}>
      <shaderMaterial
        ref={shaderRef}
        vertexShader={attackVectorVert}
        fragmentShader={attackVectorFrag}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
