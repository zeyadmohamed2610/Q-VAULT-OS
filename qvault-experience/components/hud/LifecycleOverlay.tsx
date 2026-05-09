// ═══════════════════════════════════════════════════════════════
// LIFECYCLE OVERLAY HUD (SCENE 10)
// Sovereign archival UI.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

const LIFECYCLE_STAGES = [
  "INITIALIZATION",
  "PROVISIONED",
  "ACTIVE SERVICE",
  "TRUST SYNCHRONIZATION",
  "GOVERNANCE ROTATION",
  "ARCHIVAL PRESERVATION"
];

export function LifecycleOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 10;

  const [uptimeYears, setUptimeYears] = useState(0);

  // Calculate current stage (0 to 5)
  const currentStageIdx = Math.min(5, Math.floor(progress * 6));

  useEffect(() => {
    if (!isVisible) return;
    
    const interval = setInterval(() => {
      setUptimeYears((prev) => prev + 0.1);
    }, 100);
    
    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  const isComplete = progress >= 0.9;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen text-white font-mono">
      
      {/* Top Bar: Archival Status */}
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <div className="text-xs tracking-[0.3em] opacity-60">SOVEREIGN ARCHIVE</div>
          <div className="text-2xl tracking-widest font-bold text-[#00e6ff]">
            {isComplete ? "LONG-TERM CONTINUITY VERIFIED" : "DEVICE LIFECYCLE STABLE"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest opacity-50">COMPLIANCE</div>
          <div className="text-sm tracking-widest text-[#00e6ff]">POST-QUANTUM VERIFIED</div>
        </div>
      </div>

      {/* Center Left: Lifecycle Progression */}
      <div className="absolute top-1/2 left-12 -translate-y-1/2 w-80">
        <div className="flex flex-col gap-6 border-l border-[#00e6ff]/30 pl-4">
          {LIFECYCLE_STAGES.map((stage, idx) => {
            const isActive = currentStageIdx === idx;
            const isDone = currentStageIdx > idx;
            
            return (
              <div key={idx} className={`relative flex items-center gap-4 transition-opacity duration-500 ${isActive || isDone ? 'opacity-100' : 'opacity-20'}`}>
                {/* Timeline dot */}
                <div className={`absolute -left-[21px] w-2 h-2 rounded-full border ${isDone ? 'bg-[#00e6ff] border-[#00e6ff]' : isActive ? 'bg-transparent border-[#00e6ff]' : 'bg-transparent border-white/20'}`}>
                  {isActive && <div className="absolute inset-0 bg-[#00e6ff] animate-ping rounded-full" />}
                </div>
                <span className={`font-mono text-xs tracking-widest ${isActive ? 'text-[#00e6ff] font-bold' : isDone ? 'text-white' : 'text-white/50'}`}>
                  {stage}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Center Right: Deep Time Telemetry */}
      <div className="absolute top-1/2 right-12 -translate-y-1/2 flex flex-col gap-8 text-right">
        <div>
          <div className="text-[10px] opacity-50 tracking-widest border-b border-[#00e6ff]/20 pb-1 mb-2">UPTIME</div>
          <div className="text-3xl text-[#00e6ff] font-bold">{uptimeYears.toFixed(1)} <span className="text-lg">YRS</span></div>
        </div>
        <div>
          <div className="text-[10px] opacity-50 tracking-widest border-b border-[#00e6ff]/20 pb-1 mb-2">ATTESTATION CYCLES</div>
          <div className="text-xl">{(uptimeYears * 105120).toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
        <div>
          <div className="text-[10px] opacity-50 tracking-widest border-b border-[#00e6ff]/20 pb-1 mb-2">PRESERVATION TEMP</div>
          <div className="text-xl">1.2 K</div>
        </div>
      </div>

      {/* Bottom Bar: Continuity State */}
      <div className="flex justify-between items-end border-t border-white/20 pt-4">
        <div className="flex gap-12">
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50">CONTINUITY INDEX</div>
            <div className="text-sm text-[#00e6ff]">1.00000000</div>
          </div>
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50">ENTROPY DRIFT</div>
            <div className="text-sm">0.000%</div>
          </div>
        </div>
        
        <div className="text-[10px] tracking-widest opacity-30 max-w-sm text-right">
          CRYPTOGRAPHIC MATERIAL PRESERVED. ANCHOR REMAINS VALID FOR DEEP-TIME INFRASTRUCTURE ROTATION.
        </div>
      </div>

    </div>
  );
}
