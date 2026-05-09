export const pulseFrag = `
uniform float uTime;
uniform float uProgress; 
uniform vec3 uColor;
uniform float uPulseSpeed;

varying vec2 vUv;
varying vec3 vWorldPosition;
varying vec3 vNormal;

void main() {
  // Vertical pulse traveling upward
  float timeOffset = uTime * uPulseSpeed;
  
  // Base coordinate for upward flow
  float flowCoord = vWorldPosition.y * 0.5 - timeOffset;
  
  // Create main trust pulse
  float pulse = fract(flowCoord);
  float pulseGlow = smoothstep(0.0, 0.1, pulse) * smoothstep(1.0, 0.4, pulse);
  
  // Add micro-data packets (fast moving thin lines)
  float packets = step(0.95, fract(vWorldPosition.y * 5.0 - timeOffset * 6.0)) * 0.5;
  
  // Add edge fresnel to make it look cylindrical and physical
  float fresnel = pow(1.0 - max(dot(vNormal, vec3(0.0, 0.0, 1.0)), 0.0), 2.0);
  
  // Fade bounds (Top and bottom of the stack)
  float boundsFade = smoothstep(-12.0, -9.0, vWorldPosition.y) * smoothstep(12.0, 9.0, vWorldPosition.y);
  
  float totalIntensity = (pulseGlow + packets) * (1.0 + fresnel * 2.0);
  
  vec3 finalColor = uColor * totalIntensity;
  float alpha = totalIntensity * boundsFade * 0.8;
  
  // React to scroll progress (dim when off-scene)
  alpha *= smoothstep(0.0, 0.2, uProgress) * smoothstep(1.0, 0.8, uProgress);

  gl_FragColor = vec4(finalColor, alpha);
}
`;
