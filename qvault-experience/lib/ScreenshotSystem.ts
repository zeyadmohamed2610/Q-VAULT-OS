// ═══════════════════════════════════════════════════════════════
// SCREENSHOT SYSTEM
// Cinematic capture with exposure lock and frame stabilization.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect, useRef, useState } from 'react';

interface ScreenshotState {
  isCapturing: boolean;
  exposureLocked: boolean;
  frameStabilized: boolean;
}

export function useScreenshotSystem(canvasRef?: React.RefObject<HTMLCanvasElement>) {
  const [state, setState] = useState<ScreenshotState>({
    isCapturing: false,
    exposureLocked: false,
    frameStabilized: false,
  });

  const captureFrame = () => {
    // Find the R3F canvas
    const canvas = document.querySelector('canvas') as HTMLCanvasElement | null;
    if (!canvas) return;

    setState(s => ({ ...s, isCapturing: true, frameStabilized: true }));

    // Wait 2 frames for stabilization
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        try {
          const dataUrl = canvas.toDataURL('image/png', 1.0);
          const a = document.createElement('a');
          a.href = dataUrl;
          a.download = `qvault-frame-${Date.now()}.png`;
          a.click();
        } catch (e) {
          console.warn('Screenshot capture failed (CORS or context):', e);
        }
        setState(s => ({ ...s, isCapturing: false, frameStabilized: false }));
      });
    });
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // P = screenshot, L = toggle exposure lock
      if (e.key === 'p' || e.key === 'P') {
        captureFrame();
      }
      if (e.key === 'l' || e.key === 'L') {
        setState(s => ({ ...s, exposureLocked: !s.exposureLocked }));
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return { ...state, captureFrame };
}
