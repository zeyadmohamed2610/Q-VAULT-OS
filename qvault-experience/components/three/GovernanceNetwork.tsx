// ═══════════════════════════════════════════════════════════════
// GOVERNANCE NETWORK
// The live infrastructure nodes orbiting the core.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

interface GovernanceNetworkProps {
  progress: number;
}

export function GovernanceNetwork({ progress }: GovernanceNetworkProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  
  const COUNT = 200;

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const nodes = useMemo(() => {
    const temp = [];
    for (let i = 0; i < COUNT; i++) {
      const r = 12 + Math.random() * 20;
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.acos((Math.random() * 2) - 1);
      
      temp.push({
        position: new THREE.Vector3(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta),
          r * Math.cos(phi)
        ),
        speed: (Math.random() - 0.5) * 0.5,
        orbitRadius: r
      });
    }
    return temp;
  }, []);

  useFrame((state) => {
    if (meshRef.current) {
      nodes.forEach((node, i) => {
        const time = state.clock.elapsedTime;
        const angle = time * node.speed * 1.5;
        
        dummy.position.x = node.position.x * Math.cos(angle) - node.position.z * Math.sin(angle);
        dummy.position.y = node.position.y;
        dummy.position.z = node.position.x * Math.sin(angle) + node.position.z * Math.cos(angle);
        
        // Pulse scale
        const scale = 1.0 + Math.sin(time * 5.0 + i) * 0.5;
        dummy.scale.set(scale, scale, scale);
        
        dummy.updateMatrix();
        meshRef.current!.setMatrixAt(i, dummy.matrix);
      });
      meshRef.current.instanceMatrix.needsUpdate = true;
    }
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, COUNT]}>
      <boxGeometry args={[0.2, 0.2, 0.2]} />
      <meshBasicMaterial color={PALETTE.sovereignCyan} toneMapped opacity={0.75} transparent />
    </instancedMesh>
  );
}
