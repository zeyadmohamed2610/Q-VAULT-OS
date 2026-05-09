// ═══════════════════════════════════════════════════════════════
// PROVISIONING SHADERS
// High-performance shaders for Scene 6: Provisioning
// ═══════════════════════════════════════════════════════════════

// 1. Optical Scan Sweep (Used on a plane or cylinder passing over the hardware)
export const opticalScanVert = `
varying vec2 vUv;
varying vec3 vWorldPosition;

void main() {
  vUv = uv;
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const opticalScanFrag = `
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;
varying vec3 vWorldPosition;

void main() {
  // A scanline that moves down the hardware based on progress (0.2 to 0.5)
  // Mapping progress [0.2, 0.5] to Y position [2.0, -2.0]
  float scanY = 2.0 - (uProgress - 0.2) * (4.0 / 0.3);
  
  // Distance from current scan Y
  float dist = abs(vWorldPosition.y - scanY);
  
  // Sharp line with soft tail
  float glow = smoothstep(0.1, 0.0, dist) + smoothstep(0.5, 0.0, vWorldPosition.y - scanY) * 0.3;
  
  // Only active during scan phase
  float activeMask = smoothstep(0.2, 0.25, uProgress) * smoothstep(0.5, 0.45, uProgress);
  
  gl_FragColor = vec4(uColor * glow * 2.0, glow * activeMask);
}
`;

// 2. Cryptographic Seal (Used for glowing traces on the hardware or a wrapping band)
export const sealPropVert = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const sealPropFrag = `
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;

void main() {
  // Sealing happens between 0.5 and 0.7
  float localProg = clamp((uProgress - 0.5) * 5.0, 0.0, 1.0);
  
  // Seal wrapping around horizontally
  float fill = step(vUv.x, localProg);
  
  // Pulsing energy edge
  float edge = smoothstep(localProg + 0.05, localProg, vUv.x) * smoothstep(localProg - 0.05, localProg, vUv.x);
  
  float glow = (fill * 0.3 + edge * 2.0) * localProg;
  
  gl_FragColor = vec4(uColor * glow, fill * 0.8 + edge);
}
`;

// 3. Identity Injection Beam (Volumetric shaft coming from above)
export const injectionBeamVert = `
varying vec2 vUv;
varying float vDepth;
void main() {
  vUv = uv;
  vDepth = position.y;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const injectionBeamFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;
varying float vDepth;

void main() {
  // Injection phase 0.3 to 0.6
  float activeMask = smoothstep(0.3, 0.35, uProgress) * smoothstep(0.6, 0.55, uProgress);
  
  // Horizontal fade (cylinder)
  float horiz = smoothstep(0.0, 0.2, vUv.x) * smoothstep(1.0, 0.8, vUv.x);
  
  // Vertical data scrolling
  float data = fract(vUv.y * 10.0 - uTime * 3.0);
  float dataGlow = smoothstep(0.0, 0.1, data) * smoothstep(1.0, 0.9, data);
  
  // Vertical fade
  float vertFade = smoothstep(-5.0, 5.0, vDepth);
  
  float intensity = horiz * dataGlow * vertFade * activeMask;
  
  gl_FragColor = vec4(uColor * intensity * 2.0, intensity * 0.8);
}
`;

// 4. Attestation Wave (Expanding sphere from the hardware)
export const attestationWaveVert = `
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

export const attestationWaveFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  // Attestation happens between 0.7 and 0.9
  float localProg = clamp((uProgress - 0.7) * 5.0, 0.0, 1.0);
  
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 1.5);
  
  // Expanding ring effect mapped to UV y (assuming sphere)
  float ring = smoothstep(localProg - 0.1, localProg, 1.0 - vUv.y) * smoothstep(localProg + 0.1, localProg, 1.0 - vUv.y);
  
  float intensity = ring * fresnel * (1.0 - localProg); // Fades out as it expands
  
  gl_FragColor = vec4(uColor * intensity * 3.0, intensity);
}
`;
