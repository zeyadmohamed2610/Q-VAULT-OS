// ═══════════════════════════════════════════════════════════════
// SCENE 0: VOID BOOT — ACT I: CONTACT
//
// A classified post-quantum security system initializing.
// The user scrubs through a cinematic boot ritual.
//
// Timeline Phases (scroll progress 0 → 1):
//   0.00–0.08  Pure void. Only particles drift. Silence.
//   0.08–0.25  Outer ring materializes. Classification marker appears.
//   0.25–0.50  Logo text emerges letter by letter. Emissive edges glow.
//   0.50–0.65  Logo fully bright. Corner brackets lock. Camera pushing in.
//   0.65–0.88  Boot text sequence plays in HUD terminal.
//   0.88–1.00  Peak brightness. Scanlines intensify. Iris transition fires.
//
// Sub-components:
//   VaultLogo        — Text + ring + brackets + sweep line + classification
//   AtmosphericDust  — Additive point particles for depth/scale
//   VoidFog          — Scene fog manager
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';
import type { SceneProps } from '@/lib/types';
import { PALETTE } from '@/lib/MasteringPipeline';

// ── Easing utilities ──

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function remap(value: number, inMin: number, inMax: number, outMin: number, outMax: number): number {
  const t = Math.max(0, Math.min(1, (value - inMin) / (inMax - inMin)));
  return outMin + t * (outMax - outMin);
}

// ═══════════════════════════════════════════════════════════════
// ATMOSPHERIC DUST PARTICLES
// Microscopic additive particles that create depth and scale.
// Slow sine-wave drift. Barely visible. Purpose: the void is alive.
// ═══════════════════════════════════════════════════════════════

const PARTICLE_COUNT = 280;

function AtmosphericDust({ progress, particleCount }: { progress: number; particleCount: number }) {
  const pointsRef = useRef<THREE.Points>(null);

  // Always allocate MAX buffer, control visible count via drawRange
  const [positions, baseSpeeds] = useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    const speeds = new Float32Array(PARTICLE_COUNT);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 56;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 40;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 44;
      speeds[i] = 0.2 + Math.random() * 0.5;
    }
    return [pos, speeds];
  }, []); // Never re-create — buffer size must stay constant

  useFrame(({ clock }) => {
    if (!pointsRef.current) return;
    const geo = pointsRef.current.geometry;
    const posAttr = geo.attributes.position as THREE.BufferAttribute;
    const t = clock.elapsedTime;

    // Only animate visible particles
    const visible = Math.min(particleCount, PARTICLE_COUNT);
    for (let i = 0; i < visible; i++) {
      const speed = baseSpeeds[i];
      const idx = i * 3;
      posAttr.array[idx]     += Math.sin(t * speed * 0.3 + i) * 0.003;
      posAttr.array[idx + 1] += Math.cos(t * speed * 0.2 + i * 1.3) * 0.002;
      posAttr.array[idx + 2] += Math.sin(t * speed * 0.15 + i * 0.7) * 0.003;
    }
    posAttr.needsUpdate = true;

    // Control visible particle count via drawRange
    geo.setDrawRange(0, visible);
  });

  // Particles fade in from void
  const opacity = (0.035 + smoothstep(0.0, 0.15, progress) * 0.065);

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={PALETTE.coldSteel}
        size={0.026}
        transparent
        opacity={opacity}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />

    </points>
  );
}

// ═══════════════════════════════════════════════════════════════
// VAULT LOGO ASSEMBLY
//
// Composition:
//   1. Outer ring          — Thin torus, materializes first
//   2. Corner brackets     — Four L-shaped accent lines
//   3. Classification text — "CLASSIFIED // Q-VAULT SYSTEMS" above
//   4. Main title          — "Q-VAULT" center, steel with cyan emissive
//   5. Subtitle            — "POST-QUANTUM HARDWARE SECURITY" below
//   6. Sweep line          — Horizontal scan bar that sweeps vertically
//
// Every element has its own materialization window within progress.
// ═══════════════════════════════════════════════════════════════

