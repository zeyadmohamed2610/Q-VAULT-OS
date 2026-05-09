'use client';

// ═══════════════════════════════════════════════════════════════
// COMMERCIAL PRODUCT FILM — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// Performance targets:
//   60fps on mid-range GPU | 45fps on iGPU
//
// What was removed vs OMEGA:
//   × Environment IBL (expensive cubemap convolution)
//   × 8 spot lights → 3 directional + 2 point max
//   × Real-time LED emissive mutation (GC pressure)
//   × Per-frame bbox calculations
//   × Clearcoat pass (extra shader complexity)
//
// What was kept / improved:
//   ✓ Dark titanium enclosure: roughness 0.12, metalness 0.95
//   ✓ Dark navy PCB: roughness 0.55, gold emissive traces
//   ✓ Shared material refs — only 3 material objects total
//   ✓ Memoized geometry refs
//   ✓ Spring-damped motion — no useFrame overdraw
//   ✓ Explicit product visibility per scene
//   ✓ Exploded view with authority snap
//
// Materials: 3 total. No per-frame creation.
// Lights: max 5 total. Quality-tier adaptive.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { getQualityProfile } from '@/lib/AdaptiveQuality';

// ── GLB assets ────────────────────────────────────────────────
const MODELS = {
  full: '/models/full-product-without-esp.glb',
  esp:  '/models/esp-product.glb',
  up:   '/models/up.glb',
  down: '/models/down.glb',
} as const;

// Product visual height target (world units)
const TARGET_HEIGHT = 2.1;

// ── Scene choreography — 10 scenes ───────────────────────────
// [visible, exploded, rotX, rotY, breathAmp, breathHz, explodeSep]
type SCfg = {
  visible: boolean; exploded: boolean;
  rotX: number; rotY: number;
  breathAmp: number; breathHz: number;
  explodeSep: number;
  mood: 'cold' | 'warm' | 'threat';
};

const SCENES: Record<number, SCfg> = {
  0: { visible:false, exploded:false, rotX:0.00, rotY:0.00, breathAmp:0,     breathHz:0,    explodeSep:0, mood:'cold' },
  1: { visible:true,  exploded:false, rotX:0.00, rotY:0.00, breathAmp:0.012, breathHz:0.25, explodeSep:0, mood:'cold' },
  2: { visible:true,  exploded:false, rotX:0.03, rotY:1.50, breathAmp:0.008, breathHz:0.24, explodeSep:0, mood:'cold' },
  3: { visible:true,  exploded:false, rotX:0.52, rotY:0.05, breathAmp:0.006, breathHz:0.22, explodeSep:0, mood:'cold' },
  4: { visible:true,  exploded:false, rotX:0.28, rotY:-0.55, breathAmp:0.007, breathHz:0.26, explodeSep:0, mood:'cold' },
  5: { visible:true,  exploded:false, rotX:0.00, rotY:0.00, breathAmp:0.010, breathHz:0.28, explodeSep:0, mood:'cold' },
  6: { visible:true,  exploded:false, rotX:-0.06, rotY:0.00, breathAmp:0.008, breathHz:0.22, explodeSep:0, mood:'cold' },
  7: { visible:true,  exploded:false, rotX:0.10, rotY:-0.25, breathAmp:0.009, breathHz:0.25, explodeSep:0, mood:'cold' },
  8: { visible:true,  exploded:true,  rotX:0.22, rotY:0.18, breathAmp:0.007, breathHz:0.20, explodeSep:1.5, mood:'cold' },
  9: { visible:true,  exploded:false, rotX:0.00, rotY:0.00, breathAmp:0.000, breathHz:0,    explodeSep:0, mood:'cold' },
};

// ── Cinematic light profiles — 3 moods ───────────────────────
// Lights per mood: 3 directional + 1-2 point = max 5 draw calls
// All intensities tuned for ACES filmic (requires 2-4x physical).
interface LightCfg {
  keyDir: [number,number,number]; keyColor: string; keyInt: number;
  rimDir: [number,number,number]; rimColor: string; rimInt: number;
  fillDir:[number,number,number]; fillInt: number;
  pointColor: string; pointInt: number;
  ambInt: number; ambColor: string;
}

