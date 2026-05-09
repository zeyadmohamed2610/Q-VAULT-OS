// ═══════════════════════════════════════════════════════════════
// TRUST STACK OVERLAY HUD (SCENE 3)
// Minimal classified overlays tracking stack activation
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';

const STACK_LAYERS = [
  "HARDWARE ROOT",
  "SECURE BOOT",
  "ML-KEM-768 EXCHANGE",
  "SESSION ENCLAVE",
  "POLICY ENGINE",
  "GOVERNANCE RUNTIME"
];

export function TrustStackOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 3;

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-16 z-20 flex flex-col justify-center animate-fade-in">
      
      {/* Left-aligned Activation Tracker */}
      <div className="w-64 backdrop-blur-sm bg-black/20 p-6 border border-[#00e6ff]/20">
        <div className="font-mono text-xs tracking-[0.3em] text-[#00e6ff]/70 mb-6">
          [ ACTIVE TRUST CHAIN ]
        </div>

        <div className="flex flex-col gap-4">
          {STACK_LAYERS.map((layer, idx) => {
            // Calculate activation timing based on scene progress
            const activationThreshold = 0.1 + (idx * 0.15);
            const isActivated = progress > activationThreshold;
            
            return (
              <div key={idx} className="flex items-center gap-4">
                <div className="relative flex items-center justify-center w-4 h-4">
                  {/* Outer bracket */}
                  <div className={`absolute inset-0 border transition-colors duration-500 ${isActivated ? 'border-[#00e6ff]' : 'border-white/20'}`} />
                  {/* Inner fill */}
                  <div className={`w-2 h-2 transition-all duration-300 ${isActivated ? 'bg-[#00e6ff] scale-100' : 'bg-transparent scale-0'}`} />
                </div>
                
                <span className={`font-mono text-[10px] tracking-widest transition-colors duration-500 ${isActivated ? 'text-[#00e6ff] font-bold' : 'text-white/40'}`}>
                  {layer}
                </span>
                
                {isActivated && (
                  <span className="font-mono text-[8px] text-[#00e6ff]/70 ml-auto animate-pulse">
                    VERIFIED
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Right-side Data Flow Indicators */}
      <div className="absolute right-8 md:right-16 top-1/2 -translate-y-1/2 flex flex-col items-end gap-2">
        <div className="font-mono text-[10px] tracking-widest text-[#00e6ff]/50 mb-2">
          VERTICAL DATA BUS
        </div>
        
        {/* Simple animated flow indicator */}
        <div className="w-1 h-32 bg-white/5 relative overflow-hidden">
          <div 
            className="absolute top-0 left-0 w-full bg-[#00e6ff] opacity-80"
            style={{
              height: '20%',
              animation: 'busFlow 1s linear infinite'
            }}
          />
        </div>
        <div className="font-mono text-[8px] tracking-widest text-[#00e6ff] mt-2">
          {Math.floor(progress * 100)}% CAPACITY
        </div>
      </div>

    </div>
  );
}
