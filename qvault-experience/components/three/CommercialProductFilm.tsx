'use client';

// ═══════════════════════════════════════════════════════════════
// COMMERCIAL PRODUCT FILM — PHASE XXXV: CINEMATIC RE-DIRECTION
//
// Earn the reveal. Product is a CHARACTER, not a display object.
//
// Visibility structure:
//   ACT I (0-2):   mostly hidden or partial silhouette
//   ACT II (3-5):  visible but extreme macro (overflows frame)
//   ACT III (6-8): FIRST FULL REVEAL — centered, dominant
//   ACT IV (9-10): functional dominance — threat response
//   ACT V (11-12): legendary — stillness, authority
//
// Rotation rules:
//   NO continuous spinning.
//   Rotation only when emotionally motivated.
//   Scene 6 hero: ZERO rotation — absolute frontal authority.
//   Scene 12 seal: ZERO everything — monument.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { safeComposition } from '@/lib/SafeCompositionSystem';

// ── GLB asset paths — PHASE XXXV FINAL ───────────────────────
const MODELS = {
  full: '/models/full-product-without-esp.glb',
  esp:  '/models/esp-product.glb',
  up:   '/models/up.glb',
  down: '/models/down.glb',
} as const;

// ── Fill target — calibrated at hero scene ────────────────────
// Scene 6: z=4.8, fov=25° → visible_h = 2*4.8*tan(12.5°) = 2.13wu
// TARGET slightly below that → ~99% fill on the hero shot
const TARGET_HEIGHT = 2.1;

type Assembly = 'full' | 'exploded';
type Mood     = 'signal' | 'object' | 'system' | 'threat' | 'immortality';

interface SCfg {
  visible:   boolean;
  assembly:  Assembly;
  mood:      Mood;
  explodeWu: number;     // world-unit shell separation
  rotX:      number;     // target rotation X (radians)
  rotY:      number;     // target rotation Y (radians)
  breathAmp: number;     // vertical float amplitude (wu)
  breathHz:  number;     // float frequency (Hz)
}

const S: Record<number, SCfg> = {
  // ── ACT I — THE SIGNAL ────────────────────────────────────────
  // Void: product hidden. Camera stares at empty black.
  0:  { visible:false, assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.000, breathHz:0.00 },
  // Edge macro: product visible but rotated to show ONLY right edge.
  // rotY=-1.30 = 75° turn, so camera [2.8,0,1.8] sees only the rim.
  1:  { visible:true,  assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.04, rotY:-1.30, breathAmp:0.010, breathHz:0.28 },
  // Silhouette: product partially visible, dark awakening mood.
  // rotY=0.55 turns device ~30° from frontal.
  2:  { visible:true,  assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.06, rotY: 0.55, breathAmp:0.012, breathHz:0.30 },

  // ── ACT II — THE OBJECT ───────────────────────────────────────
  // USB-C port: product rotated to expose port side to camera.
  // rotY=+1.45 = 83° — nearly fully sideways, USB-C faces camera [-2.5,0,2.0]
  3:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.02, rotY: 1.45, breathAmp:0.008, breathHz:0.25 },
  // Corner chamfer: diagonal angle to expose top-right corner edge.
  4:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.28, rotY:-0.65, breathAmp:0.008, breathHz:0.28 },
  // PCB silicon: overhead telephoto — camera above looking down.
  // rotX=0.50 tilts product to face the overhead camera [0.1,3.8,2.5]
  5:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.50, rotY: 0.08, breathAmp:0.006, breathHz:0.25 },

  // ── ACT III — THE SYSTEM ──────────────────────────────────────
  // HERO REVEAL: ZERO rotation. Absolute frontal. Product dominates.
  6:  { visible:true,  assembly:'full',     mood:'system',      explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.010, breathHz:0.30 },
  // Exploded assembly — shells separate with ballistic authority.
  7:  { visible:true,  assembly:'exploded', mood:'system',      explodeWu:1.4, rotX: 0.28, rotY: 0.10, breathAmp:0.006, breathHz:0.25 },
  // Low-angle authority — slight backward tilt, camera looks up.
  8:  { visible:true,  assembly:'full',     mood:'system',      explodeWu:0,   rotX:-0.10, rotY: 0.00, breathAmp:0.012, breathHz:0.28 },

  // ── ACT IV — THE THREAT ───────────────────────────────────────
  // Threat close: fast breathing, amber, slight aggressive tilt.
  9:  { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.12, rotY: 0.16, breathAmp:0.022, breathHz:0.60 },
  // Interception: hard intercept angle, contained.
  10: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.08, rotY:-0.20, breathAmp:0.018, breathHz:0.65 },

  // ── ACT V — IMMORTALITY ───────────────────────────────────────
  // Majestic: slow celestial rise, gentle drift. Device transcends.
  11: { visible:true,  assembly:'full',     mood:'immortality', explodeWu:0,   rotX: 0.04, rotY: 0.10, breathAmp:0.016, breathHz:0.20 },
  // Final seal: ABSOLUTE STILLNESS. Monument. Legend. Zero motion.
  12: { visible:true,  assembly:'full',     mood:'immortality', explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.000, breathHz:0.00 },
};

