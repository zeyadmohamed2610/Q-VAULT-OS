// ═══════════════════════════════════════════════════════════════
// THREAT MATRIX SHADERS
// High-performance shaders for Scene 9: Threat Matrix
// ═══════════════════════════════════════════════════════════════

// 1. Hostile Stream Distortion (Attack Vectors)
export const attackVectorVert = `
uniform float uTime;
uniform float uProgress;

attribute float aOffset;
attribute vec3 aTrajectory;

varying float vAlpha;

void main() {
  // Movement along trajectory based on time and individual offset
  float localTime = fract(uTime * 2.0 + aOffset);
  
  // Attack vectors are active mainly between progress 0.1 and 0.8
  float activeMask = smoothstep(0.0, 0.2, uProgress) * smoothstep(0.9, 0.7, uProgress);
  
  // Position moves towards the center (0,0,0)
  vec3 currentPos = position + aTrajectory * (1.0 - localTime) * 20.0;
  
  // They start disappearing as they get intercepted (progress > 0.5)
  float survivalChances = step(localTime, 1.0 - (uProgress - 0.5) * 2.0);
  
  vAlpha = activeMask * survivalChances * (1.0 - localTime);
  
  vec4 mvPosition = modelViewMatrix * vec4(currentPos, 1.0);
  gl_PointSize = 4.0 * (1.0 / -mvPosition.z);
  gl_Position = projectionMatrix * mvPosition;
}
`;

export const attackVectorFrag = `
uniform vec3 uColor;
varying float vAlpha;

void main() {
  // Soft particle
  float dist = length(gl_PointCoord - vec2(0.5));
  float alpha = smoothstep(0.5, 0.1, dist) * vAlpha;
  
  if (alpha < 0.01) discard;
  
  gl_FragColor = vec4(uColor, alpha);
}
`;

// 2. Interception Pulse Rings (Defensive barriers)
export const interceptionPulseVert = `
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  vViewPosition = -mvPosition.xyz;
  gl_Position = projectionMatrix * mvPosition;
}
`;

export const interceptionPulseFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  // Defense activates at progress 0.4
  float activeMask = smoothstep(0.3, 0.5, uProgress);
  
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 2.0);
  
  // Expanding pulses
  float pulse = fract(vUv.y * 5.0 - uTime * 7.0);
  float ring = smoothstep(0.0, 0.1, pulse) * smoothstep(0.5, 0.1, pulse);
  
  float intensity = ring * fresnel * activeMask;
  
  gl_FragColor = vec4(uColor * intensity * 2.0, intensity * 0.8);
}
`;

// 3. Containment Field (Final shield stabilizing the anomaly)
export const containmentFieldVert = `
varying vec3 vWorldPosition;
void main() {
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const containmentFieldFrag = `
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
  // Containment wraps up between 0.7 and 1.0
  float activeMask = smoothstep(0.6, 0.9, uProgress);
  
  // Hex-like/Energy pattern using noise
  float n = noise(vWorldPosition * 2.0);
  float pattern = smoothstep(0.4, 0.6, n) * smoothstep(0.8, 0.6, n);
  
  float intensity = pattern * activeMask;
  
  gl_FragColor = vec4(uColor, intensity * 0.5);
}
`;
