// ═══════════════════════════════════════════════════════════════
// ROADMAP SHADERS
// Procedural space mapping for Scene 11: Roadmap.
// ═══════════════════════════════════════════════════════════════

// 1. Sovereign Paths (Glowing energy lines connecting milestones)
export const pathVert = `
uniform float uTime;
uniform float uProgress;
varying float vProgress;

void main() {
  vProgress = position.z / -62.0;
  
  // Wave motion
  vec3 pos = position;
  pos.x += sin(pos.z * 0.1 + uTime * 3.0) * 0.8;
  pos.y += cos(pos.z * 0.1 + uTime * 2.5) * 0.8;
  
  gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
`;

export const pathFrag = `
uniform float uProgress;
uniform vec3 uColor;
varying float vProgress;

void main() {
  // Path reveals from foreground to horizon as progress increases.
  float reveal = 1.0 - smoothstep(uProgress + 0.04, uProgress + 0.24, vProgress);
  
  // High-tech pulse
  float pulse = fract(vProgress * 10.0 - uProgress * 5.0);
  float intensity = reveal * (0.26 + smoothstep(0.0, 0.2, pulse) * smoothstep(1.0, 0.2, pulse) * 0.52);

  gl_FragColor = vec4(uColor * 0.84, intensity * 0.72);
}
`;

// 2. Milestone Glow (Subtle volumetric glow around points of interest)
export const milestoneVert = `
varying vec2 vUv;
varying vec3 vViewPosition;

void main() {
  vUv = uv;
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  vViewPosition = -mvPosition.xyz;
  gl_Position = projectionMatrix * mvPosition;
}
`;

export const milestoneFrag = `
uniform float uProgress;
uniform float uRevealTrigger;
uniform vec3 uColor;

varying vec2 vUv;
varying vec3 vViewPosition;

void main() {
  // Only reveal when camera progress reaches this milestone
  float activeMask = smoothstep(uRevealTrigger - 0.2, uRevealTrigger, uProgress);
  
  // Soft spherical gradient
  float dist = length(vUv - vec2(0.5)) * 2.0;
  float glow = smoothstep(1.0, 0.0, dist);
  
  // Fresnel
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(vec3(0,0,1), viewDir), 0.0), 3.0); // Fake normal
  
  float intensity = glow * activeMask * 0.32;
  
  gl_FragColor = vec4(uColor, intensity);
}
`;
