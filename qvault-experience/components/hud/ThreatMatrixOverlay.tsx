// ═══════════════════════════════════════════════════════════════
// THREAT MATRIX OVERLAY HUD (SCENE 9)
// Real-time post-quantum attack interception UI.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function ThreatMatrixOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 9;

  const [threatCounters, setThreatCounters] = useState(0);

  useEffect(() => {
    if (!isVisible) return;
    const interval = setInterval(() => {
      // Threat increases rapidly early on, then stops as containment kicks in
      if (progress < 0.6) {
        setThreatCounters(prev => prev + Math.floor(Math.random() * 50));
      }
    }, 100);
    return () => clearInterval(interval);
  }, [isVisible, progress]);

  if (!isVisible) return null;

  const isDetecting = progress < 0.4;
  const isIntercepting = progress >= 0.4 && progress < 0.7;
  const isContained = progress >= 0.7;

  return (
    <div className={`absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen font-mono ${isContained ? 'text-[#00e6ff]' : 'text-[#ff0044]'}`}>
      
      {/* Top Bar: Attack Status */}
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <div className={`text-xs tracking-[0.3em] opacity-60 ${isContained ? 'text-white' : 'text-[#ff0044] animate-pulse'}`}>
            {isContained ? 'ANOMALY NEUTRALIZED' : 'QUANTUM ANOMALY DETECTED'}
          </div>
          <div className="text-2xl tracking-widest font-bold">
            {isDetecting ? "ACTIVE QUANTUM ATTACK" :
             isIntercepting ? "INTERCEPTION IN PROGRESS" :
             "ENCRYPTION FAILURE CONTAINED"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest opacity-50 text-white">DEFENSE SYSTEM</div>
          <div className="text-sm tracking-widest">
            {isContained ? 'ZERO TRUST ENFORCEMENT' : 'ML-KEM DEFENSE ACTIVE'}
          </div>
        </div>
      </div>

      {/* Center Left: Threat Telemetry */}
      <div className="absolute top-1/2 left-12 -translate-y-1/2 flex flex-col gap-6">
        <div>
          <div className={`text-[10px] opacity-50 tracking-widest border-b pb-1 mb-2 ${isContained ? 'border-[#00e6ff]/20' : 'border-[#ff0044]/20'}`}>HOSTILE INTRUSION STREAMS</div>
          <div className="text-3xl font-bold">{threatCounters.toLocaleString()}</div>
        </div>
        <div>
          <div className={`text-[10px] opacity-50 tracking-widest border-b pb-1 mb-2 ${isContained ? 'border-[#00e6ff]/20' : 'border-[#ff0044]/20'}`}>ATTACK ENTROPY</div>
          <div className="text-xl">{(isContained ? 0 : Math.random() * 100).toFixed(2)} TB/s</div>
        </div>
      </div>

      {/* Center Right: Containment Progress */}
      <div className="absolute top-1/2 right-12 -translate-y-1/2 flex flex-col gap-6 text-right">
        <div>
          <div className={`text-[10px] opacity-50 tracking-widest border-b pb-1 mb-2 ${isContained ? 'border-[#00e6ff]/20' : 'border-[#ff0044]/20'}`}>CONTAINMENT INTEGRITY</div>
          <div className="text-3xl font-bold">{Math.min(100, progress * 140).toFixed(1)}%</div>
        </div>
        <div>
          <div className={`text-[10px] opacity-50 tracking-widest border-b pb-1 mb-2 ${isContained ? 'border-[#00e6ff]/20' : 'border-[#ff0044]/20'}`}>RESPONSE LATENCY</div>
          <div className="text-xl">0.001 ms</div>
        </div>
      </div>

      {/* Bottom Bar: Vector Analysis */}
      <div className="flex justify-between items-end border-t border-white/20 pt-4">
        <div className="flex gap-12">
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50 text-white">THREAT VECTOR ANALYSIS</div>
            <div className="text-sm">SHOR'S ALGORITHM VARIANT</div>
          </div>
        </div>
        
        <div className="text-[10px] tracking-widest opacity-50 max-w-xs text-right text-white">
          SYSTEM STABILIZATION SEQUENCE INITIATED. ALL TRUST ANCHORS REMAIN UNCOMPROMISED.
        </div>
      </div>

    </div>
  );
}
