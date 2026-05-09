// ═══════════════════════════════════════════════════════════════
// SEAL OVERLAY HUD (SCENE 12)
// Final system closure UI.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';

const LOCK_SEQUENCE = [
  { p: 0.1, text: "SESSION TERMINATED" },
  { p: 0.3, text: "MEMORY PURGED" },
  { p: 0.5, text: "KEYS SEALED" },
  { p: 0.6, text: "TRUST PRESERVED" },
  { p: 0.7, text: "GOVERNANCE LOCKED" },
  { p: 0.8, text: "ARCHIVAL STATE IMMUTABLE" }
];

export function SealOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 12;

  if (!isVisible) return null;

  // The HUD fades out entirely by 0.9
  const hudOpacity = Math.max(0, 1.0 - Math.max(0, progress - 0.7) / 0.2);

  // Final text reveals after 0.95
  const finalOpacity = Math.max(0, Math.min(1, (progress - 0.95) / 0.05));

  return (
    <div className="absolute inset-0 pointer-events-none z-30 flex flex-col items-center justify-center font-mono">
      
      {/* HUD fading out */}
      <div 
        className="absolute inset-0 p-8 md:p-12 flex flex-col justify-between"
        style={{ opacity: hudOpacity }}
      >
        <div className="text-center w-full">
          <div className="text-xs tracking-[0.3em] opacity-60 text-white">SYSTEM CLOSURE INITIATED</div>
        </div>

        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col gap-4 text-center">
          {LOCK_SEQUENCE.map((stage, idx) => {
            const isDone = progress >= stage.p;
            if (!isDone) return null;
            return (
              <div key={idx} className="text-[#ff0044] text-lg tracking-widest font-bold animate-fade-in mix-blend-screen">
                {stage.text}
              </div>
            );
          })}
        </div>
      </div>

      {/* FINAL SILENT TEXT */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2"
        style={{ opacity: finalOpacity }}
      >
        <div className="text-white text-3xl font-bold tracking-[0.5em] mix-blend-screen">Q-VAULT</div>
        <div className="text-white/50 text-xs tracking-widest">POST-QUANTUM TRUST PRESERVED</div>
      </div>

    </div>
  );
}