const LIGHT: Record<'cold'|'warm'|'threat', LightCfg> = {
  cold: {
    keyDir:   [4, 10, 8],    keyColor:  '#d8eeff', keyInt:  3.0,
    rimDir:   [-8, 4, -10],  rimColor:  '#7FE8FF', rimInt:  2.2,
    fillDir:  [0, -4, 6],    fillInt:   0.6,
    pointColor:'#7FE8FF',    pointInt:  0.5,
    ambInt:    0.18,          ambColor:  '#080e16',
  },
  warm: {
    keyDir:   [4, 10, 8],    keyColor:  '#ffe8c8', keyInt:  2.8,
    rimDir:   [-8, 4, -10],  rimColor:  '#FF8C00', rimInt:  1.8,
    fillDir:  [0, -4, 6],    fillInt:   0.4,
    pointColor:'#FF8C00',    pointInt:  0.8,
    ambInt:    0.12,          ambColor:  '#120800',
  },
  threat: {
    keyDir:   [4, 10, 8],    keyColor:  '#ffd080', keyInt:  2.6,
    rimDir:   [-8, 4, -10],  rimColor:  '#CC2200', rimInt:  2.5,
    fillDir:  [0, -4, 6],    fillInt:   0.2,
    pointColor:'#CC2200',    pointInt:  1.2,
    ambInt:    0.08,          ambColor:  '#180400',
  },
};

// ── Pre-allocated animation vectors ──────────────────────────
const _rotXCur = { v: 0 };
const _rotYCur = { v: 0 };
const _explUpCur   = { v: 0 };
const _explDownCur = { v: 0 };

