// ═══════════════════════════════════════════════════════════════
// CALIBRATION ARM
// Robotic industrial arm that performs the optical scan and seal.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { Materials } from '@/lib/materials';
import { PALETTE } from '@/lib/MasteringPipeline';

interface CalibrationArmProps {
  progress: number;
  side: 'left' | 'right';
}

export function CalibrationArm({ progress, side }: CalibrationArmProps) {
  const baseRef = useRef<THREE.Group>(null);
  const joint1Ref = useRef<THREE.Group>(null);
  const joint2Ref = useRef<THREE.Group>(null);
  const headRef = useRef<THREE.Group>(null);

  const isLeft = side === 'left';
  const mult = isLeft ? 1 : -1;

  useFrame(() => {
    // Cinematic industrial robotics logic
    // Rest positions
    let baseRot = 0;
    let j1Rot = Math.PI / 4 * mult;
    let j2Rot = -Math.PI / 2 * mult;
    let headRot = Math.PI / 4 * mult;

    if (progress > 0.1 && progress < 0.6) {
      // Approach phase
      const approach = Math.min(1, (progress - 0.1) * 3);
      j1Rot = THREE.MathUtils.lerp(Math.PI / 4 * mult, Math.PI / 8 * mult, approach);
      j2Rot = THREE.MathUtils.lerp(-Math.PI / 2 * mult, -Math.PI / 4 * mult, approach);
    }
    
    if (progress >= 0.2 && progress < 0.5) {
      // Scanning phase - move up and down
      const scanPhase = (progress - 0.2) * (1 / 0.3);
      baseRot = Math.sin(scanPhase * Math.PI) * 0.2 * mult;
      headRot = Math.sin(scanPhase * Math.PI * 2) * 0.2;
    }

    if (progress >= 0.6) {
      // Retract phase
      const retract = Math.min(1, (progress - 0.6) * 3);
      j1Rot = THREE.MathUtils.lerp(j1Rot, Math.PI / 3 * mult, retract);
      j2Rot = THREE.MathUtils.lerp(j2Rot, -Math.PI / 1.5 * mult, retract);
    }

    if (baseRef.current) baseRef.current.rotation.y = baseRot;
    if (joint1Ref.current) joint1Ref.current.rotation.z = j1Rot;
    if (joint2Ref.current) joint2Ref.current.rotation.z = j2Rot;
    if (headRef.current) headRef.current.rotation.z = headRot;
  });

  return (
    <group position={[3.5 * mult, -2, 0]}>
      <group ref={baseRef}>
        <mesh material={Materials.machinedSteel} position={[0, 0.5, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[0.6, 0.8, 1, 32]} />
        </mesh>
        
        <group ref={joint1Ref} position={[0, 1, 0]}>
          <mesh material={Materials.carbonAnodized} position={[0, 1.5, 0]} castShadow receiveShadow>
            <boxGeometry args={[0.4, 3, 0.4]} />
          </mesh>
          
          <group ref={joint2Ref} position={[0, 3, 0]}>
            <mesh material={Materials.machinedSteel} position={[0, 1, 0]} castShadow receiveShadow>
              <boxGeometry args={[0.3, 2, 0.3]} />
            </mesh>
            
            <group ref={headRef} position={[0, 2, 0]}>
              <mesh material={Materials.darkCeramic} castShadow receiveShadow>
                <boxGeometry args={[0.5, 0.5, 0.8]} />
              </mesh>
              {/* Scanner Lens */}
              <mesh position={[0, 0, 0.41]}>
                <circleGeometry args={[0.15, 32]} />
                <meshStandardMaterial color={PALETTE.institutionalWhite} emissive={PALETTE.threatAmber} emissiveIntensity={0.28} toneMapped />
              </mesh>
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}
