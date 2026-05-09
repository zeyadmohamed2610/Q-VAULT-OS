// ═══════════════════════════════════════════════════════════════
// OS SURFACE SHADERS
// High-performance shaders for Scene 7: OS Surface
// ═══════════════════════════════════════════════════════════════

// 1. Tactical Glass Panel (Used for floating windows)
export const glassPanelVert = `
varying vec2 vUv;
varying vec3 vViewPosition;
varying vec3 vNormal;

void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  vViewPosition = -mvPosition.xyz;
  gl_Position = projectionMatrix * mvPosition;
}
`;

export const glassPanelFrag = `
uniform float uProgress;
uniform vec3 uColor;
uniform float uOpacity;

varying vec2 vUv;
varying vec3 vViewPosition;
varying vec3 vNormal;

void main() {
  // Edge highlight (Fresnel)
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
  
  // Border rendering
  float borderX = step(vUv.x, 0.02) + step(0.98, vUv.x);
  float borderY = step(vUv.y, 0.02) + step(0.98, vUv.y);
  float border = max(borderX, borderY);
  
  // Subtle internal grid
  float grid = step(fract(vUv.x * 20.0), 0.05) * step(fract(vUv.y * 20.0), 0.05) * 0.1;
  
  // Base glass color + border + fresnel edge
  float intensity = grid + border * 0.5 + fresnel * 0.8;
  
  // Fade in based on progress
  float alpha = uOpacity * smoothstep(0.0, 0.2, uProgress) * (0.1 + intensity);
  
  gl_FragColor = vec4(uColor, alpha);
}
`;

// 2. Terminal Stream (Scrolling vertical data)
export const terminalStreamVert = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

export const terminalStreamFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColor;

varying vec2 vUv;

float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
}

void main() {
  // Create columns
  float cols = 40.0;
  float colIndex = floor(vUv.x * cols);
  
  // Column speed and offset
  float speed = random(vec2(colIndex, 1.0)) * 8.0 + 4.0;
  float offset = random(vec2(colIndex, 2.0));
  
  // Moving blocks
  float yPos = fract(vUv.y - uTime * speed + offset);
  
  // Create "text" blocks
  float block = step(yPos, 0.1) * step(0.0, yPos);
  
  // Add some horizontal gaps to simulate characters
  float chars = step(fract(vUv.y * 100.0), 0.7);
  
  // Fade top and bottom
  float fade = smoothstep(0.0, 0.1, vUv.y) * smoothstep(1.0, 0.9, vUv.y);
  
  float intensity = block * chars * fade;
  
  // Fade in based on progress
  float alpha = intensity * smoothstep(0.1, 0.3, uProgress) * 0.8;
  
  gl_FragColor = vec4(uColor, alpha);
}
`;

// 3. Grid Background (Brutalist cyber command environment)
export const environmentGridVert = `
varying vec3 vWorldPosition;
void main() {
  vec4 worldPosition = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPosition.xyz;
  gl_Position = projectionMatrix * viewMatrix * worldPosition;
}
`;

export const environmentGridFrag = `
uniform float uProgress;
uniform vec3 uColor;

varying vec3 vWorldPosition;

void main() {
  // 3D Grid
  float gridX = step(fract(vWorldPosition.x * 2.0), 0.05);
  float gridY = step(fract(vWorldPosition.y * 2.0), 0.05);
  float gridZ = step(fract(vWorldPosition.z * 2.0), 0.05);
  
  float grid = max(gridX, max(gridY, gridZ));
  
  // Distance fade (fog)
  float dist = length(vWorldPosition);
  float fade = smoothstep(50.0, 10.0, dist);
  
  // Ambient glow
  float intensity = grid * fade * 0.1;
  
  gl_FragColor = vec4(uColor, intensity * smoothstep(0.0, 0.2, uProgress));
}
`;
