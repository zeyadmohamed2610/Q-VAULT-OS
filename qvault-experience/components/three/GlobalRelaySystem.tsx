// ═══════════════════════════════════════════════════════════════
// GLOBAL RELAY SYSTEM — Three.js
// Orbital governance rings + intercontinental trust corridors.
// Appears during Governance (Scene 8) and Threat Matrix (Scene 9).
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useSovereignState } from '@/lib/PersistentStateEngine';

// Three orbital rings at different inclinations
const ORBITAL_RINGS = [
  { radius: 5.2, tilt: 0.0,   speed: 0.008,  color: '#00e6ff' },
  { radius: 6.8, tilt: 0.55,  speed: -0.005, color: '#0088aa' },
  { radius: 8.5, tilt: 1.1,   speed: 0.004,  color: '#004466' },
];

function OrbitalRing({
  radius,
  tilt,
  speed,
  color,
  opacity,
}: {
  radius: number;
  tilt: number;
  speed: number;
  color: string;
  opacity: number;
}) {
  const ref = useRef<THREE.Group>(null);

  // Construct ring geometry
  const curve = useMemo(() => new THREE.EllipseCurve(0, 0, radius, radius, 0, Math.PI * 2, false, 0), [radius]);
  const points = useMemo(() => curve.getPoints(80).map(p => new THREE.Vector3(p.x, 0, p.y)), [curve]);
  const geo = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  // Relay pulses along the ring — 3 packets
  const packetRefs = [useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null)];

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y += speed;

    packetRefs.forEach((pRef, i) => {
      if (!pRef.current) return;
      const t = (clock.elapsedTime * 0.4 + i / 3) % 1;
      const idx = Math.floor(t * (points.length - 1));
      const p = points[idx];
      if (p) {
        pRef.current.position.set(p.x, p.y, p.z);
      }
    });
  });

  return (
    <group ref={ref} rotation={[tilt, 0, 0]}>
      <lineLoop geometry={geo}>
        <lineBasicMaterial color={color} transparent opacity={opacity * 0.3} depthWrite={false} />
      </lineLoop>

      {/* Relay packets */}
      {packetRefs.map((pRef, i) => (
        <mesh ref={pRef} key={i}>
          <sphereGeometry args={[0.04, 4, 4]} />
          <meshBasicMaterial color={color} transparent opacity={opacity * 0.8} />
        </mesh>
      ))}
    </group>
  );
}

export function GlobalRelaySystem({ visible = true }: { visible?: boolean }) {
  const sys = useSovereignState();
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = clock.elapsedTime * 0.005;
    }
  });

  if (!visible) return null;

  const baseOpacity = Math.min(1, sys.trustScore * 1.05);

  return (
    <group ref={groupRef}>
      {ORBITAL_RINGS.map((ring, i) => (
        <OrbitalRing key={i} {...ring} opacity={baseOpacity} />
      ))}

      {/* Central governance sphere — very faint */}
      <mesh>
        <sphereGeometry args={[0.6, 16, 16]} />
        <meshStandardMaterial
          color="#001a2e"
          emissive="#003355"
          emissiveIntensity={0.4}
          transparent
          opacity={0.5}
          wireframe
        />
      </mesh>
    </group>
  );
}
