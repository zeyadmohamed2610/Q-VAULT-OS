// ═══════════════════════════════════════════════════════════════
// HISTORICAL CONTINUUM
// Persistent civilization timeline.
// Cryptographic epochs, governance succession,
// infrastructure survival records.
// Feels like viewing the preserved history of a sovereign system.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useState, useEffect } from 'react';
import { archivePersistence, type ArchiveSnapshot } from '@/lib/ArchivePersistence';
import { useSovereignState, formatLargeNumber } from '@/lib/PersistentStateEngine';
import { sovereignRuntime } from '@/lib/SovereignRuntime';

// Fixed civilization epochs — hardcoded history
const CIVILIZATION_EPOCHS = [
  { year: 2019, event: 'NIST PQC Competition: Final Round',           type: 'genesis' },
  { year: 2022, event: 'ML-KEM (Kyber) Selected',                     type: 'milestone' },
  { year: 2024, event: 'FIPS 203/204/205 Ratified',                  type: 'milestone' },
  { year: 2025, event: 'Q-VAULT Genesis: Sovereign HSM Provisioned', type: 'genesis' },
  { year: 2026, event: 'First Attestation Cycle: VERIFIED',           type: 'operational' },
  { year: 2027, event: 'Global Node Expansion: 256 Relays',           type: 'expansion' },
  { year: 2030, event: 'Decade Continuity Certificate Issued',        type: 'archival' },
  { year: 2035, event: 'Post-Quantum Migration: Complete',            type: 'archival' },
];

const EPOCH_COLORS: Record<string, string> = {
  genesis:     'rgba(0,230,255,0.7)',
  milestone:   'rgba(0,200,220,0.5)',
  operational: 'rgba(0,180,200,0.45)',
  expansion:   'rgba(0,160,180,0.4)',
  archival:    'rgba(0,140,160,0.35)',
};

function EpochRow({ year, event, type }: { year: number; event: string; type: string }) {
  return (
    <div className="flex gap-3 items-start">
      <span
        className="font-mono text-[9px] tabular-nums shrink-0 mt-0.5 tracking-wider"
        style={{ color: EPOCH_COLORS[type] ?? 'rgba(0,230,255,0.4)' }}
      >
        {year}
      </span>
      <div className="flex gap-2 items-start min-w-0">
        <div
          className="mt-[5px] w-1 h-1 rounded-full shrink-0"
          style={{ background: EPOCH_COLORS[type] ?? 'rgba(0,230,255,0.4)' }}
        />
        <span className="font-mono text-[9px] text-white/35 tracking-wide leading-4 truncate">
          {event}
        </span>
      </div>
    </div>
  );
}

function SnapshotRow({ snap }: { snap: ArchiveSnapshot }) {
  return (
    <div className="flex justify-between items-baseline gap-2 opacity-60">
      <span className="font-mono text-[8px] text-white/20 tracking-widest shrink-0">
        {snap.timestamp.slice(11, 19)}
      </span>
      <span className="font-mono text-[8px] text-white/15 tracking-wider truncate">
        SCN:{String(snap.scene).padStart(2,'0')} · ATT:{formatLargeNumber(snap.attestationCycles)}
      </span>
      <span className="font-mono text-[7px] text-white/10 tracking-widest shrink-0">
        {snap.checksum}
      </span>
    </div>
  );
}

export function HistoricalContinuum({ visible = false }: { visible?: boolean }) {
  const sys = useSovereignState();
  const [snapshots, setSnapshots] = useState<ArchiveSnapshot[]>([]);
  const [sessionId, setSessionId] = useState('');

  useEffect(() => {
    setSessionId(sovereignRuntime.metrics.sessionId);
    const unsub = sovereignRuntime.subscribe(() => {
      setSnapshots([...archivePersistence.snapshots].reverse().slice(0, 8));
    });
    return () => {
      unsub();
    };
  }, []);

  if (!visible) return null;

  return (
    <div
      className="fixed left-6 top-1/2 -translate-y-1/2 z-[60] pointer-events-none select-none"
      style={{
        width: 260,
        background: 'rgba(2,4,8,0.94)',
        border: '1px solid rgba(0,230,255,0.06)',
        borderLeft: '1px solid rgba(0,230,255,0.15)',
        backdropFilter: 'blur(10px)',
      }}
    >
      {/* Header */}
      <div className="px-4 py-2 border-b border-white/5 flex justify-between items-center">
        <span className="font-mono text-[8px] tracking-[0.4em] text-white/25 uppercase">
          INFRASTRUCTURE CHRONICLE
        </span>
        <span className="font-mono text-[7px] text-white/10 tracking-wider">{sessionId}</span>
      </div>

      {/* Civilization epochs */}
      <div className="px-4 py-3 space-y-2">
        {CIVILIZATION_EPOCHS.map((e, i) => (
          <EpochRow key={i} {...e} />
        ))}
      </div>

      <div className="mx-4 h-px bg-white/5" />

      {/* Live session snapshots */}
      <div className="px-4 py-2">
        <div className="font-mono text-[7px] tracking-[0.4em] text-white/15 uppercase mb-2">
          SESSION ARCHIVE
        </div>
        {snapshots.length === 0 ? (
          <div className="font-mono text-[8px] text-white/10 tracking-wider">
            AWAITING FIRST SNAPSHOT…
          </div>
        ) : (
          <div className="space-y-1">
            {snapshots.map(s => <SnapshotRow key={s.id} snap={s} />)}
          </div>
        )}
      </div>

      {/* Bottom stats */}
      <div className="px-4 py-2 border-t border-white/5 flex justify-between">
        <span className="font-mono text-[7px] text-white/10 tracking-widest">
          TRUST {(sys.trustScore * 100).toFixed(2)}%
        </span>
        <span className="font-mono text-[7px] text-white/10 tracking-widest">
          EPOCH {sovereignRuntime.metrics.epoch}
        </span>
      </div>
    </div>
  );
}
