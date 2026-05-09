// ═══════════════════════════════════════════════════════════════
// ROADMAP OVERLAY HUD (SCENE 11)
// Strategic Cryptographic Horizon Visualization UI.
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

const ROADMAP_MILESTONES = [
  "Autonomous Trust Federation",
  "Multi-Region Governance Mesh",
  "Quantum Migration Layer",
  "Hardware Attestation Satellites",
  "Distributed Sovereign Identity",
  "Zero-Knowledge Infrastructure APIs",
  "Post-Quantum Civil Infrastructure",
  "Planetary Cryptographic Continuity"
];

export function RoadmapOverlay() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const progress = useExperienceStore((s) => s.sceneProgress);
  const isVisible = activeScene === 11;

  if (!isVisible) return null;

  // Reveal index based on how deep we flew into the z-axis
  const visibleCount = Math.max(1, Math.ceil(progress * ROADMAP_MILESTONES.length));

  return (
    <div className="absolute inset-0 pointer-events-none p-8 md:p-12 z-20 flex flex-col justify-between animate-fade-in mix-blend-screen text-white font-mono">
      
      {/* Top Bar */}
      <div className="flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <div className="text-xs tracking-[0.3em] opacity-60">SOVEREIGN EXPANSION VECTORS</div>
          <div className="text-2xl tracking-widest font-bold text-[#00e6ff]">STRATEGIC HORIZON</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-widest opacity-50">INFRASTRUCTURE PLANNING</div>
          <div className="text-sm tracking-widest text-[#00e6ff] animate-pulse">EXPANSION ACTIVE</div>
        </div>
      </div>

      {/* Floating Milestones List */}
      <div className="absolute top-1/2 right-12 -translate-y-1/2 w-96 flex flex-col gap-8 text-right">
        {ROADMAP_MILESTONES.map((milestone, idx) => {
          const isRevealed = idx < visibleCount;
          const isCurrent = idx === visibleCount - 1;
          
          if (!isRevealed && !isCurrent) return null;

          return (
            <div key={idx} className={`transition-all duration-1000 ${isCurrent ? 'opacity-100 translate-x-0' : 'opacity-30 translate-x-4'}`}>
              <div className={`text-[10px] opacity-50 tracking-widest border-b pb-1 mb-2 ${isCurrent ? 'border-[#00e6ff]/50' : 'border-white/20'}`}>
                PHASE 0{idx + 1}
              </div>
              <div className={`text-lg font-bold tracking-wide ${isCurrent ? 'text-[#00e6ff]' : 'text-white'}`}>
                {milestone.toUpperCase()}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Bar */}
      <div className="flex justify-between items-end border-t border-white/20 pt-4">
        <div className="flex gap-12">
          <div className="flex flex-col">
            <div className="text-[10px] tracking-widest opacity-50">HORIZON PROJECTION</div>
            <div className="text-sm text-[#00e6ff]">DEEP TIME ARCHITECTURE</div>
          </div>
        </div>
        
        <div className="text-[10px] tracking-widest opacity-30 max-w-sm text-right">
          ALL FUTURE MILESTONES ARE MATHEMATICALLY BOUND TO THE ROOT TRUST ANCHOR.
        </div>
      </div>

    </div>
  );
}
