// ═══════════════════════════════════════════════════════════════
// SOVEREIGN PATHS
// Optical connections mapping the civilizational infrastructure roadmap.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { pathVert, pathFrag } from '@/shaders/roadmapShaders';
import { FILM_MOTION_SCALE } from '@/lib/MasteringPipeline';
import { PALETTE } from '@/lib/MasteringPipeline';

interface SovereignPathsProps {
  progress: number;
}

export function SovereignPaths({ progress }: SovereignPathsProps) {
  const lineShaderRef = useRef<THREE.ShaderMaterial>(null);

  // Generate continuous procedural paths stretching into Z
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const count = 500;
    const lines = 6;
    
    const positions = new Float32Array(count * lines * 3);
    
    for (let l = 0; l < lines; l++) {
      const radius = 4 + Math.random() * 4;
      const angleOffset = (l / lines) * Math.PI * 2;
      
      for (let i = 0; i < count; i++) {
        const z = -(i / count) * 62;
        const index = (l * count + i) * 3;
        
        // Helical/orbital structure around the center
        const angle = angleOffset + z * 0.05;
        
        positions[index] = Math.cos(angle) * radius;
        positions[index + 1] = Math.sin(angle) * radius;
        positions[index + 2] = z;
      }
    }
    
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  useFrame((state) => {
    if (lineShaderRef.current) {
      lineShaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      lineShaderRef.current.uniforms.uProgress.value += (progress - lineShaderRef.current.uniforms.uProgress.value) * 0.1;
    }
  });

  return (
    <lineSegments geometry={geometry}>
      <shaderMaterial
        ref={lineShaderRef}
        vertexShader={pathVert}
        fragmentShader={pathFrag}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </lineSegments>
  );
}
