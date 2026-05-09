// ═══════════════════════════════════════════════════════════════
// SEAL MECHANISM
// Central Vault Mechanism for final closure.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { apertureVert, apertureFrag, extinctionPulseVert, extinctionPulseFrag, finalSymbolVert, finalSymbolFrag } from '@/shaders/sealShaders';
import { PALETTE } from '@/lib/MasteringPipeline';

interface SealMechanismProps {
  progress: number;
}

export function SealMechanism({ progress }: SealMechanismProps) {
  const apertureRef = useRef<THREE.ShaderMaterial>(null);
  const pulseRef = useRef<THREE.ShaderMaterial>(null);
  const symbolRef = useRef<THREE.ShaderMaterial>(null);
  const ringsRef = useRef<THREE.Group>(null);

  const apertureUniforms = useMemo(() => ({
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.deepGraphite) }
  }), []);

  const pulseUniforms = useMemo(() => ({
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.institutionalWhite) }
  }), []);

  const symbolUniforms = useMemo(() => ({
    uProgress: { value: 0 }
  }), []);

  useFrame((state) => {
    if (apertureRef.current) apertureRef.current.uniforms.uProgress.value = progress;
    if (pulseRef.current) pulseRef.current.uniforms.uProgress.value = progress;
    if (symbolRef.current) symbolRef.current.uniforms.uProgress.value = progress;

    if (ringsRef.current) {
      // Massive mechanical rings slow down and stop as progress nears 0.8
      const spinSpeed = Math.max(0, 1.0 - progress / 0.8) * 0.05;
      ringsRef.current.rotation.z += spinSpeed;
    }
  });

  return (
    <group>
      {/* Massive Mechanical Rings */}
      <group ref={ringsRef} position={[0, 0, -2]}>
        <mesh>
          <torusGeometry args={[16, 1.4, 24, 80]} />
          <meshStandardMaterial color={PALETTE.graphite} metalness={0.9} roughness={0.32} />
        </mesh>
        <mesh rotation={[0, 0, Math.PI / 4]}>
          <torusGeometry args={[20, 0.8, 24, 80]} />
          <meshStandardMaterial color={PALETTE.graphite} metalness={0.9} roughness={0.48} />
        </mesh>
        {/* Locking gears */}
        {[...Array(12)].map((_, i) => (
          <mesh key={i} position={[Math.cos(i * Math.PI/6) * 16, Math.sin(i * Math.PI/6) * 16, 0]} rotation={[0, 0, i * Math.PI/6]}>
            <boxGeometry args={[3, 1.4, 3]} />
            <meshStandardMaterial color={PALETTE.graphite} metalness={0.8} roughness={0.58} />
          </mesh>
        ))}
      </group>

      {/* The Aperture Blade Closure */}
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[44, 44]} />
        <shaderMaterial
          ref={apertureRef}
          vertexShader={apertureVert}
          fragmentShader={apertureFrag}
          uniforms={apertureUniforms}
          transparent
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Extinction Light Pulse */}
      <mesh position={[0, 0, 1]}>
        <planeGeometry args={[38, 38]} />
        <shaderMaterial
          ref={pulseRef}
          vertexShader={extinctionPulseVert}
          fragmentShader={extinctionPulseFrag}
          uniforms={pulseUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Final Q-VAULT Symbol */}
      <mesh position={[0, 0, 2]}>
        <planeGeometry args={[10, 10]} />
        <shaderMaterial
          ref={symbolRef}
          vertexShader={finalSymbolVert}
          fragmentShader={finalSymbolFrag}
          uniforms={symbolUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
