// ═══════════════════════════════════════════════════════════════
// GLOBAL OPERATIONAL LAYER — Phase XXV
// Planetary node synchronization. Submarine cable routing.
// Sovereign relay corridors with moving data traffic.
// Act III: PLANETARY AUTHORITY
// ═══════════════════════════════════════════════════════════════

'use client';

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';
import { useExperienceStore } from '@/lib/store';

const NODE_CLUSTERS = [
  { pos: [5, 2, 0], label: 'NA_EAST_CLUSTER' },
  { pos: [-4, 3, 2], label: 'EU_CENTRAL_CLUSTER' },
  { pos: [0, -4, 5], label: 'APAC_SOUTH_CLUSTER' },
];

export function GlobalOperationalLayer({ position = [0, 0, 0], scale = 1 }) {
  const meshRef = useRef<THREE.Group>(null!);
  const trafficMatRef = useRef<THREE.ShaderMaterial>(null!);
  
  const progress = useExperienceStore((s) => s.sceneProgress);
  const activeScene = useExperienceStore((s) => s.activeScene);

  const { points, cables, cablePaths } = useMemo(() => {
    const pts = [];
    const cablePoints = [];
    const paths: THREE.QuadraticBezierCurve3[] = [];
    
    // 1. Planetary Nodes — REDUCED (was 100, now 40)
    for (let i = 0; i < 40; i++) {
      const phi = Math.acos(-1 + (2 * i) / 40);
      const theta = Math.sqrt(40 * Math.PI) * phi;
      
      const r = 5;
      const x = r * Math.cos(theta) * Math.sin(phi);
      const y = r * Math.sin(theta) * Math.sin(phi);
      const z = r * Math.cos(phi);
      
      pts.push(new THREE.Vector3(x, y, z));
    }

    // 2. Cable Routes — REDUCED (was 15, now 8)
    for (let i = 0; i < 8; i++) {
      const p1 = pts[Math.floor(Math.random() * 10)];
      const p2 = pts[Math.floor(Math.random() * 40)];
      
      // Generate arc
      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5).normalize().multiplyScalar(5.5);
      const curve = new THREE.QuadraticBezierCurve3(p1, mid, p2);
      paths.push(curve);
      cablePoints.push(...curve.getPoints(20));
    }
    
    return { 
      points: pts, 
      cables: new THREE.BufferGeometry().setFromPoints(cablePoints),
      cablePaths: paths
    };
  }, []);

  // Line opacity: 0.04 (was 0.06) — product must dominate absolutely
  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    color: PALETTE.coldSteel,
    transparent: true,
    opacity: 0.04,
    blending: THREE.AdditiveBlending,
  }), []);

  // Point size/opacity: 0.016 / 0.18 — barely visible constellation
  const pointMat = useMemo(() => new THREE.PointsMaterial({
    color: PALETTE.institutionalWhite,
    size: 0.016,
    transparent: true,
    opacity: 0.18,
  }), []);

  const pointGeom = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  // Traffic nodes (data packets) travelling along the cables
  const trafficCount = 30; // 2 packets per cable
  const trafficPoints = useMemo(() => {
     return new Array(trafficCount).fill(0).map(() => new THREE.Vector3());
  }, []);
  const trafficGeom = useMemo(() => new THREE.BufferGeometry().setFromPoints(trafficPoints), [trafficPoints]);
  
  // State for traffic animation
  const trafficState = useMemo(() => {
    return new Array(trafficCount).fill(0).map((_, i) => ({
      pathIndex: i % cablePaths.length,
      t: Math.random(),
      speed: 0.1 + Math.random() * 0.2
    }));
  }, [cablePaths.length]);

  useFrame((state, delta) => {
    if (meshRef.current) {
      // Rotate faster during the Governance/Matrix scenes to feel ALIVE
      const speedMult = activeScene >= 7 && activeScene <= 9 ? 1.5 : 0.5;
      meshRef.current.rotation.y += delta * 0.05 * speedMult;
      
      // Update traffic
      const positions = trafficGeom.attributes.position.array as Float32Array;
      for (let i = 0; i < trafficCount; i++) {
        const ts = trafficState[i];
        ts.t += delta * ts.speed * speedMult;
        if (ts.t > 1) ts.t -= 1; // loop
        
        const path = cablePaths[ts.pathIndex];
        const point = path.getPoint(ts.t);
        
        positions[i * 3] = point.x;
        positions[i * 3 + 1] = point.y;
        positions[i * 3 + 2] = point.z;
      }
      trafficGeom.attributes.position.needsUpdate = true;
      
      // Traffic alpha pulsing
      if (trafficMatRef.current) {
         // High-energy moments during threat matrix (scene 9)
         const baseOpacity = activeScene === 9 ? 0.8 : 0.4;
         const pulse = Math.sin(state.clock.elapsedTime * 8) * 0.2 + 0.8;
         trafficMatRef.current.uniforms.uOpacity.value = baseOpacity * pulse;
      }
    }
  });

  return (
    <group ref={meshRef} position={position as any} scale={scale as any}>
      {/* ── Infrastructure Grid — whisper, don't shout ── */}
      <mesh>
        <sphereGeometry args={[4.95, 64, 32]} />
        <meshBasicMaterial color={PALETTE.coldSteel} wireframe transparent opacity={0.012} />
      </mesh>

      {/* ── Submarine Cables ── */}
      <lineSegments geometry={cables} material={lineMat} />

      {/* ── Node Points ── */}
      <points geometry={pointGeom} material={pointMat} />
      
      {/* ── Data Traffic ── */}
      <points geometry={trafficGeom}>
         <shaderMaterial
            ref={trafficMatRef}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            uniforms={{
              uColor: { value: new THREE.Color(PALETTE.sovereignCyan) },
              uOpacity: { value: 0.6 }
            }}
            vertexShader={`
              void main() {
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = 40.0 * (1.0 / -mvPosition.z);
                gl_Position = projectionMatrix * mvPosition;
              }
            `}
            fragmentShader={`
              uniform vec3 uColor;
              uniform float uOpacity;
              void main() {
                float dist = distance(gl_PointCoord, vec2(0.5));
                if (dist > 0.5) discard;
                // Soft glow core
                float alpha = (1.0 - dist * 2.0) * uOpacity;
                gl_FragColor = vec4(uColor, alpha);
              }
            `}
         />
      </points>

      {/* ── Continental Clusters ── */}
      {NODE_CLUSTERS.map((c, i) => (
        <group key={i} position={c.pos as any}>
          <mesh>
            <sphereGeometry args={[0.15, 8, 8]} />
            <meshBasicMaterial color={PALETTE.institutionalWhite} transparent opacity={0.15} />
          </mesh>
          {/* Subtle connecting lines to the core */}
          <line>
            <bufferGeometry attach="geometry" {...new THREE.BufferGeometry().setFromPoints([
              new THREE.Vector3(0,0,0),
              new THREE.Vector3().copy(new THREE.Vector3(...c.pos)).normalize().multiplyScalar(-5)
            ])} />
            <lineBasicMaterial color={PALETTE.sovereignCyan} transparent opacity={0.1} />
          </line>
        </group>
      ))}
    </group>
  );
}
