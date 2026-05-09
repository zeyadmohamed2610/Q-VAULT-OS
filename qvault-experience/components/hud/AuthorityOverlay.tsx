// ═══════════════════════════════════════════════════════════════
// AUTHORITY OVERLAY — Phase XVI
// Colder. Machine-like. Restrained.
// Real-world infrastructure identifiers and rack topology.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useSovereignState } from '@/lib/PersistentStateEngine';
import { useExperienceStore } from '@/lib/store';
import { SCENE_REGISTRY } from '@/lib/scenes';
import { useMemo } from 'react';

// Sovereign state constants
const IS_AUTHORITY = true;

const DATACENTERS = ['NOR-01', 'SGP-04', 'USA-12', 'DEU-08', 'CHE-02'];

export function AuthorityOverlay() {
  const sys = useSovereignState();
  const activeScene = useExperienceStore((s) => s.activeScene);
  const sceneConfig = SCENE_REGISTRY[activeScene];

  // Pre-compute rack states once — prevents flash on every render
  const rackStates = useMemo(
    () => Array.from({ length: 16 }, () => Math.random() > 0.7),
    []
  );

  const sessionDisplay = `QV-AUTH-${Math.floor(sys.uptimeSeconds)
    .toString(36)
    .toUpperCase()
    .padStart(6, '0')}`;

  if (!IS_AUTHORITY) return null;

  return (
    <div className="fixed inset-0 z-[110] pointer-events-none select-none font-mono text-white/40 uppercase">
      {/* ── Datacenter Registry ── */}
      <div className="absolute top-12 left-12 flex flex-col gap-1">
        <div className="text-[10px] text-white/20 mb-2">INFRASTRUCTURE_REGISTRY</div>
        <div className="mb-4 text-[8px] text-white/40">COMPLIANCE_ROOT: NIST-PQC-VERIFIED</div>
        {DATACENTERS.map((dc, i) => (
          <div key={dc} className="flex items-center gap-4 text-[9px]">
            <span className={i === (activeScene % 5) ? "text-white/80" : "text-white/20"}>
              DC-{dc}
            </span>
            <span className="w-12 h-[1px] bg-white/5" />
            <span className={i === (activeScene % 5) ? "text-white/60" : "text-white/10"}>
              {i === (activeScene % 5) ? "ACTIVE_SYNC" : "STANDBY"}
            </span>
          </div>
        ))}
      </div>

      {/* ── Rack Topology (Abstract) ── */}
      <div className="absolute top-12 right-12 flex flex-col items-end gap-1">
        <div className="text-[10px] text-white/20 mb-2">RACK_TOPOLOGY</div>
        <div className="text-[8px] text-white/40 mb-2">READINESS_LEVEL: L5_PROD</div>
        <div className="grid grid-cols-4 gap-1">
          {rackStates.map((active, i) => (
            <div
              key={i}
              className="w-4 h-1 border border-white/5"
              style={{
                backgroundColor: active ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            />
          ))}
        </div>
        <div className="text-[8px] text-white/10 mt-2">U_HEIGHT: 42 // SLOT_STATUS: VERIFIED</div>
      </div>

      {/* ── Central Authority Status ── */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 text-center">
        <div className="text-[24px] tracking-[0.4em] font-light text-white/90 mb-1">
          {sceneConfig?.name || 'CORE'}
        </div>
        <div className="text-[9px] tracking-[0.8em] text-white/20">
          SYSTEM_AUTHORITY: {sessionDisplay}
        </div>
      </div>

      {/* ── Immutable Archive States ── */}
      <div className="absolute bottom-12 right-12 flex flex-col items-end gap-2">
        <div className="flex items-center gap-3">
          <span className="text-[8px] tracking-widest text-white/20 uppercase">MANUFACTURING_SYNC</span>
          <div className="flex gap-0.5">
            {[...Array(6)].map((_, i) => (
              <div key={i} className={`w-1.5 h-1.5 ${i < 5 ? 'bg-white/40' : 'bg-white/5'}`} />
            ))}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[8px] tracking-widest text-white/20">ARCHIVE_REPLICATION</span>
          <div className="flex gap-0.5">
            {[...Array(6)].map((_, i) => (
              <div key={i} className={`w-1.5 h-1.5 ${i < 4 ? 'bg-white/40' : 'bg-white/5'}`} />
            ))}
          </div>
        </div>
        <div className="text-[9px] text-white/40">
          EPOCH: {Math.floor(sys.uptimeSeconds / 3600)} // STATE: IMMUTABLE
        </div>
      </div>

      {/* ── Institutional Corner Markers ── */}
      <div className="absolute top-0 left-0 w-32 h-32 border-l border-t border-white/5" />
      <div className="absolute top-0 right-0 w-32 h-32 border-r border-t border-white/5" />
      <div className="absolute bottom-0 left-0 w-32 h-32 border-l border-b border-white/5" />
      <div className="absolute bottom-0 right-0 w-32 h-32 border-r border-b border-white/5" />
    </div>
  );
}
