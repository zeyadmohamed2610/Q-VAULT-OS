// ═══════════════════════════════════════════════════════════════
// TOPOLOGY MAP — Deployment Reality Layer
// Sovereign node maps. Edge deployment diagrams.
// Visualizes the global reach and cryptographic quorum.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

const NODE_COUNT = 64;
const _matrix = new THREE.Matrix4();

export function TopologyMap({ position = [0, 0, 0], scale = 1 }) {
  const meshRef = useRef<THREE.Group>(null!);

  const { points, connections } = useMemo(() => {
    const pts = [];
    const connPoints = [];
    
    // Generate a globe-like distribution of nodes
    for (let i = 0; i < NODE_COUNT; i++) {
      const phi = Math.acos(-1 + (2 * i) / NODE_COUNT);
      const theta = Math.sqrt(NODE_COUNT * Math.PI) * phi;
      
      const r = 5;
      const x = r * Math.cos(theta) * Math.sin(phi);
      const y = r * Math.sin(theta) * Math.sin(phi);
      const z = r * Math.cos(phi);
      
      pts.push(new THREE.Vector3(x, y, z));
      
      // Connect to neighbors (probabilistic)
      if (i > 0 && Math.random() > 0.6) {
        connPoints.push(pts[i], pts[Math.floor(Math.random() * i)]);
      }
    }
    
    return { 
      points: pts, 
      connections: new THREE.BufferGeometry().setFromPoints(connPoints) 
    };
  }, []);

  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    color: PALETTE.institutionalWhite,
    transparent: true,
    opacity: 0.08,
  }), []);

  const nodeMat = useMemo(() => new THREE.MeshBasicMaterial({
    color: PALETTE.sovereignCyan,
    transparent: true,
    opacity: 0.4,
  }), []);

  const instancedRef = useRef<THREE.InstancedMesh>(null!);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.05;
    }
    
    // Update instances once
    if (instancedRef.current) {
      points.forEach((p, i) => {
        _matrix.setPosition(p);
        instancedRef.current.setMatrixAt(i, _matrix);
      });
      instancedRef.current.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <group ref={meshRef} position={position as any} scale={scale as any}>
      {/* Connections */}
      <lineSegments geometry={connections} material={lineMat} />
      
      {/* Nodes — Instanced for performance */}
      <instancedMesh ref={instancedRef} args={[null as any, null as any, NODE_COUNT]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial 
          color={PALETTE.sovereignCyan} 
          transparent 
          opacity={0.6}
        />
      </instancedMesh>

      {/* Atmospheric Glow (Subtle) */}
      <mesh>
        <sphereGeometry args={[4.9, 32, 32]} />
        <meshBasicMaterial color={PALETTE.institutionalWhite} wireframe transparent opacity={0.01} />
      </mesh>
    </group>
  );
}

/**
 * Edge Deployment Statistics Overlay (3D Label style)
 */
export function EdgeStats() {
  return (
    <group position={[6, 2, 0]}>
      {/* Text would normally use Drei Text, but we'll stick to geometry for authority */}
      <mesh>
        <planeGeometry args={[2, 1]} />
        <meshBasicMaterial color={PALETTE.deepGraphite} transparent opacity={0.5} />
      </mesh>
      <mesh position-z={0.01}>
        <planeGeometry args={[1.9, 0.9]} />
        <meshBasicMaterial color={PALETTE.institutionalWhite} wireframe transparent opacity={0.1} />
      </mesh>
    </group>
  );
}
