'use client';

// ═══════════════════════════════════════════════════════════════
// COMMERCIAL PRODUCT FILM — PHASE OMEGA: CINEMATIC REBIRTH
//
// Theme: "THE DEVICE THAT OUTLIVES SYSTEMS."
//
// MATERIAL REDESIGN:
//   Enclosure: dark titanium, brushed anisotropic metal
//   PCB: dark military navy, cyber circuitry, emissive LEDs
//   Both: premium PBR with clearcoat, micro-roughness variation
//
// PRODUCT ORIENTATION RULES:
//   Hero face ALWAYS toward viewer.
//   Logo side readable in reveal shots.
//   NO random spinning. Motion = intent.
//
// SCENE CHOREOGRAPHY (19 scenes):
//   ACT I (0-3):   hidden/macro — mystery, first contact
//   ACT II (4-7):  telephoto fragments — desire, premium
//   ACT III (8-10): HERO REVEAL — 70-85% fill, authority
//   ACT IV (11-15): RAPID CUTS — threat, kinetic, aggressive
//   ACT V (16-18): IMMORTALITY — monumental, sealed
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { useGLTF, Environment } from '@react-three/drei';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { safeComposition } from '@/lib/SafeCompositionSystem';

// ── GLB asset paths ───────────────────────────────────────────
const MODELS = {
  full: '/models/full-product-without-esp.glb',
  esp:  '/models/esp-product.glb',
  up:   '/models/up.glb',
  down: '/models/down.glb',
} as const;

// ── Frame fill target ─────────────────────────────────────────
// Hero scene 8: z=5.2, fov=23° → visible_h = 2*5.2*tan(11.5°) ≈ 2.12wu
// Product ~2.1wu tall → ~99% fill
const TARGET_HEIGHT = 2.1;

type Assembly = 'full' | 'exploded';
type Mood     = 'signal' | 'object' | 'reveal' | 'threat' | 'immortality';

interface SCfg {
  visible:    boolean;
  assembly:   Assembly;
  mood:       Mood;
  explodeWu:  number;   // shell separation in world units
  rotX:       number;   // target X rotation (radians)
  rotY:       number;   // target Y rotation (radians)
  breathAmp:  number;   // vertical float amplitude
  breathHz:   number;   // float frequency (Hz)
  ledPulse:   boolean;  // emit LED glow this scene
}