// ── Cinematic lighting per mood ───────────────────────────────
interface LightProfile {
  keyColor: string; keyInt: number;
  rimColor: string; rimInt: number;
  accentColor: string; accentInt: number;
  fillInt: number;
}

const LIGHT: Record<Mood, LightProfile> = {
  //               keyColor        keyInt  rimColor    rimInt  accentColor  accentInt  fillInt
  // ACES filmic tone-mapping heavily compresses dark values.
  // Signal/Object moods need 2x intensity to appear cinematic (not black).
  signal:      { keyColor:'#aac8e0', keyInt:120, rimColor:'#00c8ff', rimInt:85,  accentColor:'#00c8ff', accentInt:6,  fillInt:14 },
  object:      { keyColor:'#c8ddf0', keyInt:110, rimColor:'#00c8ff', rimInt:75,  accentColor:'#00c8ff', accentInt:6,  fillInt:12 },
  system:      { keyColor:'#ddeeff', keyInt:130, rimColor:'#00d4ff', rimInt:85,  accentColor:'#00d4ff', accentInt:8,  fillInt:16 },
  threat:      { keyColor:'#ffe0bb', keyInt:100, rimColor:'#ff8800', rimInt:110, accentColor:'#ff5500', accentInt:12, fillInt:5  },
  immortality: { keyColor:'#d8eeff', keyInt:100, rimColor:'#00c8ff', rimInt:75,  accentColor:'#00c8ff', accentInt:6,  fillInt:14 },
};

// ── Premium PBR materials ─────────────────────────────────────
function useMaterials() {
  const matMetal = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:              new THREE.Color(0x18191c),
    metalness:          0.97,
    roughness:          0.08,  // 0.05 = pure mirror, invisible at oblique angles
    envMapIntensity:    8.0,
    clearcoat:          0.5,
    clearcoatRoughness: 0.08,
    reflectivity:       1.0,
  }), []);

  const matPCB = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:           new THREE.Color(0x040c06),
    metalness:       0.30,
    roughness:       0.65,
    envMapIntensity: 2.5,
  }), []);

  return { matMetal, matPCB };
}

// ── Auto-scale + center from full-product bbox ────────────────
function useBBoxNorm(scene: THREE.Object3D) {
  return useMemo(() => {
    const box  = new THREE.Box3().setFromObject(scene);
    const size = new THREE.Vector3();
    const ctr  = new THREE.Vector3();
    if (box.isEmpty()) return { scale: 55, center: ctr };
    box.getSize(size);
    box.getCenter(ctr);
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale  = maxDim > 0.0001 ? TARGET_HEIGHT / maxDim : 55;
    return { scale, center: ctr };
  }, [scene]);
}