// VaultLogo — cinematic BACKDROP, positioned far BEHIND the real device.
// Device (RealProductAssembly at z=0) is always visually in front.
function VaultLogo({ progress }: { progress: number }) {
  const groupRef = useRef<THREE.Group>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const sweepRef = useRef<THREE.Mesh>(null);

  // ── Phase calculations ──
  const ringOpacity       = 0.06 + smoothstep(0.02, 0.12, progress) * 0.25; // Very dim — background element
  const bracketOpacity    = smoothstep(0.08, 0.22, progress) * 0.30;
  const classifiedOpacity = smoothstep(0.06, 0.18, progress) * 0.4;
  const titleOpacity      = smoothstep(0.10, 0.32, progress);
  const subtitleOpacity   = smoothstep(0.25, 0.42, progress) * 0.6;
  const emissiveIntensity = remap(progress, 0.10, 0.80, 0.25, 1.45);
  const peakGlow          = smoothstep(0.88, 1.0, progress);

  // ── Animate ring rotation + sweep line ──
  useFrame(({ clock }) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.001;
    }
    if (sweepRef.current) {
      // Sweep bar oscillates vertically through the logo
      const sweep = Math.sin(clock.elapsedTime * 0.8) * 1.8;
      sweepRef.current.position.y = sweep;
      (sweepRef.current.material as THREE.MeshBasicMaterial).opacity =
        smoothstep(0.15, 0.30, progress) * 0.12;
    }
    // Subtle floating drift — never static, never robotic
    if (groupRef.current) {
      const t = clock.elapsedTime;
      groupRef.current.position.y = Math.sin(t * 0.3) * 0.05;
      groupRef.current.rotation.x = Math.sin(t * 0.2) * 0.003;
      groupRef.current.rotation.y = Math.cos(t * 0.15) * 0.003;
    }
  });

  const bracketLen = 0.6;
  const bracketOff = 2.8;
  const bracketY   = 1.2;

  return (
    // z = -28: far backdrop, product is always visually in front
    <group ref={groupRef} position={[0, 0, -28]}>

      {/* ── Outer Ring — scaled up to remain visible as backdrop ── */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[5.0, 0.018, 16, 128]} />
        <meshStandardMaterial
          color={PALETTE.institutionalWhite}
          emissive={PALETTE.sovereignCyan}
          emissiveIntensity={emissiveIntensity * 0.12 + peakGlow * 0.45}
          transparent
          opacity={ringOpacity}
          depthWrite={false}
        />
      </mesh>

      {/* ── Inner Ring — scaled to match outer ── */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[4.5, 0.008, 16, 128]} />
        <meshStandardMaterial
          color={PALETTE.coldSteel}
          emissive={PALETTE.sovereignCyan}
          emissiveIntensity={emissiveIntensity * 0.08}
          transparent
          opacity={ringOpacity * 0.5}
          depthWrite={false}
        />
      </mesh>

      {/* ── Corner Brackets (4 L-shapes) ── */}
      {[
        // top-left
        { pos: [-bracketOff, bracketY, 0], scaleH: [bracketLen, 0.02, 0.01], scaleV: [0.02, bracketLen, 0.01], anchorH: [-1, 0, 0], anchorV: [0, 1, 0] },
        // top-right
        { pos: [bracketOff, bracketY, 0], scaleH: [bracketLen, 0.02, 0.01], scaleV: [0.02, bracketLen, 0.01], anchorH: [1, 0, 0], anchorV: [0, 1, 0] },
        // bottom-left
        { pos: [-bracketOff, -bracketY, 0], scaleH: [bracketLen, 0.02, 0.01], scaleV: [0.02, bracketLen, 0.01], anchorH: [-1, 0, 0], anchorV: [0, -1, 0] },
        // bottom-right
        { pos: [bracketOff, -bracketY, 0], scaleH: [bracketLen, 0.02, 0.01], scaleV: [0.02, bracketLen, 0.01], anchorH: [1, 0, 0], anchorV: [0, -1, 0] },
      ].map((b, i) => (
        <group key={i} position={b.pos as [number, number, number]}>
          <mesh position={[b.anchorH[0] * bracketLen * 0.5, 0, 0]} scale={b.scaleH as [number, number, number]}>
            <boxGeometry />
            <meshStandardMaterial
              color={PALETTE.institutionalWhite}
              emissive={PALETTE.sovereignCyan}
              emissiveIntensity={emissiveIntensity * 0.12}
              transparent
              opacity={bracketOpacity}
            />
          </mesh>
          <mesh position={[0, b.anchorV[1] * bracketLen * 0.5, 0]} scale={b.scaleV as [number, number, number]}>
            <boxGeometry />
            <meshStandardMaterial
              color={PALETTE.institutionalWhite}
              emissive={PALETTE.sovereignCyan}
              emissiveIntensity={emissiveIntensity * 0.12}
              transparent
              opacity={bracketOpacity}
            />
          </mesh>
        </group>
      ))}

      {/* ── Classification Marker ── */}
      <Text
        position={[0, 2.0, 0]}
        fontSize={0.12}
        letterSpacing={0.25}
        anchorX="center"
        anchorY="middle"
        fillOpacity={classifiedOpacity}
      >
        CLASSIFIED // Q-VAULT SYSTEMS
        <meshBasicMaterial color={PALETTE.institutionalWhite} transparent opacity={classifiedOpacity} depthWrite={false} />
      </Text>

      {/* ── Main Title: Q-VAULT ── */}
      <Text
        position={[0, 0.15, 0]}
        fontSize={1.4}
        letterSpacing={0.18}
        anchorX="center"
        anchorY="middle"
        fillOpacity={titleOpacity}
      >
        Q-VAULT
        <meshStandardMaterial
          color={PALETTE.graphite}
          emissive={PALETTE.sovereignCyan}
          emissiveIntensity={emissiveIntensity * 0.24 + peakGlow * 0.55}
          metalness={0.95}
          roughness={0.05}
          transparent
          opacity={titleOpacity}
        />
      </Text>

      {/* ── Subtitle ── */}
      <Text
        position={[0, -0.8, 0]}
        fontSize={0.14}
        letterSpacing={0.2}
        anchorX="center"
        anchorY="middle"
        fillOpacity={subtitleOpacity}
      >
        POST-QUANTUM HARDWARE SECURITY
        <meshBasicMaterial color={PALETTE.coldSteel} transparent opacity={subtitleOpacity} depthWrite={false} />
      </Text>

      {/* ── Version Tag ── */}
      <Text
        position={[0, -1.15, 0]}
        fontSize={0.09}
        letterSpacing={0.15}
        anchorX="center"
        anchorY="middle"
        fillOpacity={subtitleOpacity * 0.5}
      >
        ML-KEM-768 · AES-256-GCM · BITLOCKER
        <meshBasicMaterial color={PALETTE.sovereignCyan} transparent opacity={subtitleOpacity * 0.32} depthWrite={false} />
      </Text>

      {/* ── Sweep Line (scan bar) ── */}
      <mesh ref={sweepRef}>
        <planeGeometry args={[7, 0.015]} />
        <meshBasicMaterial
          color={PALETTE.sovereignCyan}
          transparent
          opacity={0}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

    </group>
  );
}

