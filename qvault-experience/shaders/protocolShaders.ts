// ═══════════════════════════════════════════════════════════════
// PROTOCOL SHADERS
// High-performance shaders for Scene 4: Protocol Lab
// ═══════════════════════════════════════════════════════════════

// 1. Packet Trail Shader
// Used for InstancedBufferGeometry to create moving packets along tubes
export const packetTrailVert = `
uniform float uTime;
uniform float uProgress;

attribute float aOffset;
attribute float aSpeed;
attribute float aSize;
attribute vec3 aCurvePos;
attribute vec3 aCurveTangent;

varying float vAlpha;
varying vec3 vColor;

void main() {
  // Move packet along its 1D timeline [0, 1]
  float timeOffset = uTime * aSpeed + aOffset;
  float t = fract(timeOffset);
  
  // Tie speed to scroll progress (speed increases with progress)
  t = fract(t + uProgress * aSpeed * 10.0);

  // Simple position offset based on tangent (tubular displacement)
  // Real curve position is passed via aCurvePos, but for instanced lines
  // we would ideally evaluate the spline in JS and pass positions, 
  // or evaluate a bezier in GLSL. 
  // Assuming aCurvePos is the base position for this instance.
  
  // Size attenuation and pulsing
  float pulse = sin(t * 3.14159) * aSize;
  
  vec3 finalPos = position * pulse + aCurvePos;
  
  vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  
  // Fade at start/end of the trail
  vAlpha = smoothstep(0.0, 0.2, t) * smoothstep(1.0, 0.8, t);
  vColor = mix(vec3(0.60, 0.64, 0.68), vec3(0.50, 0.86, 1.0), pulse * 0.22);
}
`;

export const packetTrailFrag = `
varying float vAlpha;
varying vec3 vColor;

void main() {
  // Soft circle for packet
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);
  if(dist > 0.5) discard;
  
  float glow = 1.0 - (dist * 2.0);
  gl_FragColor = vec4(vColor * glow, vAlpha * glow * 0.45);
}
`;

// 2. Encryption Field Shader
// Applied to the central core cylinder
export const encryptionFieldVert = `
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

export const encryptionFieldFrag = `
uniform float uTime;
uniform float uStage; // Protocol stage 0.0 to 1.0
uniform vec3 uColorStable;
uniform vec3 uColorActive;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  // Hexagonal interference pattern
  vec2 hexUv = vUv * vec2(20.0, 10.0);
  float hexY = mod(hexUv.y, 1.0);
  float hexLines = step(0.9, hexY) + step(0.9, mod(hexUv.x + (hexY > 0.5 ? 0.5 : 0.0), 1.0));
  
  // Fresnel
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
  
  // Energy waves scrolling down
  float wave = fract(vUv.y * 5.0 - uTime * 4.0);
  float scanline = smoothstep(0.0, 0.1, wave) * smoothstep(1.0, 0.9, wave);
  
  // Color mixes as protocol stages advance
  vec3 baseColor = mix(uColorStable, uColorActive, uStage);
  
  // Combine effects
  float intensity = scanline * 0.28 + hexLines * 0.12 + fresnel * 0.9;
  
  // Pulse heavily when a stage completes (uStage jumps)
  float stagePulse = sin(uStage * 3.14159 * 6.0) * 0.5 + 0.5;
  
  vec3 finalColor = baseColor * intensity * (0.8 + stagePulse * 0.9);

  gl_FragColor = vec4(finalColor, min(0.72, intensity * 0.65 + fresnel * 0.45));
}
`;
