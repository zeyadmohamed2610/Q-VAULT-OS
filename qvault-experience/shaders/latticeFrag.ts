export const latticeFrag = `
uniform float uInstability;

varying vec2 vUv;
varying vec3 vPosition;
varying float vProgress;

void main() {
  // Soft circle for point rendering
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);
  if(dist > 0.5) discard;
  
  float alpha = 1.0 - (dist * 2.0);
  
  // Cyan (stable) to Crimson (corrupted)
  vec3 colorStable = vec3(0.0, 0.9, 1.0);
  vec3 colorCorrupted = vec3(1.0, 0.2, 0.4);
  
  // Mix based on instability and noise
  float corruptionFactor = min(1.0, uInstability * 1.5 * vProgress);
  vec3 finalColor = mix(colorStable, colorCorrupted, corruptionFactor);
  
  gl_FragColor = vec4(finalColor, alpha * (0.8 - uInstability * 0.3));
}
`;
