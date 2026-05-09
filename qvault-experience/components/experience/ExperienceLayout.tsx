'use client';

import { Suspense, useCallback, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';
import { filmDirector } from '@/lib/FilmDirector';
import { SceneDispatcher } from './SceneDispatcher';
import { CameraRig } from '@/components/three/CameraRig';
import { GlobalLighting } from '@/components/three/GlobalLighting';
import { PostFX } from '@/components/three/PostFX';
import { ExecutiveOverlay } from '@/components/hud/ExecutiveOverlay';
import { IntroSequence } from './IntroSequence';
import { CinematicTitles } from './CinematicTitles';
import { EmotionalTransitionLayer } from './EmotionalTransitionLayer';
import { EndCredits } from './EndCredits';
import { WebGLFallback, isWebGLAvailable } from './WebGLFallback';
import { useAudioSystem } from '@/lib/useAudioSystem';

export default function ExperienceLayout() {
  const started = useRef(false);

  useAudioSystem();

  const handleIntroComplete = useCallback(() => {
    if (started.current) return;
    started.current = true;
    filmDirector.start();
  }, []);

  useEffect(() => () => filmDirector.stop(), []);

  useEffect(() => {
    const timer = setTimeout(handleIntroComplete, 3250);
    return () => clearTimeout(timer);
  }, [handleIntroComplete]);

  if (typeof window !== 'undefined' && !isWebGLAvailable()) {
    return <WebGLFallback reason="WEBGL_CONTEXT_REJECTED" />;
  }

  return (
    <div className="fixed inset-0 overflow-hidden bg-black cursor-none select-none">
      <IntroSequence onComplete={handleIntroComplete} />

      <div className="r3f-canvas">
        <Canvas
          gl={{
            antialias:           true,
            alpha:               false,
            powerPreference:     'high-performance',
            stencil:             false,
            depth:               true,
            toneMapping:         THREE.ACESFilmicToneMapping,
            toneMappingExposure: 1.0,
            outputColorSpace:    THREE.SRGBColorSpace,
          }}
          camera={{ fov: 40, near: 0.05, far: 200 }}
          dpr={[1, 1.5]}
          frameloop="always"
          shadows={false}
          onCreated={({ gl }) => {
            // Manually enable shadows with PCFShadowMap (not deprecated PCFSoftShadowMap)
            gl.shadowMap.enabled = true;
            gl.shadowMap.type    = THREE.PCFShadowMap;
          }}
        >
          <Suspense fallback={null}>
            <CameraRig />
            <GlobalLighting />
            <SceneDispatcher />
            <PostFX />
          </Suspense>
        </Canvas>
      </div>

      <ExecutiveOverlay />
      <EmotionalTransitionLayer />
      <CinematicTitles />
      <EndCredits />

      <div className="sr-only">
        Q-VAULT SOVEREIGN INFRASTRUCTURE FILM. AUTONOMOUS PLAYBACK MODE.
      </div>
    </div>
  );
}
