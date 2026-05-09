// ═══════════════════════════════════════════════════════════════
// THREAT LATTICE FIELD
// 3D Point cloud structure that begins stable and collapses
// as the user scrolls deeper into the Scene 1 narrative.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useExperienceStore } from '@/lib/store';
import { FILM_MOTION_SCALE, PALETTE } from '@/lib/MasteringPipeline';

// We import shaders using Next.js raw loader or similar, 
// but for standard Next.js without special loaders, we can just inline them or fetch.
// Since we wrote them to disk, we'll assume a bundler setup that imports them as strings,
// but to be absolutely safe in a Next.js environment without raw-loader configured,
// we can read them via standard fetch or inline. Let's inline the shader content to avoid loader issues.

const latticeVert = `
uniform float uTime;
uniform float uProgress;
uniform float uInstability;

varying vec3 vPosition;
varying float vGlow;
varying float vNoise;

vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2  C = vec2(1.0/6.0, 1.0/3.0);
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute( permute( permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 0.142857142857;
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_ );
  vec4 x = x_ *ns.x + ns.yyyy;
  vec4 y = y_ *ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4( x.xy, y.xy );
  vec4 b1 = vec4( x.zw, y.zw );
  vec4 s0 = floor(b0)*2.0 + 1.0;
  vec4 s1 = floor(b1)*2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
  vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
  vec3 p0 = vec3(a0.xy,h.x);
  vec3 p1 = vec3(a0.zw,h.y);
  vec3 p2 = vec3(a1.xy,h.z);
  vec3 p3 = vec3(a1.zw,h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.5 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}

void main() {
  vPosition = position;
  float slowTime = uTime * 0.2;
  float noiseValue = snoise(position * 0.1 + slowTime);
  vNoise = noiseValue;
  
  float dist = length(position);
  float wave = sin(dist * 0.5 - uTime * 2.0);
  
  vec3 displacement = vec3(
    snoise(position * 0.2 + uTime) * wave,
    snoise(position * 0.2 + uTime + 10.0) * wave,
    snoise(position * 0.2 + uTime + 20.0) * wave
  );
  
  float collapse = pow(uProgress, 3.0) * uInstability;
  vec3 finalPosition = position + (displacement * collapse * 15.0);
  
  vec4 mvPosition = modelViewMatrix * vec4(finalPosition, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  
  float baseSize = 0.55;
  float fractureSize = abs(noiseValue) * 1.6 * uProgress;
  gl_PointSize = (baseSize + fractureSize) * (120.0 / -mvPosition.z);
  vGlow = smoothstep(0.5, 1.0, wave * noiseValue);
}
`;

const latticeFrag = `
uniform float uProgress;
uniform vec3 uColorStable;
uniform vec3 uColorUnstable;

varying vec3 vPosition;
varying float vGlow;
varying float vNoise;

void main() {
  vec2 uv = gl_PointCoord.xy - vec2(0.5);
  float dist = length(uv);
  if (dist > 0.5) discard;
  
  float alpha = smoothstep(0.5, 0.1, dist);
  float corruptionMask = smoothstep(0.7, 1.0, vNoise + uProgress);
  vec3 color = mix(uColorStable, uColorUnstable, corruptionMask);
  
  color += color * vGlow * 0.8;
  gl_FragColor = vec4(color, alpha * (0.12 + vGlow * 0.18) * (1.0 - uProgress * 0.35));
}
`;

export function LatticeField() {
  const pointsRef = useRef<THREE.Points>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const sceneProgress = useExperienceStore(s => s.sceneProgress);
  const activeScene = useExperienceStore(s => s.activeScene);
  
  // Scene index 1 is Threat Horizon
  const isThreatScene = activeScene === 1;

  // Generate mathematical lattice geometry
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const count = 2200;
    const positions = new Float32Array(count * 3);
    
    // Create a structured lattice instead of purely random
    let idx = 0;
    const size = 60;
    const spacing = 4;
    const halfSize = size / 2;
    
    for (let x = -halfSize; x < halfSize; x += spacing) {
      for (let y = -halfSize; y < halfSize; y += spacing) {
        for (let z = -halfSize; z < halfSize; z += spacing) {
          if (idx < count * 3) {
            // Add slight jitter to break pure grid look
            positions[idx] = x + (Math.random() - 0.5) * 0.5;
            positions[idx+1] = y + (Math.random() - 0.5) * 0.5;
            positions[idx+2] = z + (Math.random() - 0.5) * 0.5;
            idx += 3;
          }
        }
      }
    }
    
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 },
    uInstability: { value: 1.0 },
    uColorStable: { value: new THREE.Color(PALETTE.coldSteel) },
    uColorUnstable: { value: new THREE.Color(PALETTE.sovereignCyan) }
  }), []);

  useFrame(({ clock }) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.elapsedTime * FILM_MOTION_SCALE;
      
      // Update progress. If not in scene 1, hold it at 0 or 1 based on where we are.
      let targetProgress = 0;
      if (activeScene === 1) targetProgress = sceneProgress;
      else if (activeScene > 1) targetProgress = 1;
      
      // Smooth out progress updates slightly
      materialRef.current.uniforms.uProgress.value += (targetProgress - materialRef.current.uniforms.uProgress.value) * 0.1;
    }
    
    if (pointsRef.current) {
      // Slow constant rotation
      pointsRef.current.rotation.y = clock.elapsedTime * 0.03;
      pointsRef.current.rotation.x = clock.elapsedTime * 0.015;
    }
  });

  return (
    <points ref={pointsRef} geometry={geometry}>
      <shaderMaterial
        ref={materialRef}
        vertexShader={latticeVert}
        fragmentShader={latticeFrag}
        uniforms={uniforms}
        transparent={true}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
