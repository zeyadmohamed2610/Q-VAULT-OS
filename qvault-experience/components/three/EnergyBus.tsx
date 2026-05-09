// ═══════════════════════════════════════════════════════════════
// ENERGY BUS (TRUST STACK)
// The vertical data flow connecting the layers of the Trust Stack.
// Uses custom shaders for energy pulsing and data packets.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { pulseVert } from '@/shaders/pulseVert';
import { pulseFrag } from '@/shaders/pulseFrag';
import { energyFrag } from '@/shaders/energyFrag';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface EnergyBusProps {
  progress: number;
}

export function EnergyBus({ progress }: EnergyBusProps) {
  const coreRef = useRef<THREE.ShaderMaterial>(null);
  const pulseRef = useRef<THREE.ShaderMaterial>(null);

  const coreUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) },
    uIntensity: { value: 0.85 }
  }), []);

  const pulseUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.institutionalWhite) },
    uPulseSpeed: { value: 2.0 }
  }), []);

  useFrame((state) => {
    const time = state.clock.elapsedTime * FILM_MOTION_SCALE;
    if (coreRef.current) {
      coreRef.current.uniforms.uTime.value = time;
      // Core gets brighter as we progress into the scene
      coreRef.current.uniforms.uIntensity.value = 0.65 + progress * 0.9;
    }
    if (pulseRef.current) {
      pulseRef.current.uniforms.uTime.value = time;
      pulseRef.current.uniforms.uProgress.value = progress;
      // Pulse speeds up as progress increases
      pulseRef.current.uniforms.uPulseSpeed.value = 1.5 + progress * 3.0;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Central Energy Core */}
      <mesh>
        <cylinderGeometry args={[0.3, 0.3, 24, 16, 1, true]} />
        <shaderMaterial
          ref={coreRef}
          vertexShader={pulseVert}
          fragmentShader={energyFrag}
          uniforms={coreUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Outer Data Pulse Ring */}
      <mesh>
        <cylinderGeometry args={[0.8, 0.8, 24, 32, 1, true]} />
        <shaderMaterial
          ref={pulseRef}
          vertexShader={pulseVert}
          fragmentShader={pulseFrag}
          uniforms={pulseUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Decorative inner guide rails */}
      {Array.from({ length: 4 }).map((_, i) => (
        <mesh key={i} position={[Math.cos((i * Math.PI) / 2) * 1.5, 0, Math.sin((i * Math.PI) / 2) * 1.5]}>
          <cylinderGeometry args={[0.02, 0.02, 24, 4]} />
          <meshBasicMaterial color={PALETTE.coldSteel} transparent opacity={0.08 + progress * 0.16} blending={THREE.AdditiveBlending} />
        </mesh>
      ))}
    </group>
  );
}
