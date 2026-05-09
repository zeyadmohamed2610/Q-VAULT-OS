// ═══════════════════════════════════════════════════════════════
// HARDWARE REALITY LAYER
// Believable infrastructure diagrams. PCB traces. Enclave maps.
// Manufacturing-grade lighting and monochromatic precision.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useMemo } from 'react';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

export function HardwareDiagrams({ type = 'pcb', position = [0,0,0], scale = 1 }) {
  const lineGeometry = useMemo(() => {
    if (type === 'pcb') {
      const points = [];
      // Generate industrial PCB trace patterns
      for (let i = 0; i < 40; i++) {
        const startX = (Math.random() - 0.5) * 10;
        const startZ = (Math.random() - 0.5) * 10;
        
        // 90-degree trace logic
        const midX = startX + (Math.random() - 0.5) * 2;
        const midZ = startZ;
        const endX = midX;
        const endZ = midZ + (Math.random() - 0.5) * 2;
        
        points.push(new THREE.Vector3(startX, 0, startZ));
        points.push(new THREE.Vector3(midX, 0, midZ));
        points.push(new THREE.Vector3(endX, 0, endZ));
      }
      return new THREE.BufferGeometry().setFromPoints(points);
    }
    
    if (type === 'enclave') {
      // Secure enclave boundary diagram
      const pts = [];
      const radius = 2;
      for (let i = 0; i <= 64; i++) {
        const a = (i / 64) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(a) * radius, 0, Math.sin(a) * radius));
      }
      // Add cross-hatching or inner grid
      for (let i = -radius; i <= radius; i += 0.5) {
        pts.push(new THREE.Vector3(i, 0, -radius), new THREE.Vector3(i, 0, radius));
      }
      return new THREE.BufferGeometry().setFromPoints(pts);
    }

    return new THREE.BufferGeometry();
  }, [type]);

  const mat = useMemo(() => new THREE.LineBasicMaterial({
    color: type === 'pcb' ? PALETTE.sovereignCyan : PALETTE.coldSteel,
    transparent: true,
    opacity: 0.15,
    blending: THREE.AdditiveBlending,
  }), []);

  return (
    <group position={position as any} scale={scale as any}>
      <lineSegments geometry={lineGeometry} material={mat} />
      
      {/* Central "Enclave" marker for 'enclave' type */}
      {type === 'enclave' && (
        <mesh rotation-x={-Math.PI / 2}>
          <planeGeometry args={[0.5, 0.5]} />
          <meshBasicMaterial color={PALETTE.sovereignCyan} transparent opacity={0.26} />
        </mesh>
      )}
    </group>
  );
}

/**
 * ML-KEM Lifecycle Visualization
 * Visualizes the 3 steps: KeyGen -> Encaps -> Decaps
 */
export function MLKEMLifecycle({ position = [0,0,0] }) {
  return (
    <group position={position as any}>
      {/* 3 stages as volumetric boxes or wireframes */}
      {[0, 1, 2].map((i) => (
        <group key={i} position={[i * 3 - 3, 0, 0]}>
          <mesh>
            <boxGeometry args={[2, 0.05, 2]} />
            <meshBasicMaterial color={PALETTE.institutionalWhite} wireframe transparent opacity={0.1} />
          </mesh>
          <mesh position-y={0.5}>
            <sphereGeometry args={[0.1, 8, 8]} />
            <meshBasicMaterial color={PALETTE.sovereignCyan} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
