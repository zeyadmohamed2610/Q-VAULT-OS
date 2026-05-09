// ═══════════════════════════════════════════════════════════════
// ZERO KNOWLEDGE SHADERS
// High-performance shaders for Scene 5: Zero Knowledge
// ═══════════════════════════════════════════════════════════════

// 1. Entropy Distortion Shader
// Applied to the SecretCore to obscure the payload via refraction and noise
export const entropyDistortionVert = `
uniform float uTime;
uniform float uProgress;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;
varying vec3 vWorldPosition;

// Simplex 3D Noise for instability
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

float snoise(vec3 v){ 
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 = v - i + dot(i, C.xxx) ;
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + 1.0 * C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0 ); 
  vec4 p = permute( permute( permute( 
             i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
           + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 1.0/7.0;
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
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
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}

void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  
  // Progress drives the destruction/vaporization phase
  // Around progress 0.7 to 1.0, the core expands and breaks apart
  float vaporization = smoothstep(0.7, 1.0, uProgress);
  
  vec3 pos = position;
  float noise = snoise(pos * 2.0 + uTime);
  
  // Displace geometry during vaporization
  pos += normal * noise * vaporization * 5.0;
  
  vec4 worldPosition = modelMatrix * vec4(pos, 1.0);
  vWorldPosition = worldPosition.xyz;
  
  vec4 mvPosition = viewMatrix * worldPosition;
  vViewPosition = -mvPosition.xyz;
  gl_Position = projectionMatrix * mvPosition;
}
`;

export const entropyDistortionFrag = `
uniform float uTime;
uniform float uProgress;
uniform vec3 uColorBase;
uniform vec3 uColorVapor;

varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;
varying vec3 vWorldPosition;

// Simplex 3D Noise for fragment masking
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
float snoise(vec3 v){ 
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 = v - i + dot(i, C.xxx) ;
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + 1.0 * C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0 ); 
  vec4 p = permute( permute( permute( i.z + vec4(0.0, i1.z, i2.z, 1.0 )) + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 1.0/7.0;
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
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
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}

void main() {
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  
  // Extreme Fresnel to make it look like a silhouette/refraction
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
  
  // Mathematical noise patterns to obscure the secret
  float noise1 = snoise(vWorldPosition * 3.0 + uTime * 1.5);
  float noise2 = snoise(vWorldPosition * 10.0 - uTime * 3.0);
  float combinedNoise = (noise1 * 0.5 + 0.5) * (noise2 * 0.5 + 0.5);
  
  // Procedural Masking: Hide the core partially
  float mask = step(0.4, combinedNoise + fresnel);
  
  // Progress timeline
  // 0.0 - 0.3: Intake
  // 0.3 - 0.5: Fragmentation
  // 0.5 - 0.7: Proof Generation
  // 0.7 - 1.0: Vaporization
  
  float vaporization = smoothstep(0.7, 0.9, uProgress);
  float vaporDecay = 1.0 - smoothstep(0.85, 1.0, uProgress); // Fades completely to 0 at the end
  
  vec3 color = mix(uColorBase, uColorVapor, vaporization);
  
  // Add optical distortion and chromatic separation in the math
  float r = mask * fresnel * 0.34;
  float g = mask * fresnel * 0.72;
  float b = mask * fresnel * 0.92;
  vec3 finalColor = color * vec3(r, g, b);
  
  // Make it brighter during proof generation
  float proofPulse = smoothstep(0.5, 0.6, uProgress) * smoothstep(0.8, 0.6, uProgress);
  finalColor += uColorVapor * proofPulse * combinedNoise * 0.9;
  
  float alpha = mask * fresnel * vaporDecay;
  
  // Only render where alpha > 0
  if(alpha < 0.05) discard;
  
  gl_FragColor = vec4(finalColor, alpha);
}
`;


