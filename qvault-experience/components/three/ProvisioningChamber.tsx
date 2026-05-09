// ═══════════════════════════════════════════════════════════════
// PROVISIONING CHAMBER
// The central platform holding the hardware module and shaders.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { CalibrationArm } from '@/components/three/CalibrationArm';
import { opticalScanVert, opticalScanFrag, injectionBeamVert, injectionBeamFrag, attestationWaveVert, attestationWaveFrag } from '@/shaders/provisioningShaders';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface ProvisioningChamberProps {
  progress: number;
}

export function ProvisioningChamber({ progress }: ProvisioningChamberProps) {
  const scanRef = useRef<THREE.ShaderMaterial>(null);
  const beamRef = useRef<THREE.ShaderMaterial>(null);
  const waveRef = useRef<THREE.ShaderMaterial>(null);
  const hardwareGroupRef = useRef<THREE.Group>(null);

  const scanUniforms = useMemo(() => ({
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  const beamUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.institutionalWhite) }
  }), []);

  const waveUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.threatAmber) }
  }), []);

  useFrame((state) => {
    if (scanRef.current) scanRef.current.uniforms.uProgress.value += (progress - scanRef.current.uniforms.uProgress.value) * 0.1;
    if (beamRef.current) {
      beamRef.current.uniforms.uProgress.value += (progress - beamRef.current.uniforms.uProgress.value) * 0.1;
      beamRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
    }
    if (waveRef.current) {
      waveRef.current.uniforms.uProgress.value += (progress - waveRef.current.uniforms.uProgress.value) * 0.1;
      waveRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
    }
    
    // Slow suspension rotation
    if (hardwareGroupRef.current) {
      hardwareGroupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.3) * 0.1;
    }
  });

  return (
    <group>
      {/* Central Suspended Hardware (Global Hero Asset handles the product) */}
      <group ref={hardwareGroupRef} position={[0, 0, 0]}>
        
        {/* Optical Scan Pass */}
        <mesh scale={[1.2, 1.2, 1.2]}>
          <cylinderGeometry args={[1, 1, 4, 32]} />
          <shaderMaterial
            ref={scanRef}
            vertexShader={opticalScanVert}
            fragmentShader={opticalScanFrag}
            uniforms={scanUniforms}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>

      {/* Identity Injection Beam (from above) */}
      <mesh position={[0, 5, 0]}>
        <cylinderGeometry args={[0.5, 0.5, 10, 32]} />
        <shaderMaterial
          ref={beamRef}
          vertexShader={injectionBeamVert}
          fragmentShader={injectionBeamFrag}
          uniforms={beamUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Attestation Wave (Expanding sphere) */}
      <mesh>
        <sphereGeometry args={[5, 64, 64]} />
        <shaderMaterial
          ref={waveRef}
          vertexShader={attestationWaveVert}
          fragmentShader={attestationWaveFrag}
          uniforms={waveUniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Robotic Calibration Arms */}
      <CalibrationArm progress={progress} side="left" />
      <CalibrationArm progress={progress} side="right" />
      
      {/* Lower Docking Platform */}
      <mesh position={[0, -4, 0]} receiveShadow>
        <cylinderGeometry args={[4, 5, 1, 64]} />
        <meshStandardMaterial color={PALETTE.graphite} roughness={0.8} metalness={0.6} />
      </mesh>
      <mesh position={[0, -3.4, 0]}>
        <ringGeometry args={[3.8, 3.9, 64]} />
        <meshBasicMaterial color={PALETTE.threatAmber} transparent opacity={0.18} />
      </mesh>
    </group>
  );
}