// ── Per-scene product choreography ────────────────────────────
// rotY positive = turns left (shows right side to camera)
// rotY negative = turns right (shows left side to camera)
// rotX positive = tilts top toward camera (PCB faces forward)
// rotX negative = tilts bottom toward camera (looks up at device)
const S: Record<number, SCfg> = {
  // ── ACT I — THE SIGNAL ─────────────────────────────────────
  0:  { visible:false, assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.000, breathHz:0.00, ledPulse:false },
  // LED blink: tilted to show PCB surface. Camera above-close.
  1:  { visible:true,  assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.55, rotY: 0.12, breathAmp:0.006, breathHz:0.22, ledPulse:true  },
  // Edge macro: hard rotY to show only right edge rim.
  2:  { visible:true,  assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.05, rotY:-1.35, breathAmp:0.010, breathHz:0.28, ledPulse:false },
  // Boot texture: top surface faces camera, slight diagonal.
  3:  { visible:true,  assembly:'full',     mood:'signal',      explodeWu:0,   rotX: 0.45, rotY:-0.35, breathAmp:0.008, breathHz:0.25, ledPulse:true  },

  // ── ACT II — ENGINEERED OBJECT ─────────────────────────────
  // USB-C: rotated to expose left side/port to camera.
  4:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.03, rotY: 1.48, breathAmp:0.007, breathHz:0.24, ledPulse:false },
  // Seam: corner angle, elevated, enclosure split visible.
  5:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.30, rotY:-0.60, breathAmp:0.007, breathHz:0.26, ledPulse:false },
  // PCB: tilts forward to face overhead camera.
  6:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.52, rotY: 0.05, breathAmp:0.005, breathHz:0.22, ledPulse:true  },
  // Reflection sweep: 3/4 angle, shows metallic sheen.
  7:  { visible:true,  assembly:'full',     mood:'object',      explodeWu:0,   rotX: 0.12, rotY: 0.42, breathAmp:0.009, breathHz:0.30, ledPulse:false },

  // ── ACT III — FULL REVEAL ──────────────────────────────────
  // HERO: ZERO rotation. Dead frontal. Logo faces viewer. Authority.
  8:  { visible:true,  assembly:'full',     mood:'reveal',      explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.012, breathHz:0.28, ledPulse:true  },
  // Exploded: shells separate dramatically. 3/4 view.
  9:  { visible:true,  assembly:'exploded', mood:'reveal',      explodeWu:1.6, rotX: 0.25, rotY: 0.15, breathAmp:0.007, breathHz:0.22, ledPulse:true  },
  // Pedestal: slight backward tilt. Camera looks up. Monumental.
  10: { visible:true,  assembly:'full',     mood:'reveal',      explodeWu:0,   rotX:-0.08, rotY: 0.00, breathAmp:0.010, breathHz:0.26, ledPulse:true  },

  // ── ACT IV — THE THREAT (RAPID CUTS) ───────────────────────
  // Fast breathing, aggressive tilts, amber lighting takes over.
  11: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.14, rotY: 0.22, breathAmp:0.030, breathHz:0.80, ledPulse:false },
  12: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX:-0.10, rotY:-0.18, breathAmp:0.025, breathHz:0.90, ledPulse:false },
  13: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.18, rotY:-0.30, breathAmp:0.028, breathHz:0.85, ledPulse:false },
  14: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.06, rotY: 0.12, breathAmp:0.018, breathHz:0.60, ledPulse:true  },
  // Zero knowledge: snap back to frontal. Cyan returns.
  15: { visible:true,  assembly:'full',     mood:'threat',      explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.012, breathHz:0.50, ledPulse:true  },

  // ── ACT V — IMMORTALITY ────────────────────────────────────
  // Slow. Majestic. Monumental.
  16: { visible:true,  assembly:'full',     mood:'immortality', explodeWu:0,   rotX: 0.04, rotY: 0.08, breathAmp:0.018, breathHz:0.18, ledPulse:true  },
  // Logo reveal: perfectly centered. Hero.
  17: { visible:true,  assembly:'full',     mood:'immortality', explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.010, breathHz:0.16, ledPulse:true  },
  // Final seal: ABSOLUTE STILLNESS. Monument. Legend.
  18: { visible:true,  assembly:'full',     mood:'immortality', explodeWu:0,   rotX: 0.00, rotY: 0.00, breathAmp:0.000, breathHz:0.00, ledPulse:false },
};

// ── PREMIUM CINEMATIC LIGHTING ────────────────────────────────
// Three-point photographic light system per mood.
// ACES filmic requires 2-4x physical light units vs Reinhard.
interface LightProfile {
  // Key: main dramatic illumination
  keyColor: string; keyInt: number;
  // Rim: edge separation — the "expensive" look
  rimColor: string; rimInt: number;
  rimColor2: string; rimInt2: number; // second rim for dimension
  // Fill: shadow recovery without killing drama
  fillInt: number;
  // Accent: tight point light near device
  accentColor: string; accentInt: number;
  // Ambient: prevents pure-black crush
  ambientInt: number; ambientColor: string;
  // Camera fill: photographic "beauty light"
  beautyInt: number;
}

