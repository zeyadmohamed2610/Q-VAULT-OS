// ═══════════════════════════════════════════════════════════════
// PROTOCOL OVERLAY HUD (SCENE 4)
// Tactical military-UI displaying live handshake states.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

const PROTOCOL_STAGES = [
  "DEVICE HELLO",
  "PQ KEY EXCHANGE",
  "ML-KEM-768 ENCAPSULATION",
  "SESSION DERIVATION",
  "AES-256 SECURE CHANNEL",
  "ZERO-KNOWLEDGE VERIFICATION"
];

export function ProtocolOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 4;

  const [entropy, setEntropy] = useState(0);

  // Calculate current stage (0 to 5)
  const currentStageIdx = Math.min(5, Math.floor(progress * 6));

  useEffect(() => {
    if (!isVisible) return;
    
    // Simulate entropy meter fluctuation
    const interval = setInterval(() => {
      setEntropy(240 + Math.random() * 16);
    }, 100);
    
    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in">
      
      {/* Top Left: Main Status */}
      <div className="flex flex-col gap-2">
        <div className="font-mono text-xs tracking-[0.3em] text-[#00e6ff] opacity-80">
          [ HANDSHAKE PROTOCOL ]
        </div>
        <div className="font-mono text-2xl tracking-widest text-white font-bold">
          ESTABLISHING
        </div>
      </div>

      {/* Center Left: Stage Progression */}
      <div className="w-80 backdrop-blur-sm bg-black/30 p-6 border-l-2 border-[#00e6ff]">
        <div className="flex flex-col gap-3">
          {PROTOCOL_STAGES.map((stage, idx) => {
            const isActive = currentStageIdx === idx;
            const isCompleted = currentStageIdx > idx;
            
            return (
              <div key={idx} className={`flex items-center gap-3 transition-opacity duration-300 ${isActive || isCompleted ? 'opacity-100' : 'opacity-30'}`}>
                <div className={`w-2 h-2 ${isCompleted ? 'bg-[#00e6ff]' : isActive ? 'bg-[#00e6ff] animate-pulse' : 'bg-transparent border border-[#00e6ff]/50'}`} />
                <span className={`font-mono text-[11px] tracking-wider ${isActive ? 'text-white font-bold' : 'text-[#00e6ff]'}`}>
                  {stage}
                </span>
                {isActive && (
                  <span className="ml-auto font-mono text-[9px] text-[#00e6ff] animate-pulse">
                    PROCESSING
                  </span>
                )}
                {isCompleted && (
                  <span className="ml-auto font-mono text-[9px] text-white/50">
                    OK
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Right: Analytics */}
      <div className="absolute bottom-12 right-12 flex gap-8 text-right">
        <div className="flex flex-col">
          <span className="font-mono text-[9px] text-[#00e6ff]/60 tracking-widest mb-1">PACKET STREAM</span>
          <span className="font-mono text-sm text-white tracking-widest">
            {Math.floor(progress * 84932).toLocaleString()} B/s
          </span>
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-[9px] text-[#00e6ff]/60 tracking-widest mb-1">TRUE ENTROPY</span>
          <span className="font-mono text-sm text-[#00e6ff] tracking-widest">
            {entropy.toFixed(1)} BITS
          </span>
        </div>
      </div>

    </div>
  );
}
