// ═══════════════════════════════════════════════════════════════
// Q-VAULT — PHASE XXIX: PRODUCT-CENTRIC FILM RECONSTRUCTION
// The hardware is the protagonist. Every system serves the device.
// Real GLBs. Hero framing. No invisible product.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useGLTF, Environment, ContactShadows } from '@react-three/drei';
import { PALETTE, SCENE_ACCENT } from '@/lib/MasteringPipeline';
import { useExperienceStore } from '@/lib/store';

// ── Model scale — tuned so the device fills the frame at z=4 ──
const PRODUCT_SCALE = 12.0;

export function HardwareModel() {
  const groupRef    = useRef<THREE.Group>(null);
  const upCoverRef  = useRef<THREE.Group>(null);
  const espRef      = useRef<THREE.Group>(null);
  const downCoverRef = useRef<THREE.Group>(null);
  const sweepRef    = useRef<THREE.SpotLight>(null);
  const rimRef      = useRef<THREE.SpotLight>(null);
  const keyRef      = useRef<THREE.SpotLight>(null);
  const ledRef      = useRef<THREE.PointLight>(null);

  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress    = useExperienceStore((s) => s.sceneProgress);

  // Real GLB Assets
  const espGltf      = useGLTF('/models/esp32-s3.glb');
  const upCoverGltf  = useGLTF('/models/up-cover.glb');
  const downCoverGltf = useGLTF('/models/cover-down.glb');

  // ── CINEMATIC MATERIALS ──
  // Aluminium shell: dark graphite with premium metallic response
  const matAluminum = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:            new THREE.Color('#1c1f22'),
    roughness:        0.08,
    metalness:        0.95,
    envMapIntensity:  4.0,
    reflectivity:     1.0,
    clearcoat:        0.2,
    clearcoatRoughness: 0.1,
  }), []);

  // PCB: dark green-black with subtle metallic traces
  const matPCB = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:     new THREE.Color('#060d06'),
    roughness: 0.55,
    metalness: 0.45,
    envMapIntensity: 1.5,
  }), []);

  // Apply materials to all GLB meshes
  useEffect(() => {
    espGltf.scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = matPCB;
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    upCoverGltf.scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = matAluminum;
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
    downCoverGltf.scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.material = matAluminum;
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
  }, [espGltf, upCoverGltf, downCoverGltf, matAluminum, matPCB]);

  // NOTE: All Y offsets are in WORLD space.
  // The product group has scale=12 applied, so 1 model-unit = 12 world-units.
  // These targets are intentionally small so parts stay in the macro camera frame.
  const WS = 1 / PRODUCT_SCALE; // 1 model-unit in world-space

  useFrame((state, delta) => {
    if (!groupRef.current || !upCoverRef.current || !espRef.current || !downCoverRef.current) return;

    const t = state.clock.elapsedTime;

    // Breathing motion — ±0.02 world units (subtle, never pushes device out of frame)
    groupRef.current.position.y = -0.3 + Math.sin(t * 0.4) * 0.02;

    // Light sweep across the enclosure
    if (sweepRef.current) {
      sweepRef.current.position.x = Math.sin(t * 0.8) * 6;
      sweepRef.current.position.z = Math.cos(t * 0.5) * 4;
      sweepRef.current.intensity  = (Math.sin(t * 2.0) * 0.5 + 0.5) * 80;
    }

    // Scene-based choreography
    let targetRotX   = 0.08;
    let targetRotY   = 0;
    // Explode distances — kept tight so parts stay in frame
    let targetUpY    = 0;
    let targetEspY   = 0;
    let targetDownY  = 0;
    let ledTarget    = 0;

    switch (activeScene) {
      // ── ACT I: AWAKENING — device rises from darkness ──
      case 0:
        // Silhouette slowly rotating, parts barely separated for depth
        targetRotY  = t * 0.08;
        targetUpY   = 0.06 * WS;   // tiny world-space gap at scale 12
        targetDownY = -0.06 * WS;
        targetEspY  = 0;
        ledTarget   = 0;
        break;

      case 1:
        // Perimeter scan — slow orbit with slight tilt
        targetRotX = 0.15;
        targetRotY = t * 0.1;
        targetUpY   = 0.04 * WS;
        targetDownY = -0.04 * WS;
        ledTarget   = 1.0;
        break;

      case 2:
        // Full hardware reveal — assembled, hero shot
        targetRotX = 0.05;
        targetRotY = Math.sin(t * 0.2) * 0.3;
        targetUpY   = 0;
        targetDownY = 0;
        ledTarget   = 8.0;
        break;

      // ── ACT II: ENGINEERING — assembly sequence ──
      case 3:
        // Exploded view — parts separated, still within macro frustum
        targetRotX = 0.2;
        targetRotY = Math.PI * 0.15;
        targetUpY   = 0.1 * WS;    // 0.1 model-units = visible gap
        targetDownY = -0.1 * WS;
        targetEspY  = 0;
        ledTarget   = 3.0;
        break;

      case 4:
        // PCB descends onto lower shell
        targetRotX = 0.15;
        targetRotY = Math.PI * -0.1;
        targetUpY   = 0.1 * WS;
        targetEspY  = THREE.MathUtils.lerp(0.12 * WS, 0, progress);
        targetDownY = 0;
        ledTarget   = 4.0;
        break;

      case 5:
        // Upper shell seals shut — cinematic close
        targetRotX = 0.1;
        targetRotY = Math.PI * 0.05;
        targetUpY   = THREE.MathUtils.lerp(0.1 * WS, 0, progress);
        targetEspY  = 0;
        targetDownY = 0;
        ledTarget   = progress > 0.7 ? 12.0 : 4.0;
        break;

      case 6:
        // Fully assembled — slow confident rotation
        targetRotX = 0.08;
        targetRotY = t * 0.12;
        targetUpY   = 0;
        targetDownY = 0;
        ledTarget   = 6.0;
        break;

      // ── ACT III: GOVERNANCE — device dominates ──
      case 7:
      case 8:
        targetRotX = 0.06;
        targetRotY = Math.sin(t * 0.15) * 0.4;
        ledTarget   = 5.0;
        break;

      case 9:
        // Threat — amber pulse, slight tilt
        targetRotX = 0.12;
        targetRotY = t * 0.06;
        ledTarget   = 6.0 + Math.sin(t * 6) * 3.0;
        break;

      // ── ACT IV: IMMORTALITY — final hero shot ──
      case 10:
      case 11:
        targetRotX = 0.04;
        targetRotY = t * 0.04;
        ledTarget   = 4.0;
        break;

      case 12:
        // Final seal — centered, still, authoritative
        targetRotX = 0;
        targetRotY = 0;
        ledTarget   = 2.0;
        break;

      default:
        targetRotY = t * 0.05;
        ledTarget  = 3.0;
        break;
    }

    // Smooth inertia
    groupRef.current.rotation.x  += (targetRotX - groupRef.current.rotation.x)  * delta * 1.5;
    groupRef.current.rotation.y  += (targetRotY - groupRef.current.rotation.y)  * delta * 1.5;
    upCoverRef.current.position.y  += (targetUpY   - upCoverRef.current.position.y)  * delta * 2.5;
    espRef.current.position.y      += (targetEspY  - espRef.current.position.y)      * delta * 2.5;
    downCoverRef.current.position.y += (targetDownY - downCoverRef.current.position.y) * delta * 2.5;

    if (ledRef.current) {
      ledRef.current.intensity += (ledTarget - ledRef.current.intensity) * delta * 3.0;
    }
  });

  const accentColor = SCENE_ACCENT[activeScene] ?? PALETTE.sovereignCyan;

  return (
    <group ref={groupRef}>

      {/* ════════════════════════════════════════
          CINEMATIC STUDIO ENVIRONMENT
          IBL + controlled key/rim/fill setup
          ════════════════════════════════════════ */}
      <Environment preset="studio" />

      {/* Key light — cold white, from upper-right front */}
      <spotLight
        ref={keyRef}
        position={[8, 12, 10]}
        target-position={[0, 0, 0]}
        angle={0.25}
        penumbra={0.8}
        intensity={120}
        color="#ddeeff"
        castShadow
        shadow-mapSize={[2048, 2048]}
      />

      {/* Rim light — sovereign cyan, from upper-left rear */}
      <spotLight
        ref={rimRef}
        position={[-10, 6, -12]}
        target-position={[0, 0, 0]}
        angle={0.3}
        penumbra={0.6}
        intensity={80}
        color={PALETTE.sovereignCyan}
      />

      {/* Fill — warm graphite, from below-right */}
      <directionalLight
        position={[5, -3, 6]}
        intensity={8}
        color="#b8c5cc"
      />

      {/* Sweep light — moving optical reflection across enclosure */}
      <spotLight
        ref={sweepRef}
        position={[0, 8, 6]}
        target-position={[0, 0, 0]}
        angle={0.15}
        penumbra={1}
        intensity={0}
        color="#ffffff"
      />

      {/* Accent glow — scene-based color pulse */}
      <pointLight
        position={[0, 0, 2]}
        intensity={activeScene >= 2 ? 12 : 2}
        color={accentColor}
        distance={6}
        decay={2}
      />

      {/* ════════════════════════════════════════
          THE PRODUCT — centered, scaled for hero
          Position Y=-0.3 centers it in macro camera frustum
          ════════════════════════════════════════ */}
      <group scale={PRODUCT_SCALE} position={[0, -0.3, 0]}>

        {/* Upper aluminium shell */}
        <group ref={upCoverRef}>
          <primitive object={upCoverGltf.scene} />
        </group>

        {/* ESP32-S3 PCB — the heart of Q-VAULT */}
        <group ref={espRef}>
          <primitive object={espGltf.scene} />

          {/* Cryptographic LED — attestation heartbeat */}
          <pointLight
            ref={ledRef}
            position={[0, 0.01, 0]}
            color={accentColor}
            intensity={0}
            distance={0.6}
            decay={2}
          />

          {/* Secure enclave glow mesh */}
          <mesh position={[0, 0.005, 0]}>
            <boxGeometry args={[0.02, 0.002, 0.015]} />
            <meshStandardMaterial
              color={accentColor}
              emissive={accentColor}
              emissiveIntensity={activeScene >= 2 ? 8 : 0}
              transparent
              opacity={0.9}
            />
          </mesh>
        </group>

        {/* Lower aluminium shell */}
        <group ref={downCoverRef}>
          <primitive object={downCoverGltf.scene} />
        </group>

      </group>

      {/* Contact shadow for grounding */}
      <ContactShadows
        position={[0, -0.8, 0]}
        opacity={0.5}
        scale={4}
        blur={1.5}
        far={2}
        color="#000000"
      />

    </group>
  );
}

useGLTF.preload('/models/esp32-s3.glb');
useGLTF.preload('/models/up-cover.glb');
useGLTF.preload('/models/cover-down.glb');
