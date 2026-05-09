// ═══════════════════════════════════════════════════════════════
// THREAT OVERLAY HUD (SCENE 1)
// Tactical military-scientific overlay indicating quantum threat
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function ThreatOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 1;

  // Track glitch states
  const [glitchText, setGlitchText] = useState('HARVEST NOW. DECRYPT LATER.');

  useEffect(() => {
    if (!isVisible) return;
    
    // Simulate digital instability as progress increases
    let interval: NodeJS.Timeout;
    if (progress > 0.5) {
      interval = setInterval(() => {
        if (Math.random() > 0.8) {
          const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+';
          const randomChar = chars[Math.floor(Math.random() * chars.length)];
          const base = 'HARVEST NOW. DECRYPT LATER.';
          const idx = Math.floor(Math.random() * base.length);
          const newText = base.substring(0, idx) + randomChar + base.substring(idx + 1);
          setGlitchText(newText);
          
          setTimeout(() => setGlitchText(base), 50 + Math.random() * 100);
        }
      }, 100);
    } else {
      setGlitchText('HARVEST NOW. DECRYPT LATER.');
    }

    return () => clearInterval(interval);
  }, [progress, isVisible]);

  if (!isVisible) return null;

  return (
    <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-16 z-20 font-mono text-white/40">
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] tracking-[0.4em] uppercase font-bold text-white/60">THREAT_IDENTIFIER // L14</span>
          <span className="text-[8px] tracking-[0.2em] uppercase">VULNERABILITY: RSA_2048_DESTABILIZATION</span>
        </div>
        <div className="text-right flex flex-col gap-1">
          <span className="text-[10px] tracking-[0.4em] uppercase text-white/40">CRITICAL_STATE</span>
          <span className="text-[8px] tracking-[0.2em] uppercase">Q_DAY_THRESHOLD_PROJECTION: EXCEEDED</span>
        </div>
      </div>

      <div className="flex justify-center">
        <h2 className="text-[14px] tracking-[0.6em] uppercase font-light text-white/80 animate-pulse">
          HARVEST NOW. DECRYPT LATER.
        </h2>
      </div>

      <div className="flex justify-between items-end">
        <div className="max-w-xs text-[8px] tracking-[0.2em] leading-relaxed uppercase">
          LATTICE STRUCTURE DESTABILIZATION DETECTED. LEGACY PRIMITIVES UNDERGOING RAPID DECAY. 
          INFRASTRUCTURE RISK: CATEGORY_NULL.
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className="text-[10px] tracking-[0.4em] uppercase">FIELD_SYMMETRY</span>
          <span className="text-[12px] tracking-[0.2em] text-white/60">{(progress * 100).toFixed(2)}%</span>
        </div>
      </div>
    </div>
  );
}
