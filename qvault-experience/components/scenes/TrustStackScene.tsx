// ═══════════════════════════════════════════════════════════════
// SCENE 3: TRUST STACK
// Visualizes the internal layered architecture of the Q-Vault.
// Physical hardware transitions into living trust infrastructure.
// ═══════════════════════════════════════════════════════════════

import { useMemo, useRef } from 'react';
import { useExperienceStore } from '@/lib/store';
import { EnergyBus } from '@/components/three/EnergyBus';
import { StackLayer } from '@/components/three/StackLayer';
import * as THREE from 'three';
import { PALETTE } from '@/lib/MasteringPipeline';

const LAYERS = [
  { id: 'root', name: 'HARDWARE ROOT', y: -8 },
  { id: 'boot', name: 'SECURE BOOT', y: -4 },
  { id: 'exchange', name: 'ML-KEM-768 EXCHANGE', y: 0 },
  { id: 'enclave', name: 'SESSION ENCLAVE', y: 4 },
  { id: 'policy', name: 'POLICY ENGINE', y: 8 },
  { id: 'governance', name: 'GOVERNANCE RUNTIME', y: 12 },
];

export default function TrustStackScene() {
  const groupRef = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const dustPositions = useMemo(() => {
    const positions = new Float32Array(600);
    for (let i = 0; i < positions.length; i++) {
      const seed = Math.sin(i * 127.1) * 43758.5453;
      positions[i] = (seed - Math.floor(seed) - 0.5) * 30;
    }
    return positions;
  }, []);

  // Keep it mounted if we are nearby
  const isVisible = activeScene >= 2 && activeScene <= 4;

  if (!isVisible) return null;

  return (
    <group ref={groupRef} visible={activeScene === 3 || activeScene === 4}>
      {/* 
        DATACENTER LIGHTING 
        Industrial, volumetric, high contrast
      */}
      <group>
        {/* Main top-down shaft */}
        <spotLight
          position={[0, 20, 0]}
          angle={0.4}
          penumbra={1.0}
          intensity={8.0}
          color={PALETTE.institutionalWhite}
          castShadow
        />
        {/* Subtle rim light from bottom */}
        <spotLight
          position={[0, -15, 5]}
          angle={0.6}
          penumbra={0.8}
          intensity={4.0}
          color={PALETTE.sovereignCyan}
        />
        <ambientLight intensity={0.025} color={PALETTE.coldSteel} />
      </group>

      {/* Volumetric depth fog tailored for the datacenter */}

      {/* Central Energy Core / Data Bus */}
      <EnergyBus progress={activeScene === 3 ? progress : 1} />

      {/* Floating Trust Layers */}
      {LAYERS.map((layer, index) => (
        <StackLayer
          key={layer.id}
          index={index}
          label={layer.name}
          position={[0, layer.y, 0]}
          progress={activeScene === 3 ? progress : 1}
        />
      ))}
      
      {/* 
        Atmospheric Particles (Simulating airborne dust in a cooled datacenter)
        Using point cloud for GPU efficiency 
      */}
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[dustPositions, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.05} color={PALETTE.coldSteel} transparent opacity={0.22} sizeAttenuation />
      </points>
    </group>
  );
}
