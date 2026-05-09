// ═══════════════════════════════════════════════════════════════
// LIFECYCLE SHADERS
// High-performance shaders for Scene 10: Hardware Lifecycle
// ═══════════════════════════════════════════════════════════════

// 1. Temporal Energy Rings (Slow moving orbital synchronization rings)
export const temporalRingVert = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const temporalRingFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;

void main() {
  // A slow, persistent scanning energy along the ring
  float scan = fract(vUv.x * 3.0 - uTime * 0.5);
  float glow = smoothstep(0.0, 0.5, scan) * smoothstep(1.0, 0.5, scan);
  
  // Edge fade
  float edge = smoothstep(0.0, 0.2, vUv.y) * smoothstep(1.0, 0.8, vUv.y);
  
  float intensity = glow * edge;
  
  // Fade in based on progress
  float alpha = intensity * smoothstep(0.0, 0.2, uProgress);
  
  gl_FragColor = vec4(uColor * 0.72, alpha * 0.28);
}
`;

// 2. Cryogenic Haze (Volumetric preservation fog)
export const cryogenicHazeVert = `
varying vec3 vWorldPosition;
void main() {
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const cryogenicHazeFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec3 vWorldPosition;

// Simple 3D noise
float hash(vec3 p) {
  p = fract(p * 0.3183099 + .1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise(in vec3 x) {
  vec3 p = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash(p + vec3(0,0,0)), hash(p + vec3(1,0,0)), f.x),
                 mix(hash(p + vec3(0,1,0)), hash(p + vec3(1,1,0)), f.x), f.y),
             mix(mix(hash(p + vec3(0,0,1)), hash(p + vec3(1,0,1)), f.x),
                 mix(hash(p + vec3(0,1,1)), hash(p + vec3(1,1,1)), f.x), f.y), f.z);
}

void main() {
  // Slow swirling cold mist
  float n = noise(vWorldPosition * 0.5 + vec3(0.0, uTime * 0.1, uTime * 0.05));
  
  // Fade out at edges (sphere mask)
  float dist = length(vWorldPosition);
  float mask = smoothstep(20.0, 5.0, dist);
  
  float intensity = n * mask * 0.12;
  
  // Progress fade
  float alpha = intensity * smoothstep(0.1, 0.3, uProgress);
  
  gl_FragColor = vec4(uColor, alpha);
}
`;

// 3. Continuity Scan Field (A subtle vertical sweep indicating preservation checks)
export const continuityScanVert = `
varying vec3 vWorldPosition;
void main() {
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const continuityScanFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec3 vWorldPosition;

void main() {
  // A slow, persistent vertical scan
  float scanY = fract(uTime * 0.15) * 40.0 - 20.0;
  
  float dist = abs(vWorldPosition.y - scanY);
  float glow = smoothstep(2.0, 0.0, dist);
  
  // Hex grid overlay to make it look like a structural scan
  float hex = step(fract(vWorldPosition.x * 2.0 + vWorldPosition.y), 0.1) * 
              step(fract(vWorldPosition.z * 2.0 + vWorldPosition.y), 0.1);
  
  float intensity = glow * (0.18 + hex * 0.45) * 0.22;
  
  float alpha = intensity * smoothstep(0.0, 0.1, uProgress);
  
  gl_FragColor = vec4(uColor * 0.7, alpha * 0.32);
}
`;
