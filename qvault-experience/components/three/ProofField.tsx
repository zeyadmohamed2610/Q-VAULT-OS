// ═══════════════════════════════════════════════════════════════
// PROOF FIELD
// Instanced particle system handling proof trails and vaporization.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { proofPlasmaVert, proofPlasmaFrag } from '@/shaders/zkShaders';
import { FILM_MOTION_SCALE } from '@/lib/MasteringPipeline';

interface ProofFieldProps {
  progress: number;
}

export function ProofField({ progress }: ProofFieldProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  const COUNT = 1800;

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 }
  }), []);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    
    // We only need a point per instance, so a single vertex geometry is fine, 
    // or we can use a small quad. We will use Points/ShaderMaterial approach directly on InstancedBufferGeometry,
    // wait, if we use InstancedMesh we need a base geometry. Let's use a small Plane.
    const baseGeo = new THREE.PlaneGeometry(0.1, 0.1);
    
    const offsets = new Float32Array(COUNT * 3);
    const velocities = new Float32Array(COUNT * 3);
    const life = new Float32Array(COUNT);
    const sizes = new Float32Array(COUNT);
    
    for (let i = 0; i < COUNT; i++) {
      // Start clustered tightly around the core
      const r = 2.0 * Math.cbrt(Math.random());
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.acos(2 * Math.random() - 1);
      
      offsets[i*3] = r * Math.sin(phi) * Math.cos(theta);
      offsets[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
      offsets[i*3+2] = r * Math.cos(phi);
      
      // Random velocity vector for explosion
      velocities[i*3] = (Math.random() - 0.5) * 2.0;
      velocities[i*3+1] = (Math.random() - 0.5) * 2.0;
      velocities[i*3+2] = (Math.random() - 0.5) * 2.0;
      
      life[i] = Math.random();
      sizes[i] = 0.12 + Math.random() * 0.45;
    }
    
    baseGeo.setAttribute('aOffset', new THREE.InstancedBufferAttribute(offsets, 3));
    baseGeo.setAttribute('aVelocity', new THREE.InstancedBufferAttribute(velocities, 3));
    baseGeo.setAttribute('aLife', new THREE.InstancedBufferAttribute(life, 1));
    baseGeo.setAttribute('aSize', new THREE.InstancedBufferAttribute(sizes, 1));
    
    return baseGeo;
  }, []);

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      // Smoothly track progress
      materialRef.current.uniforms.uProgress.value += (progress - materialRef.current.uniforms.uProgress.value) * 0.05;
    }
  });

  return (
    <instancedMesh ref={meshRef} args={[geometry, undefined, COUNT]}>
      <shaderMaterial
        ref={materialRef}
        vertexShader={proofPlasmaVert}
        fragmentShader={proofPlasmaFrag}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </instancedMesh>
  );
}