const LIGHT: Record<Mood, LightProfile> = {
  // signal — cyan ice, mysterious, barely there
  signal: {
    keyColor:    '#aac8e0', keyInt:    110,
    rimColor:    '#7FE8FF', rimInt:    100,
    rimColor2:   '#4488aa', rimInt2:   35,
    fillInt:     16,
    accentColor: '#7FE8FF', accentInt: 10,
    ambientInt:  0.35,      ambientColor: '#0a1520',
    beautyInt:   10,
  },
  // object — cool white/cyan, reveals premium material
  object: {
    keyColor:    '#d0e4f0', keyInt:    120,
    rimColor:    '#7FE8FF', rimInt:    90,
    rimColor2:   '#3366aa', rimInt2:   40,
    fillInt:     18,
    accentColor: '#7FE8FF', accentInt: 8,
    ambientInt:  0.38,      ambientColor: '#0d1a28',
    beautyInt:   12,
  },
  // reveal — premium studio: white key, cyan rim, deep fill
  // Maximum: this is the hero shot. Everything in service of product.
  reveal: {
    keyColor:    '#f0f4ff', keyInt:    150,
    rimColor:    '#7FE8FF', rimInt:    120,
    rimColor2:   '#ffffff', rimInt2:   45,
    fillInt:     22,
    accentColor: '#7FE8FF', accentInt: 12,
    ambientInt:  0.45,      ambientColor: '#101828',
    beautyInt:   16,
  },
  // threat — amber/red dominates. Danger. Urgency.
  threat: {
    keyColor:    '#ffc880', keyInt:    105,
    rimColor:    '#ff6600', rimInt:    130,
    rimColor2:   '#cc2200', rimInt2:   60,
    fillInt:     8,
    accentColor: '#ff4400', accentInt: 18,
    ambientInt:  0.25,      ambientColor: '#180800',
    beautyInt:   8,
  },
  // immortality — deep cyan, violet undertones, eternal
  immortality: {
    keyColor:    '#e0f0ff', keyInt:    110,
    rimColor:    '#7FE8FF', rimInt:    95,
    rimColor2:   '#8866ff', rimInt2:   30,  // subtle violet
    fillInt:     16,
    accentColor: '#7FE8FF', accentInt: 9,
    ambientInt:  0.40,      ambientColor: '#0a1020',
    beautyInt:   12,
  },
};

// ── PHASE OMEGA MATERIALS — PREMIUM PBR ──────────────────────
function useMaterials(ledPulse: boolean, time: number) {
  // ENCLOSURE: Dark titanium/ceramic graphite.
  // "Apple meets military hardware."
  const matMetal = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:              new THREE.Color(0x141618),  // dark titanium
    metalness:          0.95,
    roughness:          0.10,    // brushed metal — some scatter
    envMapIntensity:    9.0,
    clearcoat:          0.6,
    clearcoatRoughness: 0.12,
    reflectivity:       1.0,
    // anisotropy requires WebGPU; simulate with roughness variation
  }), []);

  // PCB: COMPLETELY REDESIGNED.
  // Dark military navy — NOT white. Classified, expensive.
  const matPCB = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:           new THREE.Color(0x06090f),  // deep navy/graphite blue
    metalness:       0.45,                        // circuit board metallics
    roughness:       0.55,                        // matte but present
    envMapIntensity: 3.5,
    // Copper trace emissive — soft gold glow
    emissive:        new THREE.Color(0x1a0e04),
    emissiveIntensity: 0.3,
  }), []);

  // LED: bright cyan emissive point.
  // Pulses with breathHz when ledPulse=true.
  const ledIntensity = ledPulse
    ? 0.6 + Math.sin(time * 1.2 * Math.PI * 2) * 0.4
    : 0.0;

  const matLED = useMemo(() => new THREE.MeshPhysicalMaterial({
    color:             new THREE.Color(0x7FE8FF),
    emissive:          new THREE.Color(0x7FE8FF),
    emissiveIntensity: 0, // updated per frame via material reference
    metalness:         0.0,
    roughness:         0.0,
  }), []);
  matLED.emissiveIntensity = ledIntensity;

  return { matMetal, matPCB, matLED };
}

