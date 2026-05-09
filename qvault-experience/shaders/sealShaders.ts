// ═══════════════════════════════════════════════════════════════
// SEAL SHADERS
// Procedural closure and final lighting collapse.
// ═══════════════════════════════════════════════════════════════

// 1. Aperture Closure (Massive mechanical plates sliding shut)
export const apertureVert = `
varying vec2 vUv;
varying vec3 vPosition;

void main() {
  vUv = uv;
  vPosition = position;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const apertureFrag = `
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;
varying vec3 vPosition;

void main() {
  // Polar coordinates for aperture
  vec2 st = vUv - vec2(0.5);
  float radius = length(st);
  float angle = atan(st.y, st.x);
  
  // Create 8 aperture blades
  float blades = 8.0;
  float bladeAngle = mod(angle, 6.28318 / blades);
  
  // The opening shrinks as progress goes from 0.0 to 0.8
  float openRadius = mix(0.5, 0.0, smoothstep(0.0, 0.8, uProgress));
  
  // Mechanical blade shape
  float shape = radius * cos(bladeAngle - 3.14159 / blades) - openRadius;
  
  float alpha = step(0.0, shape);
  
  // Metallic reflection fake
  float reflection = pow(1.0 - radius, 2.0) * alpha * 0.18;
  
  if (alpha < 0.5) discard;
  
  gl_FragColor = vec4(uColor * (0.35 + reflection), 0.48);
}
`;

// 2. Final Extinction Pulse (The last line of light before total darkness)
export const extinctionPulseVert = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const extinctionPulseFrag = `
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;

void main() {
  // Center line that gets thinner and thinner
  float centerDist = abs(vUv.y - 0.5);
  
  // Pulse starts thinning at 0.7, completely vanishes at 0.95
  float thickness = mix(0.022, 0.001, smoothstep(0.62, 0.95, uProgress));
  
  float glow = smoothstep(thickness, 0.0, centerDist);
  
  // Fades out completely by 0.98
  float alpha = glow * (1.0 - smoothstep(0.95, 0.98, uProgress));
  
  gl_FragColor = vec4(uColor * 0.78, alpha * 0.28);
}
`;

// 3. Q-VAULT Final Symbol Reveal
export const finalSymbolVert = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const finalSymbolFrag = `
uniform float uProgress;
uniform sampler2D tMap;

varying vec2 vUv;

void main() {
  float reveal = smoothstep(0.46, 0.82, uProgress);
  
  // Assuming a simple procedural Q symbol for now, or text texture
  // Draw a Q-like shape
  vec2 st = vUv - 0.5;
  float dist = length(st);
  
  float circle = smoothstep(0.4, 0.38, dist) - smoothstep(0.3, 0.28, dist);
  float tail = smoothstep(0.05, 0.0, abs(st.x - st.y - 0.2)) * step(0.1, st.x) * step(st.x, 0.4);
  
  float qShape = max(circle, tail);
  
  gl_FragColor = vec4(vec3(0.50, 0.86, 1.0), qShape * reveal * 0.52);
}
`;
