'use client';

// ═══════════════════════════════════════════════════════════════
// REAL PRODUCT ASSEMBLY — PHASE XXX FIXED
// Scale empirically calibrated: 55 world-units at z=7/fov=32 → 70% fill.
// Explode offsets in LOCAL model space (after scale applied).
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF, ContactShadows, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { SCENE_ACCENT, PALETTE } from '@/lib/MasteringPipeline';

// ── Calibrated scale ───────────────────────────────────────────
// Camera at z=7, fov=32: visible_h = 2*7*tan(16°) ≈ 4.01 world-units.
// Target 70% fill → device needs 2.81 world-unit height.
// GLB models are in meters. ESP32 enclosure ≈ 0.051m long, 0.026m wide.
// 2.81 / 0.051 ≈ 55. So PRODUCT_SCALE ≈ 55 delivers target fill.
const PRODUCT_SCALE = 55;

// ── Explode offsets in LOCAL model space ───────────────────────
// 0.6 world units separation → 0.6 / 55 = 0.011 model units
const UP_Y   =  0.012;  // upper shell local-space Y offset
const DOWN_Y = -0.012;  // lower shell local-space Y offset
const PCB_Y  =  0.004;  // PCB float local-space Y offset

// ── Scene choreography ─────────────────────────────────────────
interface SCfg {
  visible: boolean;
  rotX: number;
  rotYFn: (t: number) => number;
  upY: number;
  espY: number;
  downY: number;
  led: number;
}

const SCENE: Record<number, SCfg> = {
  // ACT I: VoidBoot — product HIDDEN
  0: { visible: false, rotX: 0,    rotYFn: ()  => 0,                          upY: 0,     espY: 0,     downY: 0,      led: 0  },
  // Surveillance scan
  1: { visible: true,  rotX: 0.10, rotYFn: (t) => t * 0.06,                   upY: 0,     espY: 0,     downY: 0,      led: 1  },
  // HERO REVEAL — assembled
  2: { visible: true,  rotX: 0.04, rotYFn: (t) => Math.sin(t * 0.18) * 0.22,  upY: 0,     espY: 0,     downY: 0,      led: 10 },
  // Exploded view — parts separate
  3: { visible: true,  rotX: 0.16, rotYFn: (t) => 0.40 + Math.sin(t * 0.08) * 0.04, upY: UP_Y,  espY: 0,     downY: DOWN_Y, led: 3  },
  // PCB descent
  4: { visible: true,  rotX: 0.12, rotYFn: ()  => -0.25,                      upY: UP_Y,  espY: 0,     downY: 0,      led: 4  },
  // Upper shell seals
  5: { visible: true,  rotX: 0.07, rotYFn: ()  =>  0.12,                      upY: 0,     espY: 0,     downY: 0,      led: 5  },
  // Fully assembled — confident orbit
  6: { visible: true,  rotX: 0.05, rotYFn: (t) => t * 0.08,                   upY: 0,     espY: 0,     downY: 0,      led: 6  },
  // Governance
  7: { visible: true,  rotX: 0.04, rotYFn: (t) => Math.sin(t * 0.12) * 0.30,  upY: 0,     espY: 0,     downY: 0,      led: 5  },
  8: { visible: true,  rotX: 0.04, rotYFn: (t) => Math.sin(t * 0.10) * 0.28,  upY: 0,     espY: 0,     downY: 0,      led: 5  },
  // Threat
  9: { visible: true,  rotX: 0.09, rotYFn: (t) => t * 0.04,                   upY: 0,     espY: 0,     downY: 0,      led: 7  },
  // Lifecycle
  10:{ visible: true,  rotX: 0.03, rotYFn: (t) => t * 0.03,                   upY: 0,     espY: 0,     downY: 0,      led: 4  },
  11:{ visible: true,  rotX: 0.03, rotYFn: (t) => t * 0.02,                   upY: 0,     espY: 0,     downY: 0,      led: 3  },
  // Final Seal
  12:{ visible: true,  rotX: 0,    rotYFn: ()  => 0,                           upY: 0,     espY: 0,     downY: 0,      led: 2  },
};

