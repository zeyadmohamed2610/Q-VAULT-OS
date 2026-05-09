// ═══════════════════════════════════════════════════════════════
// PACKET STREAMS
// GPU Particle System using InstancedMesh for high performance
// data flow visualization. Avoids useFrame allocations.
// ═══════════════════════════════════════════════════════════════

import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { packetTrailVert, packetTrailFrag } from '@/shaders/protocolShaders';
import { FILM_MOTION_SCALE } from '@/lib/MasteringPipeline';

interface PacketStreamsProps {
  progress: number;
}

export function PacketStreams({ progress }: PacketStreamsProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  const COUNT = 320;

  // We use ShaderMaterial for instances instead of standard points
  // to allow complex sizing and tubular flow without geometry updates.
  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uProgress: { value: 0 }
  }), []);

  const geometry = useMemo(() => {
    // Basic quad for the packet
    const geo = new THREE.PlaneGeometry(0.1, 0.1);
    
    // Instance attributes
    const offsets = new Float32Array(COUNT);
    const speeds = new Float32Array(COUNT);
    const sizes = new Float32Array(COUNT);
    const curvePos = new Float32Array(COUNT * 3);
    
    for (let i = 0; i < COUNT; i++) {
      offsets[i] = Math.random();
      speeds[i] = 0.5 + Math.random() * 1.5;
      sizes[i] = 0.18 + Math.random() * 0.55;
      
      // Randomly assign to one of 6 "tubes" feeding into the core
      const tubeIndex = i % 6;
      const angle = (tubeIndex * Math.PI * 2) / 6;
      const radius = 4.6 + Math.random() * 1.2;
      const height = -7 + Math.random() * 14;
      
      curvePos[i*3] = Math.cos(angle) * radius;
      curvePos[i*3+1] = height;
      curvePos[i*3+2] = Math.sin(angle) * radius;
    }
    
    geo.setAttribute('aOffset', new THREE.InstancedBufferAttribute(offsets, 1));
    geo.setAttribute('aSpeed', new THREE.InstancedBufferAttribute(speeds, 1));
    geo.setAttribute('aSize', new THREE.InstancedBufferAttribute(sizes, 1));
    geo.setAttribute('aCurvePos', new THREE.InstancedBufferAttribute(curvePos, 3));
    
    return geo;
  }, []);

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = state.clock.elapsedTime * FILM_MOTION_SCALE;
      // Smooth progress update for particle speed injection
      materialRef.current.uniforms.uProgress.value += (progress - materialRef.current.uniforms.uProgress.value) * 0.1;
    }
    
    // Rotate the entire stream setup slowly
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.15;
    }
  });

  return (
    <instancedMesh ref={meshRef} args={[geometry, undefined, COUNT]}>
      <shaderMaterial
        ref={materialRef}
        vertexShader={packetTrailVert}
        fragmentShader={packetTrailFrag}
        uniforms={uniforms}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        side={THREE.DoubleSide}
      />
    </instancedMesh>
  );
}
