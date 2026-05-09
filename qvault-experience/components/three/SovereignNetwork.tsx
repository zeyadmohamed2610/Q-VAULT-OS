// ═══════════════════════════════════════════════════════════════
// SOVEREIGN NETWORK — Three.js
// Planetary-scale cryptographic relay visualization.
// Instanced lines + node clusters. Zero per-frame allocations.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSovereignState } from '@/lib/PersistentStateEngine';

// 12 sovereign nodes, geographically distributed on a sphere
const NODE_POSITIONS = [
  [0, 1.8, 0],
  [1.4, 1.0, 0.8],
  [-1.4, 1.0, 0.8],
  [0.8, -0.5, 1.6],
  [-0.8, -0.5, 1.6],
  [1.6, -0.6, -0.8],
  [-1.6, -0.6, -0.8],
  [0, -1.8, 0.3],
  [0.9, 0.6, -1.6],
  [-0.9, 0.6, -1.6],
  [1.8, 0.2, 0.2],
  [-1.8, 0.2, 0.2],
].map(([x, y, z]) => new THREE.Vector3(x, y, z).normalize().multiplyScalar(3.5));

// Relay connections (pairs of node indices)
const RELAYS = [
  [0, 1], [0, 2], [1, 2], [1, 3], [2, 4], [3, 5], [4, 6],
  [5, 7], [6, 7], [3, 8], [4, 9], [8, 10], [9, 11],
  [10, 5], [11, 6], [0, 8], [0, 9], [7, 10], [7, 11],
];

function RelayLine({
  start,
  end,
  opacity,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  opacity: number;
}) {
  const ref = useRef<THREE.LineSegments>(null);
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry().setFromPoints([start, end]);
    return g;
  }, [start, end]);

  useFrame(({ clock }) => {
    if (ref.current) {
      const mat = ref.current.material as THREE.LineBasicMaterial;
      mat.opacity = opacity * (0.3 + 0.15 * Math.sin(clock.elapsedTime * 0.8 + start.x));
    }
  });

  return (
    <lineSegments ref={ref} geometry={geo}>
      <lineBasicMaterial
        color="#ffffff"
        transparent
        opacity={opacity * 0.35}
        depthWrite={false}
      />
    </lineSegments>
  );
}

export function SovereignNetwork({ visible = true }: { visible?: boolean }) {
  const sys = useSovereignState();
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    if (groupRef.current) {
      // Very slow axial rotation — feels like orbital drift
      groupRef.current.rotation.y = clock.elapsedTime * 0.018;
      groupRef.current.rotation.x = Math.sin(clock.elapsedTime * 0.006) * 0.04;
    }
  });

  if (!visible) return null;

  // Scale relay opacity with system trust score
  const relayOpacity = sys.trustScore;

  return (
    <group ref={groupRef}>
      {/* Relay lines */}
      {RELAYS.map(([a, b], i) => (
        <RelayLine
          key={i}
          start={NODE_POSITIONS[a]}
          end={NODE_POSITIONS[b]}
          opacity={relayOpacity}
        />
      ))}

      {/* Node clusters */}
      {NODE_POSITIONS.map((pos, i) => {
        const isOnline = i < sys.activeNodes / (sys.totalNodes / NODE_POSITIONS.length);
        return (
          <group key={i} position={[pos.x, pos.y, pos.z]}>
            {/* Core node */}
            <mesh>
              <sphereGeometry args={[0.045, 6, 6]} />
              <meshStandardMaterial
                color={isOnline ? '#00e6ff' : '#ff1a44'}
                emissive={isOnline ? '#00e6ff' : '#ff1a44'}
                emissiveIntensity={isOnline ? 1.2 : 0.4}
                transparent
                opacity={isOnline ? 0.9 : 0.3}
              />
            </mesh>
            {/* Outer pulse ring */}
            <mesh>
              <ringGeometry args={[0.06, 0.08, 12]} />
              <meshBasicMaterial
                color="#00e6ff"
                transparent
                opacity={0.15}
                side={THREE.DoubleSide}
                depthWrite={false}
              />
            </mesh>
          </group>
        );
      })}

      {/* Atmosphere sphere — very faint */}
      <mesh>
        <sphereGeometry args={[3.6, 32, 32]} />
        <meshBasicMaterial
          color="#001a2e"
          transparent
          opacity={0.04}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