// 2. Proof Plasma Shader
// Applied to Instanced GPU Particles for Proof Trails and Vaporized Fragments
export const proofPlasmaVert = `
uniform float uTime;
uniform float uProgress;

attribute vec3 aOffset;
attribute vec3 aVelocity;
attribute float aLife;
attribute float aSize;

varying float vAlpha;
varying vec3 vColor;

// Curl noise for turbulent particle motion
// Re-using snoise for simplicity
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
float snoise(vec3 v){ 
  const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
  const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy) );
  vec3 x0 = v - i + dot(i, C.xxx) ;
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min( g.xyz, l.zxy );
  vec3 i2 = max( g.xyz, l.zxy );
  vec3 x1 = x0 - i1 + 1.0 * C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0 ); 
  vec4 p = permute( permute( permute( i.z + vec4(0.0, i1.z, i2.z, 1.0 )) + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
  float n_ = 1.0/7.0;
  vec3  ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
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
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
}

vec3 curlNoise(vec3 p) {
  float e = 0.1;
  vec3 dx = vec3(e, 0.0, 0.0);
  vec3 dy = vec3(0.0, e, 0.0);
  vec3 dz = vec3(0.0, 0.0, e);
  
  float x = snoise(p + dy) - snoise(p - dy) - snoise(p + dz) + snoise(p - dz);
  float y = snoise(p + dz) - snoise(p - dz) - snoise(p + dx) + snoise(p - dx);
  float z = snoise(p + dx) - snoise(p - dx) - snoise(p + dy) + snoise(p - dy);
  
  return vec3(x, y, z) / (2.0 * e);
}

void main() {
  // Particles are dormant until progress reaches ~0.4 (Fragmentation starts)
  float activation = smoothstep(0.4, 0.7, uProgress);
  
  // Vaporization explodes them outward at 0.7 to 1.0
  float explosion = smoothstep(0.7, 0.9, uProgress);
  
  // The local time of the particle based on global time and its life offset
  float localTime = uTime * 4.0 + aLife * 10.0;
  
  vec3 basePos = aOffset;
  
  // Turbulence
  vec3 turbulence = curlNoise(basePos * 0.5 + uTime * 0.1) * activation * 3.0;
  
  // Explosion velocity (outward from center)
  vec3 dir = normalize(basePos);
  vec3 explosionVelocity = dir * aVelocity * explosion * 15.0;
  
  // Swirling vortex effect
  vec3 vortex = vec3(-basePos.z, basePos.y, basePos.x) * activation * 5.0;
  
  // Final position
  vec3 finalPos = basePos + turbulence + explosionVelocity + vortex * uTime * 1.0;
  
  // Pulsing size
  float pulse = sin(localTime) * 0.5 + 0.5;
  float currentSize = aSize * (pulse + 0.5) * activation;
  
  // Shrink during explosion to mimic vaporization into nothingness
  currentSize *= (1.0 - smoothstep(0.8, 1.0, uProgress));
  
  vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  
  // Adjust point size based on distance
  gl_PointSize = currentSize * (150.0 / -mvPosition.z);
  
  // Determine color (Cyan -> White -> Deep Blue during explosion)
  vec3 colorGrey = vec3(0.60, 0.64, 0.68);
  vec3 colorWhite = vec3(0.50, 0.86, 1.0);
  vec3 colorDark = vec3(0.05, 0.05, 0.05);
  
  vColor = mix(colorGrey, colorWhite, pulse);
  vColor = mix(vColor, colorDark, explosion);
  
  // Fade out completely by the end
  vAlpha = activation * (1.0 - smoothstep(0.85, 1.0, uProgress));
}
`;

export const proofPlasmaFrag = `
varying float vAlpha;
varying vec3 vColor;

void main() {
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);
  if(dist > 0.5 || vAlpha < 0.01) discard;
  
  float glow = pow(1.0 - (dist * 2.0), 1.5);
  gl_FragColor = vec4(vColor * glow, vAlpha * glow * 0.42);
}
`;

// 3. Verification Pulse Ring Shader
export const verificationRingVert = `
uniform float uTime;
uniform float uProgress;

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

export const verificationRingFrag = `
uniform float uProgress;
varying vec2 vUv;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  // Verification triggers strictly between 0.6 and 0.8
  float intensity = smoothstep(0.6, 0.65, uProgress) * smoothstep(0.8, 0.75, uProgress);
  
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 2.0);
  
  // A clean, geometric scanning line moving across the ring
  float scanline = fract(vUv.x * 2.0 - uProgress * 10.0);
  float scanGlow = smoothstep(0.0, 0.1, scanline) * smoothstep(1.0, 0.9, scanline);
  
  vec3 finalColor = vec3(0.50, 0.86, 1.0) * (fresnel + scanGlow * 1.2) * intensity;

  gl_FragColor = vec4(finalColor, min(0.42, intensity * fresnel * 0.55));
}
`;
