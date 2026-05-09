// ═══════════════════════════════════════════════════════════════
// HARDWARE REVEAL OVERLAY HUD (SCENE 2)
// Minimal tactical specification card indicating engineering specs
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

export function HardwareOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 2;

  // Typewriter effect for specs
  const [specLines, setSpecLines] = useState<string[]>([]);
  
  const fullSpecs = [
    "ESP32-S3 SECURE MICROCONTROLLER",
    "POST-QUANTUM ML-KEM-768",
    "AES-256-GCM SYMMETRIC ENCLAVE",
    "HARDWARE TRUST ANCHOR VERIFIED",
    "UART 115200 BAUDRATE ESTABLISHED",
    "SECURE BOOT: ENABLED"
  ];

  useEffect(() => {
    if (!isVisible) {
      setSpecLines([]);
      return;
    }

    // Reveal lines progressively based on scene progress
    // Scene progress 0.4 to 0.7 reveals the 6 lines
    const currentLineCount = Math.floor(Math.max(0, (progress - 0.4) / 0.3) * fullSpecs.length);
    const clampedCount = Math.min(currentLineCount, fullSpecs.length);
    
    if (specLines.length !== clampedCount) {
      setSpecLines(fullSpecs.slice(0, clampedCount));
    }
  }, [progress, isVisible]);

  if (!isVisible) return null;

  // HUD fades out as the hardware descends to the Trust Stack
  const opacity = progress > 0.8 ? 1.0 - ((progress - 0.8) / 0.2) : (progress > 0.3 ? 1.0 : 0.0);

  return (
    <div 
      className="absolute inset-0 pointer-events-none flex items-center justify-end p-12 md:p-24 z-20"
      style={{ opacity, transition: 'opacity 0.5s ease-out' }}
    >
      {/* Floating Specification Card */}
      <div className="flex flex-col gap-3 border-l-2 border-white/40 pl-6 w-80 backdrop-blur-md bg-black/40 py-4">
        <div className="font-mono text-xs tracking-[0.3em] text-white/50 mb-2">
          [ PHYSICAL TRUST ANCHOR ]
        </div>
        
        {specLines.map((line, idx) => (
          <div 
            key={idx} 
            className="font-mono text-sm tracking-wider text-white/90 animate-fade-in flex items-center gap-2"
          >
            <div className="w-1.5 h-1.5 bg-white opacity-60" />
            {line}
          </div>
        ))}
        
        {/* Subtle decorative elements */}
        {specLines.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10 flex justify-between items-center">
            <span className="font-mono text-[10px] text-white/30 tracking-widest">Q-VAULT PROTOCOL V2</span>
            <div className="flex gap-1">
              <div className="w-1 h-2 bg-white/60 animate-pulse" />
              <div className="w-1 h-2 bg-white/20" />
              <div className="w-1 h-2 bg-white/20" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
