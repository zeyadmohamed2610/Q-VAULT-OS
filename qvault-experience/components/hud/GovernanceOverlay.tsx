// ═══════════════════════════════════════════════════════════════
// GOVERNANCE OVERLAY HUD (SCENE 8)
// Minimal but terrifyingly precise UI for the command authority.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function GovernanceOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const isVisible = activeScene === 8;

  const [nodes, setNodes] = useState(14023);

  useEffect(() => {
    if (!isVisible) return;
    const interval = setInterval(() => {
      setNodes(prev => prev + (Math.random() > 0.5 ? 1 : -1));
    }, 1000);
    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen text-white font-mono">
      
      {/* Top Bar */}
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <div className="text-xs tracking-[0.3em] opacity-60">SOVEREIGN AUTHORITY</div>
          <div className="text-2xl tracking-widest font-bold text-[#00e6ff]">TRUST NETWORK ACTIVE</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest opacity-50">GLOBAL INFRASTRUCTURE</div>
          <div className="text-sm tracking-widest text-[#00e6ff] animate-pulse">DEFENSE ONLINE</div>
        </div>
      </div>

      {/* Center Reticle */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-20">
        <div className="w-96 h-96 border-[0.5px] border-[#00e6ff] rounded-full flex items-center justify-center">
          <div className="w-80 h-80 border-[0.5px] border-dashed border-[#00e6ff] rounded-full animate-spin-slow" />
        </div>
      </div>

      {/* Side Stats */}
      <div className="absolute top-1/2 left-12 -translate-y-1/2 flex flex-col gap-8">
        <div>
          <div className="text-[10px] opacity-50 tracking-widest border-b border-white/20 pb-1 mb-2">VERIFIED NODES</div>
          <div className="text-3xl text-[#00e6ff] font-bold">{nodes.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-[10px] opacity-50 tracking-widest border-b border-white/20 pb-1 mb-2">ATTESTATION</div>
          <div className="text-xl">99.999%</div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="flex justify-between items-end border-t border-white/20 pt-4">
        <div className="flex gap-12">
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50">CONSENSUS</div>
            <div className="text-sm text-[#00e6ff]">STABLE</div>
          </div>
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50">THREAT PREDICTION</div>
            <div className="text-sm">ACTIVE MONITORING</div>
          </div>
        </div>
        
        <div className="text-[10px] tracking-widest opacity-30 max-w-xs text-right">
          CRYPTOGRAPHIC AUTHORITY PROPAGATION IS FUNCTIONING WITHIN NORMAL PARAMETERS
        </div>
      </div>

    </div>
  );
}
