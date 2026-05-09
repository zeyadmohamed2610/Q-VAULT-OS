// ═══════════════════════════════════════════════════════════════
// OS SURFACE OVERLAY HUD (SCENE 7)
// High-density data feeds acting as the actual OS interface.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function OsOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 7;

  const [telemetry, setTelemetry] = useState<string[]>([]);
  const [threatCount, setThreatCount] = useState(0);

  useEffect(() => {
    if (!isVisible) return;
    
    // Simulate live OS telemetry
    const interval = setInterval(() => {
      setTelemetry((prev) => {
        const newFeed = [...prev, `[SYS] ${new Date().toISOString()} - Q-STATE VERIFIED - ENTROPY: ${(Math.random() * 100).toFixed(2)}`];
        return newFeed.slice(-10); // Keep last 10
      });
      if (Math.random() > 0.8) {
        setThreatCount((prev) => prev + Math.floor(Math.random() * 3));
      }
    }, 400);
    
    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen text-[#00e6ff] font-mono">
      
      {/* Top Bar: Governance & System State */}
      <div className="flex justify-between items-start border-b border-[#00e6ff]/30 pb-4">
        <div className="flex flex-col gap-1">
          <div className="text-xs tracking-[0.3em] opacity-60 text-white">Q-VAULT CENTRAL COMMAND</div>
          <div className="text-xl tracking-widest font-bold">OS KERNEL ACTIVE</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest opacity-50 text-white">SYSTEM GOVERNANCE</div>
          <div className="text-sm tracking-widest">ML-KEM-768 BOUND // NODE 01</div>
        </div>
      </div>

      <div className="flex-1 flex justify-between items-center my-8">
        {/* Left: Terminal Stream overlay mapping to left panel */}
        <div className="w-1/3 flex flex-col gap-2 max-h-full overflow-hidden opacity-80" style={{ transform: 'perspective(500px) rotateY(10deg)' }}>
          <div className="text-[10px] text-white opacity-50 tracking-widest border-b border-[#00e6ff]/20 pb-1 mb-2">LIVE TELEMETRY</div>
          {telemetry.map((line, i) => (
            <div key={i} className="text-[9px] tracking-wider truncate">{line}</div>
          ))}
        </div>

        {/* Right: Threat Map / Enclave State mapping to right panel */}
        <div className="w-1/4 flex flex-col gap-6 opacity-90 text-right" style={{ transform: 'perspective(500px) rotateY(-10deg)' }}>
          <div>
            <div className="text-[10px] text-white opacity-50 tracking-widest border-b border-[#ff3366]/20 pb-1 mb-2 border-r pr-2">THREAT INTELLIGENCE</div>
            <div className="text-3xl text-[#ff3366] font-bold">{threatCount}</div>
            <div className="text-[9px] opacity-70 mt-1">THREATS NEUTRALIZED</div>
          </div>
          
          <div>
            <div className="text-[10px] text-white opacity-50 tracking-widest border-b border-[#00e6ff]/20 pb-1 mb-2 border-r pr-2">SECURE ENCLAVE</div>
            <div className="text-sm tracking-widest">LOCKED</div>
            <div className="text-[9px] opacity-70 mt-1">ZERO-KNOWLEDGE PROOF: VALID</div>
          </div>
        </div>
      </div>

      {/* Bottom Bar: Attestation Monitor */}
      <div className="flex justify-between items-end border-t border-[#00e6ff]/30 pt-4">
        <div className="flex gap-8">
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50 text-white">MEMORY ALLOCATION</div>
            <div className="text-sm">4.2 PB / SECURE</div>
          </div>
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50 text-white">NETWORK STATE</div>
            <div className="text-sm">ISOLATED</div>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-[10px] tracking-widest opacity-50 text-white">ATTESTATION</div>
          <div className="w-32 h-1 bg-[#00e6ff]/20 rounded-full overflow-hidden">
            <div className="w-full h-full bg-[#00e6ff] animate-pulse" />
          </div>
          <div className="text-xs font-bold">100%</div>
        </div>
      </div>

    </div>
  );
}
