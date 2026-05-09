// ═══════════════════════════════════════════════════════════════
// PROOF OVERLAY HUD (SCENE 5)
// Minimalist classified overlay for Zero-Knowledge states.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function ProofOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 5;

  const [signature, setSignature] = useState("0x00000000000000000000");

  useEffect(() => {
    if (!isVisible) return;
    
    // Simulate cryptographic proof signature generation
    const interval = setInterval(() => {
      if (progress > 0.5) {
        setSignature("0x" + Array.from({length: 20}, () => Math.floor(Math.random()*16).toString(16)).join(''));
      }
    }, 50);
    
    return () => clearInterval(interval);
  }, [isVisible, progress]);

  if (!isVisible) return null;

  // State phases
  const isIntake = progress < 0.3;
  const isFragmentation = progress >= 0.3 && progress < 0.5;
  const isProofGen = progress >= 0.5 && progress < 0.7;
  const isVaporizing = progress >= 0.7 && progress < 0.9;
  const isComplete = progress >= 0.9;

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen">
      
      {/* Top Left: Main Status */}
      <div className="flex flex-col gap-2">
        <div className="font-mono text-xs tracking-[0.3em] text-white opacity-60">
          [ CRYPTOGRAPHIC CORE ]
        </div>
        <div className="font-mono text-2xl tracking-widest text-[#00e6ff] font-bold">
          {isIntake ? "INTAKE ISOLATION" :
           isFragmentation ? "ENTROPY SEPARATION" :
           isProofGen ? "ZERO-KNOWLEDGE COMPUTATION" :
           isVaporizing ? "SECURE VAPORIZATION" : "VERIFICATION COMPLETE"}
        </div>
      </div>

      {/* Center Right: State Flags */}
      <div className="absolute top-1/2 right-12 -translate-y-1/2 flex flex-col gap-4 text-right">
        <div className={`font-mono text-xs tracking-widest transition-opacity duration-300 ${isProofGen || isVaporizing || isComplete ? 'text-[#00e6ff] opacity-100' : 'text-white opacity-20'}`}>
          PROOF GENERATED
        </div>
        <div className={`font-mono text-xs tracking-widest transition-opacity duration-300 ${isVaporizing || isComplete ? 'text-[#ff3366] opacity-100' : 'text-white opacity-20'}`}>
          SECRET DESTROYED
        </div>
        <div className={`font-mono text-xs tracking-widest transition-opacity duration-300 ${isComplete ? 'text-[#00e6ff] opacity-100 animate-pulse' : 'text-white opacity-20'}`}>
          VERIFICATION COMPLETE
        </div>
        <div className="font-mono text-xs tracking-widest text-white opacity-50 mt-4">
          NO PLAINTEXT EXPOSURE
        </div>
      </div>

      {/* Bottom Left: Proof Signature */}
      <div className="absolute bottom-12 left-12 flex flex-col">
        <span className="font-mono text-[9px] text-white/50 tracking-widest mb-1">ZK-SNARK SIGNATURE</span>
        <span className={`font-mono text-sm tracking-widest ${(isProofGen || isVaporizing || isComplete) ? 'text-[#00e6ff]' : 'text-white/20'}`}>
          {signature}
        </span>
      </div>

    </div>
  );
}
