// ═══════════════════════════════════════════════════════════════
// FUTURE MILESTONES
// Floating structures in deep space representing infrastructure leaps.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { milestoneVert, milestoneFrag } from '@/shaders/roadmapShaders';
import { PALETTE } from '@/lib/MasteringPipeline';

interface FutureMilestonesProps {
  progress: number;
}

const MILESTONES = [
  { z: -12, p: 0.1, x: -5, y: 5 },
  { z: -22, p: 0.25, x: 6, y: 7 },
  { z: -34, p: 0.45, x: -4, y: 9 },
  { z: -46, p: 0.65, x: 5, y: 11 },
  { z: -58, p: 0.9, x: 0, y: 13 },
];

export function FutureMilestones({ progress }: FutureMilestonesProps) {
  const groupRef = useRef<THREE.Group>(null);
  
  // Custom shader materials per milestone so they trigger individually based on progress
  const materials = useMemo(() => {
    return MILESTONES.map(m => new THREE.ShaderMaterial({
      vertexShader: milestoneVert,
      fragmentShader: milestoneFrag,
      uniforms: {
        uProgress: { value: 0 },
        uRevealTrigger: { value: m.p },
        uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide
    }));
  }, []);

  useFrame((state) => {
    materials.forEach(mat => {
      mat.uniforms.uProgress.value += (progress - mat.uniforms.uProgress.value) * 0.1;
    });

    if (groupRef.current) {
      groupRef.current.children.forEach((child, i) => {
        // Slow structural spin
        child.rotation.x = state.clock.elapsedTime * 0.15 + i;
        child.rotation.y = state.clock.elapsedTime * 0.075 + i;
      });
    }
  });

  return (
    <group ref={groupRef}>
      {MILESTONES.map((m, i) => (
        <group key={i} position={[m.x, m.y, m.z]}>
          <mesh>
            <octahedronGeometry args={[1.0 + (i * 0.18), 0]} />
            <meshStandardMaterial color={PALETTE.deepGraphite} metalness={0.9} roughness={0.1} />
          </mesh>
          <mesh scale={1.2} material={materials[i]}>
            <sphereGeometry args={[1.35 + (i * 0.22), 24, 24]} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