// ─────────────────────────────────────────────────────────────
export function CommercialProductFilm() {
  const groupRef  = useRef<THREE.Group>(null);
  const upRef     = useRef<THREE.Group>(null);
  const downRef   = useRef<THREE.Group>(null);
  const activeScene = useExperienceStore((s) => s.activeScene);
  const quality   = useMemo(() => getQualityProfile(), []);

  const { scene: fullScene } = useGLTF(MODELS.full);
  const { scene: espScene  } = useGLTF(MODELS.esp);
  const { scene: upScene   } = useGLTF(MODELS.up);
  const { scene: downScene } = useGLTF(MODELS.down);

  // ── 3 shared materials — created ONCE, never mutated per frame ─
  const matMetal = useMemo(() => new THREE.MeshStandardMaterial({
    color:           new THREE.Color(0x131517),  // dark titanium
    metalness:       0.95,
    roughness:       0.12,
    envMapIntensity: quality.environmentIBL ? 1.0 : 0.0,
  }), [quality.environmentIBL]);

  const matPCB = useMemo(() => new THREE.MeshStandardMaterial({
    color:             new THREE.Color(0x060a0f),  // dark military navy
    metalness:         0.40,
    roughness:         0.58,
    emissive:          new THREE.Color(0x0d0800),  // faint copper trace glow
    emissiveIntensity: 0.25,
    envMapIntensity:   quality.environmentIBL ? 0.5 : 0.0,
  }), [quality.environmentIBL]);

  const matLED = useMemo(() => new THREE.MeshBasicMaterial({
    color: new THREE.Color(0x7FE8FF),
  }), []);

  // ── Scale from bbox — computed once per GLB load ─────────────
  const { SCALE, fullCtr, upCtr, downCtr } = useMemo(() => {
    const bb = new THREE.Box3().setFromObject(fullScene);
    const sz = new THREE.Vector3();
    const c  = new THREE.Vector3();
    bb.getSize(sz); bb.getCenter(c);
    const maxD = Math.max(sz.x, sz.y, sz.z);
    const sc   = maxD > 0.0001 ? TARGET_HEIGHT / maxD : 50;

    const bUp   = new THREE.Box3().setFromObject(upScene);
    const cUp   = new THREE.Vector3(); bUp.getCenter(cUp);
    const bDn   = new THREE.Box3().setFromObject(downScene);
    const cDn   = new THREE.Vector3(); bDn.getCenter(cDn);
    return { SCALE: sc, fullCtr: c, upCtr: cUp, downCtr: cDn };
  }, [fullScene, upScene, downScene]);

  // ── Apply materials once on mount ────────────────────────────
  useEffect(() => {
    [fullScene, upScene, downScene].forEach((s) =>
      s.traverse((ch) => {
        if (ch instanceof THREE.Mesh) {
          ch.material = matMetal;
          ch.castShadow = false;
          ch.receiveShadow = false;
          // Frustum cull aggressively
          ch.frustumCulled = true;
        }
      })
    );
    espScene.traverse((ch) => {
      if (ch instanceof THREE.Mesh) {
        const isLED = ch.name.toLowerCase().includes('led');
        ch.material = isLED ? matLED : matPCB;
        ch.castShadow = false;
        ch.receiveShadow = false;
        ch.frustumCulled = true;
      }
    });
  }, [fullScene, espScene, upScene, downScene, matMetal, matPCB, matLED]);

  // ── Per-frame animation — LEAN: only spring + breath ─────────
  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const dt = Math.min(delta, 0.05);
    const t  = state.clock.elapsedTime;
    const c  = SCENES[activeScene] ?? SCENES[5];

    // Breathing — vertical float (skip on final scene)
    groupRef.current.position.y = c.breathHz > 0
      ? Math.sin(t * c.breathHz * Math.PI * 2) * c.breathAmp
      : 0;

    // Rotation spring — fast settle (5.0 constant)
    _rotXCur.v += (c.rotX - _rotXCur.v) * dt * 5.0;
    _rotYCur.v += (c.rotY - _rotYCur.v) * dt * 4.5;
    groupRef.current.rotation.x = _rotXCur.v;
    groupRef.current.rotation.y = _rotYCur.v;

    // Exploded shell Y separation
    const localSep = c.explodeSep / SCALE;
    const tUp   = c.exploded ? localSep       : 0;
    const tDown = c.exploded ? -localSep * 0.6 : 0;
    _explUpCur.v   += (tUp   - _explUpCur.v)   * dt * 3.5;
    _explDownCur.v += (tDown - _explDownCur.v) * dt * 3.5;
    if (upRef.current)   upRef.current.position.y   = _explUpCur.v;
    if (downRef.current) downRef.current.position.y = _explDownCur.v;
  });

  const cfg  = SCENES[activeScene] ?? SCENES[5];
  const lp   = LIGHT[cfg.mood];
  const expl = cfg.exploded;

  return (
    <group ref={groupRef} visible={cfg.visible}>

      {/* ── 3-point light system (max 5 lights total) ────────── */}
      {/* KEY — primary dramatic fill */}
      <directionalLight
        position={lp.keyDir}
        intensity={lp.keyInt}
        color={lp.keyColor}
      />
      {/* RIM — edge separation, the "expensive" look */}
      <directionalLight
        position={lp.rimDir}
        intensity={lp.rimInt}
        color={lp.rimColor}
      />
      {/* FILL — low-angle shadow recovery */}
      <directionalLight
        position={lp.fillDir}
        intensity={lp.fillInt}
        color="#8899bb"
      />
      {/* ACCENT — tight point glow near product surface */}
      {quality.maxLights >= 4 && (
        <pointLight
          position={[0, 0, 3.5]}
          intensity={lp.pointInt}
          color={lp.pointColor}
          distance={7}
          decay={2}
        />
      )}
      {/* AMBIENT — prevents ACES from crushing darks */}
      <ambientLight intensity={lp.ambInt} color={lp.ambColor} />

      {/* ── Product hierarchy ─────────────────────────────────── */}
      <group scale={SCALE} position={[-fullCtr.x, -fullCtr.y, -fullCtr.z]}>

        {/* ASSEMBLED view */}
        <group visible={!expl}>
          <primitive object={fullScene} />
          <primitive object={espScene} />
        </group>

        {/* EXPLODED view */}
        <group visible={expl}>
          <group ref={upRef}>
            <group position={[-upCtr.x, -upCtr.y, -upCtr.z]}>
              <primitive object={upScene} />
            </group>
          </group>
          <primitive object={espScene} />
          <group ref={downRef}>
            <group position={[-downCtr.x, -downCtr.y, -downCtr.z]}>
              <primitive object={downScene} />
            </group>
          </group>
        </group>
      </group>

      {/* Soft ground shadow — single plane, no shadow map ─────── */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.6, 0]}>
        <planeGeometry args={[6, 6]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.18} />
      </mesh>
    </group>
  );
}

// Preload all assets at module import time
useGLTF.preload(MODELS.full);
useGLTF.preload(MODELS.esp);
useGLTF.preload(MODELS.up);
useGLTF.preload(MODELS.down);