// ── Materials ──────────────────────────────────────────────────
function useProductMaterials() {
  const matAluminum = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:              new THREE.Color('#1a1d20'),
    roughness:          0.06,
    metalness:          0.96,
    envMapIntensity:    5.0,
    reflectivity:       1.0,
    clearcoat:          0.3,
    clearcoatRoughness: 0.08,
  }), []);

  const matPCB = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:           new THREE.Color('#050c05'),
    roughness:       0.52,
    metalness:       0.48,
    envMapIntensity: 2.0,
  }), []);

  return { matAluminum, matPCB };
}

export function RealProductAssembly() {
  const groupRef     = useRef<THREE.Group>(null);
  const upCoverRef   = useRef<THREE.Group>(null);
  const espRef       = useRef<THREE.Group>(null);
  const downCoverRef = useRef<THREE.Group>(null);
  const ledRef       = useRef<THREE.PointLight>(null);

  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);

  const espGltf   = useGLTF('/models/esp32-s3.glb');
  const upGltf    = useGLTF('/models/up-cover.glb');
  const downGltf  = useGLTF('/models/cover-down.glb');

  const { matAluminum, matPCB } = useProductMaterials();

  // ── Shared assembly center — preserves part relative positions ─
  // Computing per-part centers DESTROYS the CAD alignment.
  // Correct approach: compute combined bbox of all 3, offset the group.
  const assemblyCenter = useMemo(() => {
    const box = new THREE.Box3();
    espGltf.scene.traverse((c) => { if ((c as THREE.Mesh).isMesh) box.expandByObject(c); });
    upGltf.scene.traverse((c)  => { if ((c as THREE.Mesh).isMesh) box.expandByObject(c); });
    downGltf.scene.traverse((c) => { if ((c as THREE.Mesh).isMesh) box.expandByObject(c); });
    const center = new THREE.Vector3();
    if (!box.isEmpty()) box.getCenter(center);
    return center; // negate this on the scaled group
  }, [espGltf.scene, upGltf.scene, downGltf.scene]);

  useEffect(() => {
    espGltf.scene.traverse((c) => {
      if (c instanceof THREE.Mesh) { c.material = matPCB; c.castShadow = true; c.receiveShadow = true; }
    });
    upGltf.scene.traverse((c) => {
      if (c instanceof THREE.Mesh) { c.material = matAluminum; c.castShadow = true; c.receiveShadow = true; }
    });
    downGltf.scene.traverse((c) => {
      if (c instanceof THREE.Mesh) { c.material = matAluminum; c.castShadow = true; c.receiveShadow = true; }
    });
  }, [espGltf.scene, upGltf.scene, downGltf.scene, matAluminum, matPCB]);

  // ── Per-frame choreography ─────────────────────────────────
  useFrame((state, delta) => {
    if (!groupRef.current || !upCoverRef.current || !espRef.current || !downCoverRef.current) return;

    const t   = state.clock.elapsedTime;
    const cfg = SCENE[activeScene] ?? SCENE[6];
    const dt  = Math.min(delta, 0.05);

    // Sovereign breathing — ±0.018 world units
    groupRef.current.position.y = Math.sin(t * 0.38) * 0.018;

    // Rotation — heavy inertial dolly
    groupRef.current.rotation.x += (cfg.rotX      - groupRef.current.rotation.x) * dt * 2.0;
    groupRef.current.rotation.y += (cfg.rotYFn(t) - groupRef.current.rotation.y) * dt * 1.8;

    // Explode — Y in local model space
    let targetUpY   = cfg.upY;
    let targetDownY = cfg.downY;
    let targetEspY  = cfg.espY;

    // Scene 4: PCB descends progressively onto lower shell
    if (activeScene === 4) targetEspY = PCB_Y * (1 - progress);
    // Scene 5: upper shell seals progressively
    if (activeScene === 5) targetUpY  = UP_Y  * (1 - progress);

    upCoverRef.current.position.y   += (targetUpY   - upCoverRef.current.position.y)   * dt * 3.0;
    espRef.current.position.y       += (targetEspY  - espRef.current.position.y)       * dt * 3.0;
    downCoverRef.current.position.y += (targetDownY - downCoverRef.current.position.y) * dt * 3.0;

    // LED intensity
    if (ledRef.current) {
      const ledTarget = cfg.led + (activeScene === 9 ? Math.sin(t * 6) * 2.5 : 0);
      ledRef.current.intensity += (ledTarget - ledRef.current.intensity) * dt * 3.5;
    }
  });

  const cfg         = SCENE[activeScene] ?? SCENE[6];
  const accentColor = SCENE_ACCENT[activeScene] ?? PALETTE.sovereignCyan;

  return (
    <group ref={groupRef} visible={cfg.visible}>

      {/* Studio IBL — metallic response on enclosure */}
      <Environment preset="studio" />

      {/* KEY LIGHT — cold white, upper right */}
      <spotLight
        position={[8, 14, 10]}
        target-position={[0, 0, 0]}
        angle={0.22}
        penumbra={0.85}
        intensity={140}
        color="#d8eeff"
        castShadow
        shadow-mapSize={[2048, 2048]}
      />

      {/* RIM LIGHT — sovereign cyan, upper left rear */}
      <spotLight
        position={[-10, 6, -12]}
        target-position={[0, 0, 0]}
        angle={0.28}
        penumbra={0.7}
        intensity={activeScene === 9 ? 100 : 90}
        color={activeScene === 9 ? '#ff8800' : PALETTE.sovereignCyan}
      />

      {/* FILL — gentle, preserve shadow detail */}
      <directionalLight position={[4, -2, 5]} intensity={5} color="#b0bec5" />

      {/* NEGATIVE FILL — deepen cinematic contrast */}
      <directionalLight position={[-8, -4, -8]} intensity={-2} color="#000000" />

      {/* Accent glow — scene-reactive */}
      <pointLight
        position={[0, 0, 2]}
        intensity={activeScene >= 2 ? 10 : 2}
        color={accentColor}
        distance={6}
        decay={2}
      />

      {/* ════════════════════════════════════════════════════════
          THE PRODUCT — scale=55 → 70% fill at z=7/fov=32.
          All 3 parts share one center offset — preserves CAD assembly.
          ════════════════════════════════════════════════════════ */}
      <group
        scale={PRODUCT_SCALE}
        position={[
          -assemblyCenter.x,
          -assemblyCenter.y,
          -assemblyCenter.z,
        ]}
      >
        {/* Upper aluminium shell */}
        <group ref={upCoverRef}>
          <primitive object={upGltf.scene} />
        </group>

        {/* ESP32-S3 PCB — sovereign trust anchor */}
        <group ref={espRef}>
          <primitive object={espGltf.scene} />

          {/* Attestation LED */}
          <pointLight
            ref={ledRef}
            position={[0, 0.01, 0]}
            color={accentColor}
            intensity={0}
            distance={0.6}
            decay={2}
          />
          {/* Secure enclave chip glow */}
          <mesh position={[0, 0.006, 0]}>
            <boxGeometry args={[0.018, 0.002, 0.014]} />
            <meshStandardMaterial
              color={accentColor}
              emissive={accentColor}
              emissiveIntensity={activeScene >= 2 ? 6 : 0}
              transparent
              opacity={0.85}
            />
          </mesh>
        </group>

        {/* Lower aluminium shell */}
        <group ref={downCoverRef}>
          <primitive object={downGltf.scene} />
        </group>
      </group>

      {/* Contact shadow */}
      <ContactShadows
        position={[0, -1.6, 0]}
        opacity={0.5}
        scale={6}
        blur={2.5}
        far={3}
        color="#000000"
      />
    </group>
  );
}

useGLTF.preload('/models/esp32-s3.glb');
useGLTF.preload('/models/up-cover.glb');
useGLTF.preload('/models/cover-down.glb');
