// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Cinematic Memory Fabric (Phase XIV)
// Visualizes faint, ghost-like traces of previous infrastructure states.
// Floating cryptographic particles and historical scene indices.
// Architectural. Ephemeral. Persistent.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useExperienceStore } from '@/lib/store';
import { directiveEngine } from '@/lib/DirectiveEngine';
import * as THREE from 'three';

const PARTICLE_COUNT = 90;
const BOUNDS = 80;

export function MemoryFabric() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const meshRef = useRef<THREE.Points>(null!);
  
  // ── Persistent memory positions ──
  const { positions, originalPos } = useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    const orig = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const x = (Math.random() - 0.5) * BOUNDS;
      const y = (Math.random() - 0.5) * BOUNDS;
      const z = (Math.random() - 0.5) * BOUNDS;
      pos.set([x, y, z], i * 3);
      orig.set([x, y, z], i * 3);
    }
    return { positions: pos, originalPos: orig };
  }, []);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const de = directiveEngine.state;
    const geometry = meshRef.current.geometry;
    const attr = geometry.attributes.position;

    // Fade particles based on scene tension
    const baseOpacity = 0.012 + Math.max(0, de.tensionVector) * 0.018;
    (meshRef.current.material as THREE.PointsMaterial).opacity = baseOpacity;

    // Gentle floating motion + attraction to scene center
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      const ix = originalPos[i3];
      const iy = originalPos[i3 + 1];
      const iz = originalPos[i3 + 2];

      const driftX = Math.sin(t * 0.2 + i) * 0.05;
      const driftY = Math.cos(t * 0.3 + i) * 0.05;
      const driftZ = Math.sin(t * 0.4 + i) * 0.05;

      // Influence by active scene (subtle pull)
      const pull = 0.01 * (activeScene + 1);
      
      attr.setX(i, ix + driftX + Math.sin(t * 0.1) * pull);
      attr.setY(i, iy + driftY + Math.cos(t * 0.1) * pull);
      attr.setZ(i, iz + driftZ);
    }
    
    attr.needsUpdate = true;
    meshRef.current.rotation.y = t * 0.02;
  });

  return (
    <points ref={meshRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.8}
        color="#ffffff"
        transparent
        opacity={0.018}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        sizeAttenuation={false}
      />
    </points>
  );
}
