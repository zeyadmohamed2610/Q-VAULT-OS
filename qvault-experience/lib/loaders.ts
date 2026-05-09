// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Asset Loader Pipeline
// Configures DRACO and KTX2 compression for high-fidelity assets.
// Provides suspense-aware loading and preloading strategies.
// ═══════════════════════════════════════════════════════════════

import { useGLTF } from '@react-three/drei';
import { DRACOLoader } from 'three-stdlib';
import { KTX2Loader } from 'three-stdlib';
import { useThree } from '@react-three/fiber';
import { useEffect } from 'react';
import * as THREE from 'three';

// ── Decoder Configuration ──
// These should point to local public folders in production.
const DRACO_DECODER_PATH = 'https://www.gstatic.com/draco/versioned/decoders/1.5.6/';
const BASIS_TRANSCODER_PATH = 'https://unpkg.com/three@0.160.0/examples/jsm/libs/basis/';

// ── Shared Loaders ──
let dracoLoader: DRACOLoader | null = null;
let ktx2Loader: KTX2Loader | null = null;

export function getDracoLoader() {
  if (!dracoLoader) {
    dracoLoader = new DRACOLoader();
    dracoLoader.setDecoderPath(DRACO_DECODER_PATH);
  }
  return dracoLoader;
}

export function getKTX2Loader(gl: THREE.WebGLRenderer) {
  if (!ktx2Loader) {
    ktx2Loader = new KTX2Loader();
    ktx2Loader.setTranscoderPath(BASIS_TRANSCODER_PATH);
    ktx2Loader.detectSupport(gl);
  }
  return ktx2Loader;
}

// ── Custom Hook for High-Fidelity Assets ──
export function usePremiumGLTF(path: string) {
  const gl = useThree((state) => state.gl);
  
  // Register loaders with Drei's internal useGLTF cache
  const gltf = useGLTF(path, true, true, (loader) => {
    loader.setDRACOLoader(getDracoLoader());
    loader.setKTX2Loader(getKTX2Loader(gl));
  });

  return gltf;
}

// Preload critical assets without blocking the main thread (lazy preloading)
export function preloadPremiumGLTF(path: string) {
  useGLTF.preload(path, true, true, (loader) => {
    loader.setDRACOLoader(getDracoLoader());
    // KTX2 needs WebGLRenderer context, which is tricky in pure preload.
    // For now, we rely on Draco for pure geometry preloading.
  });
}