// ═══════════════════════════════════════════════════════════════
// VOID FOG MANAGER
// Sets exponential fog on the scene during Scene 0.
// Creates depth falloff so distant particles fade into void.
// ═══════════════════════════════════════════════════════════════

// VoidFog DISABLED — fog now controlled globally by SceneAtmosphere
// using near-zero values from MasteringPipeline.SCENE_FOG.
// Re-enabling this would occlude the hardware model.
function VoidFog({ isActive: _a, progress: _p }: { isActive: boolean; progress: number }) {
  return null;
}

// ═══════════════════════════════════════════════════════════════
// MAIN SCENE EXPORT
// ═══════════════════════════════════════════════════════════════

export default function VoidBootScene({
  progress,
  isActive,
  qualityTier,
  reducedMotion,
}: SceneProps) {
  const invalidate = useThree((s) => s.invalidate);

  // Keep the canvas rendering while scene is active
  useFrame(() => {
    if (isActive) invalidate();
  });

  // Particle count scales with quality tier
  const particleCount = (() => {
    switch (qualityTier) {
      case 'ultra':  return 280;
      case 'high':   return 220;
      case 'medium': return 120;
      case 'low':    return 0;
    }
  })();

  return (
    <group visible={isActive}>
      <VoidFog isActive={isActive} progress={progress} />
      <VaultLogo progress={progress} />
      {particleCount > 0 && !reducedMotion && (
        <AtmosphericDust progress={progress} particleCount={particleCount} />
      )}
    </group>
  );
}
