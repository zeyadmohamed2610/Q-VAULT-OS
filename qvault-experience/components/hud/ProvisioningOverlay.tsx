// ═══════════════════════════════════════════════════════════════
// PROVISIONING OVERLAY HUD (SCENE 6)
// Minimal military UI for the hardware onboarding ritual.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

const PROVISIONING_STAGES = [
  "HARDWARE ISOLATION",
  "ROOT KEY INJECTION",
  "ML-KEM-768 BOUND",
  "ENCLAVE SEALED",
  "DEVICE ATTESTED",
  "GOVERNANCE REGISTERED"
];

export function ProvisioningOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 6;

  const [serial, setSerial] = useState("QV-");

  // Calculate current stage (0 to 5)
  const currentStageIdx = Math.min(5, Math.floor(progress * 6));

  useEffect(() => {
    if (!isVisible) return;
    
    // Generate a static serial for this session
    setSerial("QV-" + Math.floor(Math.random() * 100000000).toString(16).toUpperCase().padStart(8, '0'));
  }, [isVisible]);

  if (!isVisible) return null;

  const isComplete = progress >= 0.9;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen">
      
      {/* Top Left: Main Status */}
      <div className="flex flex-col gap-2">
        <div className="font-mono text-xs tracking-[0.3em] text-white opacity-60">
          [ DEVICE ONBOARDING ]
        </div>
        <div className="font-mono text-2xl tracking-widest text-[#00e6ff] font-bold">
          {isComplete ? "PROVISIONING COMPLETE" : "CALIBRATION ACTIVE"}
        </div>
      </div>

      {/* Center Left: Stage Progression */}
      <div className="absolute top-1/2 left-12 -translate-y-1/2 w-80">
        <div className="flex flex-col gap-4">
          {PROVISIONING_STAGES.map((stage, idx) => {
            const isActive = currentStageIdx === idx;
            const isDone = currentStageIdx > idx;
            
            return (
              <div key={idx} className={`flex items-center gap-4 transition-opacity duration-300 ${isActive || isDone ? 'opacity-100' : 'opacity-20'}`}>
                <div className={`w-3 h-3 border border-[#00e6ff] flex items-center justify-center ${isDone ? 'bg-[#00e6ff]' : ''}`}>
                  {isActive && <div className="w-1.5 h-1.5 bg-[#00e6ff] animate-ping" />}
                </div>
                <span className={`font-mono text-xs tracking-widest ${isActive ? 'text-white font-bold' : 'text-[#00e6ff]'}`}>
                  {stage}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Right: Hardware Diagnostics */}
      <div className="absolute bottom-12 right-12 flex gap-12 text-right">
        <div className="flex flex-col">
          <span className="font-mono text-[9px] text-[#00e6ff]/60 tracking-widest mb-1">HARDWARE SERIAL</span>
          <span className="font-mono text-sm text-white tracking-widest">
            {serial}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-[9px] text-[#00e6ff]/60 tracking-widest mb-1">THERMAL STABILITY</span>
          <span className="font-mono text-sm text-[#00e6ff] tracking-widest">
            {(38.2 + Math.sin(progress * 20) * 0.5).toFixed(1)} °C
          </span>
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-[9px] text-[#00e6ff]/60 tracking-widest mb-1">SEAL INTEGRITY</span>
          <span className="font-mono text-sm text-[#00e6ff] tracking-widest">
            {(Math.min(100, progress * 120)).toFixed(2)}%
          </span>
        </div>
      </div>

    </div>
  );
}
