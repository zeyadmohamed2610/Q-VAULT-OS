// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Cinematic Camera Choreography
// Creates a heavy, physically damped camera with subtle mouse
// parallax. Bypasses standard OrbitControls for a cinematic feel.
// ═══════════════════════════════════════════════════════════════

import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

export function CinematicCamera({ progress }: { progress: number }) {
  const { camera, pointer } = useThree();
  
  // Track smoothed pointer for parallax
  const targetPointer = useRef(new THREE.Vector2());
  const currentPointer = useRef(new THREE.Vector2());
  
  // Track camera base position
  const basePos = useRef(new THREE.Vector3());

  useFrame((state, delta) => {
    // 1. Calculate base cinematic path based on scroll progress
    // Sequence: 
    // - Early progress: Starts off-center, low, looking up (hero reveal).
    // - Mid progress: Slow, deliberate orbit around the object.
    // - Late progress: Pull back and up, looking down as object descends to Trust Stack.
    
    // Easing function for progress
    const t = Math.max(0, Math.min(1, progress));
    const smoothT = t * t * (3 - 2 * t);
    
    // Orbit angles
    const orbitAngle = smoothT * Math.PI * 0.75; // 135 degree orbit
    const radius = 18 - (smoothT * 5); // Start far, get closer
    
    // Base position
    basePos.current.x = Math.sin(orbitAngle) * radius;
    basePos.current.z = Math.cos(orbitAngle) * radius;
    basePos.current.y = -2 + (smoothT * 6); // Rise up
    
    // 2. Mouse Parallax Integration (Subtle & Restrained)
    targetPointer.current.x = pointer.x * 2.0;
    targetPointer.current.y = pointer.y * 2.0;
    
    // Damped interpolation for heavy, physical feeling
    currentPointer.current.lerp(targetPointer.current, delta * 3.0);
    
    // Apply parallax to base position
    const finalX = basePos.current.x + currentPointer.current.x;
    const finalY = basePos.current.y + currentPointer.current.y;
    const finalZ = basePos.current.z;
    
    // Interpolate camera to final position smoothly
    camera.position.lerp(new THREE.Vector3(finalX, finalY, finalZ), delta * 2.0);
    
    // 3. Focal Targeting
    // The camera should always look at the object center, with slight drag
    const lookAtTarget = new THREE.Vector3(0, 0, 0);
    // Add slight offset based on mouse to make the composition feel alive but stable
    lookAtTarget.x -= currentPointer.current.x * 0.5;
    lookAtTarget.y -= currentPointer.current.y * 0.5;
    
    // We cannot easily lerp lookAt without a quaternions, so we calculate target quaternion
    const currentQuat = camera.quaternion.clone();
    camera.lookAt(lookAtTarget);
    const targetQuat = camera.quaternion.clone();
    
    // Restore and slerp
    camera.quaternion.copy(currentQuat);
    camera.quaternion.slerp(targetQuat, delta * 4.0);
  });

  return null;
}
