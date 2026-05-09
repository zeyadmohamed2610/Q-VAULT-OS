// ═══════════════════════════════════════════════════════════════
// PERFORMANCE OVERLAY
// Classified HUD showing active system optimizations.
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState } from 'react';

export function PerformanceOverlay() {
  const [fps, setFps] = useState(60);
  const [dpr, setDpr] = useState(window.devicePixelRatio);

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();

    const loop = () => {
      frameCount++;
      const now = performance.now();
      if (now - lastTime >= 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = now;
      }
      requestAnimationFrame(loop);
    };

    const handleId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(handleId);
  }, []);

  // Use a subtle top-right telemetry block
  return (
    <div className="absolute top-4 right-4 pointer-events-none z-50 text-[10px] font-mono opacity-30 text-white flex flex-col items-end">
      <div>SYS_GOV: ACTIVE</div>
      <div>FPS: {fps}</div>
      <div>DPR: {dpr.toFixed(1)}</div>
      {fps < 30 && <div className="text-[#ff0044] animate-pulse">THERMAL LIMIT DEGRADATION</div>}
    </div>
  );
}
