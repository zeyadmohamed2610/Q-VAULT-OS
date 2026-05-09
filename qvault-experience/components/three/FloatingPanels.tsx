// ═══════════════════════════════════════════════════════════════
// FLOATING PANELS
// The Window Compositor for the OS Surface (Scene 7)
// Instanced Glass Panels and Terminal Streams.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { glassPanelVert, glassPanelFrag, terminalStreamVert, terminalStreamFrag } from '@/shaders/osSurfaceShaders';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

interface FloatingPanelsProps {
  progress: number;
}

export function FloatingPanels({ progress }: FloatingPanelsProps) {
  const panelShaderRef = useRef<THREE.ShaderMaterial>(null);
  const terminalShaderRef = useRef<THREE.ShaderMaterial>(null);
  const groupRef = useRef<THREE.Group>(null);

  const panelUniforms = useMemo(() => ({
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.coldSteel) },
    uOpacity: { value: 0.46 }
  }), []);

  const terminalUniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uColor: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  // Define panel positions (depth parallax)
  const panels = useMemo(() => [
    { position: [-6, 2, -2], scale: [4, 6, 1] }, // Left Threat Map
    { position: [0, 0, -5], scale: [8, 5, 1] },  // Center Main Registry
    { position: [5, -2, -3], scale: [5, 4, 1] }, // Right Terminal
    { position: [-4, -3, 2], scale: [3, 2, 1] }, // Bottom Left Enclave State
    { position: [6, 3, 1], scale: [4, 3, 1] },   // Top Right Governance
    { position: [2, 4, -8], scale: [6, 3, 1] },  // Deep Background
  ], []);

  useFrame((state) => {
    if (panelShaderRef.current) panelShaderRef.current.uniforms.uProgress.value += (progress - panelShaderRef.current.uniforms.uProgress.value) * 0.1;
    if (terminalShaderRef.current) {
      terminalShaderRef.current.uniforms.uProgress.value += (progress - terminalShaderRef.current.uniforms.uProgress.value) * 0.1;
      terminalShaderRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
    }
    
    // Slow parallax drift
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.15) * 0.2;
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.075) * 0.05;
    }
  });

  return (
    <group ref={groupRef}>
      {panels.map((panel, idx) => (
        <group key={idx} position={new THREE.Vector3(...panel.position)}>
          {/* Glass Window Base */}
          <mesh scale={new THREE.Vector3(...panel.scale)}>
            <planeGeometry args={[1, 1, 16, 16]} />
            <shaderMaterial
              ref={idx === 0 ? panelShaderRef : undefined} // Only need ref on one for uniform updates if shared, but here we share the material by not creating it inline. Wait, inline shaderMaterial creates new instances.
              vertexShader={glassPanelVert}
              fragmentShader={glassPanelFrag}
              uniforms={panelUniforms}
              transparent
              depthWrite={false}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* Terminal Stream Content (only on some panels) */}
          {idx % 2 === 0 && (
            <mesh position={[0, 0, 0.01]} scale={new THREE.Vector3(panel.scale[0] * 0.9, panel.scale[1] * 0.9, 1)}>
              <planeGeometry args={[1, 1]} />
              <shaderMaterial
                ref={idx === 0 ? terminalShaderRef : undefined}
                vertexShader={terminalStreamVert}
                fragmentShader={terminalStreamFrag}
                uniforms={terminalUniforms}
                transparent
                depthWrite={false}
                blending={THREE.AdditiveBlending}
              />
            </mesh>
          )}
        </group>
      ))}
    </group>
  );
}