// ── Auto-scale from bbox ──────────────────────────────────────
function useBBoxNorm(scene: THREE.Object3D) {
  return useMemo(() => {
    const box = new THREE.Box3().setFromObject(scene);
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
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────
export function CommercialProductFilm() {
  const groupRef    = useRef<THREE.Group>(null);
  const upRef       = useRef<THREE.Group>(null);
  const downRef     = useRef<THREE.Group>(null);
  const rotXRef     = useRef(0);
  const rotYRef     = useRef(0);
  const explUpRef   = useRef(0);
  const explDownRef = useRef(0);
  const timeRef     = useRef(0);

  const activeScene = useExperienceStore((s) => s.activeScene);
  const camera      = useThree((s) => s.camera);

  const fullGltf = useGLTF(MODELS.full);
  const espGltf  = useGLTF(MODELS.esp);
  const upGltf   = useGLTF(MODELS.up);
  const downGltf = useGLTF(MODELS.down);

  const cfg = S[activeScene] ?? S[8];
  const { matMetal, matPCB, matLED } = useMaterials(cfg.ledPulse, timeRef.current);

  const { scale: SCALE, center: FULL_CTR } = useBBoxNorm(fullGltf.scene);
  const upCtr   = useMemo(() => { const b = new THREE.Box3().setFromObject(upGltf.scene);   const c = new THREE.Vector3(); if (!b.isEmpty()) b.getCenter(c); return c; }, [upGltf.scene]);
  const downCtr = useMemo(() => { const b = new THREE.Box3().setFromObject(downGltf.scene); const c = new THREE.Vector3(); if (!b.isEmpty()) b.getCenter(c); return c; }, [downGltf.scene]);

  // Apply Phase OMEGA materials on load
  useEffect(() => {
    // Enclosure shells: dark titanium
    [fullGltf.scene, upGltf.scene, downGltf.scene].forEach((s) =>
      s.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.material = matMetal;
          child.castShadow    = true;
          child.receiveShadow = false;
        }
      })
    );
    // PCB: dark military navy + LED detection
    espGltf.scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        // Detect LED geometry by name or size heuristic
        const geomBB = new THREE.Box3().setFromObject(child);
        const size   = new THREE.Vector3();
        geomBB.getSize(size);
        const vol = size.x * size.y * size.z;
        // LEDs are very small components
        if (vol < 0.000005 && child.name.toLowerCase().includes('led')) {
          child.material = matLED;
        } else {
          child.material = matPCB;
        }
      }
    });
  }, [fullGltf.scene, espGltf.scene, upGltf.scene, downGltf.scene, matMetal, matPCB, matLED]);

  // Attach camera for SafeCompositionSystem
  useEffect(() => {
    if (groupRef.current) safeComposition.attachCamera(groupRef.current, camera);
  }, [camera]);

  // ── Per-frame animation ──────────────────────────────────────
  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const dt  = Math.min(delta, 0.05);
    const t   = state.clock.elapsedTime;
    timeRef.current = t;
    const c = S[activeScene] ?? S[8];

    // 1. Breathing — vertical float
    groupRef.current.position.y = c.breathHz > 0
      ? Math.sin(t * c.breathHz * Math.PI * 2) * c.breathAmp
      : 0;

    // 2. Rotation spring — intentional, emotionally motivated
    // Threat scenes: faster spring (kinetic urgency)
    // Macro scenes: fast spring (settle on extreme angle)
    const isThreat = activeScene >= 11 && activeScene <= 15;
    const isMacro  = activeScene >= 1  && activeScene <= 7;
    const rotSpring = isThreat ? 6.0 : isMacro ? 4.5 : 3.0;
    rotXRef.current += (c.rotX - rotXRef.current) * dt * rotSpring;
    rotYRef.current += (c.rotY - rotYRef.current) * dt * (rotSpring * 0.88);
    groupRef.current.rotation.x = rotXRef.current;
    groupRef.current.rotation.y = rotYRef.current;

    // 3. Exploded shell animation
    const localExplode = c.explodeWu / SCALE;
    const tUp   = c.assembly === 'exploded' ?  localExplode       : 0;
    const tDown = c.assembly === 'exploded' ? -localExplode * 0.6 : 0;
    if (upRef.current) {
      explUpRef.current += (tUp - explUpRef.current) * dt * 4.0;
      upRef.current.position.y = explUpRef.current;
    }
    if (downRef.current) {
      explDownRef.current += (tDown - explDownRef.current) * dt * 4.0;
      downRef.current.position.y = explDownRef.current;
    }

    // 4. Update LED emissive in real-time
    if (c.ledPulse) {
      const pulse = 0.6 + Math.sin(t * 1.5 * Math.PI * 2) * 0.35;
      matLED.emissiveIntensity = pulse;
    } else {
      matLED.emissiveIntensity = 0;
    }

    // 5. SafeCompositionSystem
    safeComposition.reportProductGroup(groupRef.current, SCALE);
  });

  const lp   = LIGHT[cfg.mood];
  const expl = cfg.assembly === 'exploded';

  return (
    <group ref={groupRef} visible={cfg.visible}>

      {/* ── IBL: City environment for premium metallic reflections */}
      <Environment preset="city" />

      {/* ── KEY LIGHT: main dramatic illumination ── */}
      <spotLight
        position={[6, 14, 10]}
        angle={0.18}
        penumbra={0.92}
        intensity={lp.keyInt}
        color={lp.keyColor}
      />

      {/* ── PRIMARY RIM: edge separation, the "expensive" light ── */}
      <spotLight
        position={[-10, 5, -14]}
        angle={0.22}
        penumbra={0.80}
        intensity={lp.rimInt}
        color={lp.rimColor}
      />

      {/* ── SECONDARY RIM: dimensional fill from right-rear ── */}
      <spotLight
        position={[10, 3, -10]}
        angle={0.28}
        penumbra={0.85}
        intensity={lp.rimInt2}
        color={lp.rimColor2}
      />

      {/* ── FILL: low-angle shadow recovery ── */}
      <directionalLight
        position={[2, -5, 8]}
        intensity={lp.fillInt}
        color="#9ab8cc"
      />

      {/* ── KICKER: under-bounce, premium material reveal ── */}
      <directionalLight
        position={[0, -8, 4]}
        intensity={lp.fillInt * 0.25}
        color={lp.rimColor}
      />

      {/* ── NEGATIVE FILL: sculpt shadows, NOT blackout ── */}
      <directionalLight
        position={[-6, -4, -8]}
        intensity={-3}
        color="#000000"
      />

      {/* ── AMBIENT: prevent ACES from crushing dark to black ── */}
      <ambientLight
        intensity={lp.ambientInt}
        color={lp.ambientColor}
      />

      {/* ── ACCENT GLOW: tight point near device surface ── */}
      <pointLight
        position={[0.5, 0.5, 2.5]}
        intensity={lp.accentInt}
        color={lp.accentColor}
        distance={6}
        decay={2}
      />

      {/* ── BEAUTY LIGHT: photographic front fill ── */}
      <pointLight
        position={[0, 0, 8]}
        intensity={lp.beautyInt}
        color="#c8ddf0"
        distance={22}
        decay={1.2}
      />

      {/* ── LED GLOW: emissive halo when ledPulse=true ── */}
      {cfg.ledPulse && (
        <pointLight
          position={[0, 0.3, 1.8]}
          intensity={3.5}
          color="#7FE8FF"
          distance={3}
          decay={3}
        />
      )}

      {/* ════════════════════════════════════════════════════
          PRODUCT HIERARCHY — scaled from bbox → TARGET_HEIGHT
          ════════════════════════════════════════════════════ */}
      <group
        scale={SCALE}
        position={[-FULL_CTR.x, -FULL_CTR.y, -FULL_CTR.z]}
      >
        {/* ASSEMBLED — enclosure + PCB */}
        <group visible={!expl}>
          <primitive object={fullGltf.scene} />
          <primitive object={espGltf.scene} />
        </group>

        {/* EXPLODED — shells separate with authority */}
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

      {/* ── Ground contact shadow ── */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.6, 0]}>
        <planeGeometry args={[8, 8]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.20} />
      </mesh>
    </group>
  );
}

// Preload all assets
useGLTF.preload(MODELS.full);
useGLTF.preload(MODELS.esp);
useGLTF.preload(MODELS.up);
useGLTF.preload(MODELS.down);