// ─────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────
export function CommercialProductFilm() {
  const groupRef    = useRef<THREE.Group>(null);
  const upRef       = useRef<THREE.Group>(null);
  const downRef     = useRef<THREE.Group>(null);
  const rotXRef     = useRef(0);
  const rotYRef     = useRef(0);
  const explUpRef   = useRef(0);
  const explDownRef = useRef(0);

  const activeScene = useExperienceStore((s) => s.activeScene);
  const camera      = useThree((s) => s.camera);

  // Load all 4 GLBs
  const fullGltf = useGLTF(MODELS.full);
  const espGltf  = useGLTF(MODELS.esp);
  const upGltf   = useGLTF(MODELS.up);
  const downGltf = useGLTF(MODELS.down);

  const { matMetal, matPCB } = useMaterials();

  const { scale: SCALE, center: FULL_CTR } = useBBoxNorm(fullGltf.scene);

  const upCtr   = useMemo(() => { const b=new THREE.Box3().setFromObject(upGltf.scene);   const c=new THREE.Vector3(); if(!b.isEmpty()) b.getCenter(c); return c; }, [upGltf.scene]);
  const downCtr = useMemo(() => { const b=new THREE.Box3().setFromObject(downGltf.scene); const c=new THREE.Vector3(); if(!b.isEmpty()) b.getCenter(c); return c; }, [downGltf.scene]);

  // Apply materials once on load
  useEffect(() => {
    [fullGltf.scene, upGltf.scene, downGltf.scene].forEach((s) =>
      s.traverse((c) => {
        if (c instanceof THREE.Mesh) { c.material = matMetal; }
      })
    );
    espGltf.scene.traverse((c) => {
      if (c instanceof THREE.Mesh) { c.material = matPCB; }
    });
  }, [fullGltf.scene, espGltf.scene, upGltf.scene, downGltf.scene, matMetal, matPCB]);

  // Attach camera ref for SafeCompositionSystem
  useEffect(() => {
    if (groupRef.current) safeComposition.attachCamera(groupRef.current, camera);
  }, [camera]);

  // ── Per-frame animation ──────────────────────────────────────
  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const dt  = Math.min(delta, 0.05);
    const t   = state.clock.elapsedTime;
    const cfg = S[activeScene] ?? S[6];

    // 1. Breathing — vertical float (zero on sealed scenes)
    groupRef.current.position.y = cfg.breathHz > 0
      ? Math.sin(t * cfg.breathHz * Math.PI * 2) * cfg.breathAmp
      : 0;

    // 2. Deliberate snap rotation — NO continuous spinning
    // ACT II macro shots need faster spring to settle on their angle
    const rotSpring = activeScene >= 3 && activeScene <= 5 ? 3.5 : 2.8;
    rotXRef.current += (cfg.rotX - rotXRef.current) * dt * rotSpring;
    rotYRef.current += (cfg.rotY - rotYRef.current) * dt * (rotSpring * 0.85);
    groupRef.current.rotation.x = rotXRef.current;
    groupRef.current.rotation.y = rotYRef.current;

    // 3. Exploded shell movement
    const localExplode = cfg.explodeWu / SCALE;
    const tUp   = cfg.assembly === 'exploded' ?  localExplode       : 0;
    const tDown = cfg.assembly === 'exploded' ? -localExplode * 0.6 : 0;
    if (upRef.current) {
      explUpRef.current   += (tUp   - explUpRef.current)   * dt * 3.2;
      upRef.current.position.y = explUpRef.current;
    }
    if (downRef.current) {
      explDownRef.current += (tDown - explDownRef.current) * dt * 3.2;
      downRef.current.position.y = explDownRef.current;
    }

    // 4. SafeCompositionSystem report
    safeComposition.reportProductGroup(groupRef.current, SCALE);
  });

  const cfg  = S[activeScene] ?? S[6];
  const lp   = LIGHT[cfg.mood];
  const expl = cfg.assembly === 'exploded';

  return (
    <group ref={groupRef} visible={cfg.visible}>

      {/* IBL — studio metallic response */}
      <Environment preset="studio" />

      {/* KEY LIGHT — precision white */}
      <spotLight
        position={[7, 14, 10]}
        angle={0.20} penumbra={0.90}
        intensity={lp.keyInt} color={lp.keyColor}
      />

      {/* RIM LIGHT — sovereign separation */}
      <spotLight
        position={[-10, 6, -14]}
        angle={0.24} penumbra={0.75}
        intensity={lp.rimInt} color={lp.rimColor}
      />

      {/* SECONDARY RIM — right rear */}
      <spotLight
        position={[9, 3, -10]}
        angle={0.30} penumbra={0.80}
        intensity={lp.rimInt * 0.28} color={lp.keyColor}
      />

      {/* FILL — low-angle detail recovery */}
      <directionalLight position={[2, -5, 8]} intensity={lp.fillInt} color="#9ab0c4" />

      {/* NEGATIVE FILL — shadow sculpture, not scene-blackout */}
      <directionalLight position={[-6, -3, -8]} intensity={-4} color="#000000" />

      {/* AMBIENT BASE — ensures product reads as silhouette even in dark scenes */}
      <ambientLight intensity={0.40} color="#1a2a38" />

      {/* ACCENT GLOW — sovereign color near device */}
      <pointLight position={[0, 0, 2.5]} intensity={lp.accentInt} color={lp.accentColor} distance={6} decay={2} />

      {/* CAMERA-POSITION FILL — ensures product always reads
          as a physical 3D object regardless of camera angle.
          This is a "beauty light" photographic technique. */}
      <pointLight position={[0, 0, 8]} intensity={8} color="#c8ddf0" distance={20} decay={1.5} />

      {/* ════════════════════════════════════════════════════
          PRODUCT HIERARCHY
          Scaled from full-product bbox → TARGET_HEIGHT fill.
          ════════════════════════════════════════════════════ */}
      <group
        scale={SCALE}
        position={[-FULL_CTR.x, -FULL_CTR.y, -FULL_CTR.z]}
      >
        {/* ASSEMBLED — full enclosure + PCB */}
        <group visible={!expl}>
          <primitive object={fullGltf.scene} />
          <primitive object={espGltf.scene} />
        </group>

        {/* EXPLODED — individual shells with pivot correction */}
        <group visible={expl}>
          <group ref={upRef}>
            <group position={[-upCtr.x, -upCtr.y, -upCtr.z]}>
              <primitive object={upGltf.scene} />
            </group>
          </group>
          <primitive object={espGltf.scene} />
          <group ref={downRef}>
            <group position={[-downCtr.x, -downCtr.y, -downCtr.z]}>
              <primitive object={downGltf.scene} />
            </group>
          </group>
        </group>
      </group>

      {/* Ground shadow plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.4, 0]}>
        <planeGeometry args={[6, 6]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.16} />
      </mesh>
    </group>
  );
}

// Preload all Phase XXXV assets
useGLTF.preload(MODELS.full);
useGLTF.preload(MODELS.esp);
useGLTF.preload(MODELS.up);
useGLTF.preload(MODELS.down);
