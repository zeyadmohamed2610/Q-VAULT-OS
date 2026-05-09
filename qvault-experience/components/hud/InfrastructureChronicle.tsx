// ═══════════════════════════════════════════════════════════════
// INFRASTRUCTURE CHRONICLE
// Compact persistent timeline strip — always visible.
// Shows live epoch, session uptime, and last anomaly event.
// Architectural. Minimal. Zero visual noise.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useState, useEffect } from 'react';
import { sovereignRuntime, type RuntimeMetrics } from '@/lib/SovereignRuntime';
import { useSovereignState } from '@/lib/PersistentStateEngine';
import { IS_ARCHIVE, IS_RELEASE } from '@/lib/ArchiveMode';

function pad(n: number, l = 2) { return String(n).padStart(l, '0'); }

function formatSimTime(ms: number): string {
  const s  = Math.floor(ms / 1000);
  const m  = Math.floor(s / 60);
  const h  = Math.floor(m / 60);
  const d  = Math.floor(h / 24);
  if (d > 0) return `${d}d ${pad(h % 24)}h`;
  if (h > 0) return `${pad(h)}h ${pad(m % 60)}m`;
  return `${pad(m)}m ${pad(s % 60)}s`;
}

export function InfrastructureChronicle() {
  const sys = useSovereignState();
  const [rt, setRt] = useState<RuntimeMetrics>(() => sovereignRuntime.metrics);
  const [lastAnomaly, setLastAnomaly] = useState<string | null>(null);

  useEffect(() => {
    const unsub = sovereignRuntime.subscribe(setRt);
    return () => {
      unsub();
    };
  }, []);

  // Track anomaly appearances
  useEffect(() => {
    if (sys.activeAnomalies > 0) {
      setLastAnomaly(new Date().toISOString().slice(11, 19));
    }
  }, [sys.activeAnomalies]);

  // Hide in release unless archive mode
  if (IS_RELEASE && !IS_ARCHIVE) return null;

  const thermalColor =
    rt.thermalState === 'throttled' ? '#ff1a44' :
    rt.thermalState === 'warm'      ? '#ffaa00' :
    'rgba(0,230,255,0.25)';

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-[52] pointer-events-none select-none"
      style={{
        background: 'rgba(2,4,8,0.85)',
        borderTop: '1px solid rgba(0,230,255,0.05)',
        backdropFilter: 'blur(4px)',
      }}
    >
      <div className="flex items-center justify-between px-6 py-1 font-mono">
        {/* Left: session + epoch */}
        <div className="flex items-center gap-5">
          <span className="text-[8px] tracking-[0.35em] text-white/20 uppercase">
            {rt.sessionId}
          </span>
          <span className="text-[8px] tracking-[0.3em] text-white/15 uppercase">
            EPOCH {rt.epoch}
          </span>
          <span className="text-[8px] tracking-[0.3em] text-white/15 uppercase">
            SIM {formatSimTime(rt.simulationTime)}
          </span>
        </div>

        {/* Centre: thermal state */}
        <div className="flex items-center gap-1.5">
          <div className="w-1 h-1 rounded-full" style={{ background: thermalColor }} />
          <span className="text-[8px] tracking-[0.3em] uppercase" style={{ color: thermalColor }}>
            THERMAL {rt.thermalState.toUpperCase()}
          </span>
        </div>

        {/* Right: last anomaly + archive watermark */}
        <div className="flex items-center gap-5">
          {lastAnomaly && (
            <span className="text-[8px] tracking-[0.3em] text-[#ff1a44]/50 uppercase">
              ANOMALY {lastAnomaly}
            </span>
          )}
          {IS_ARCHIVE && (
            <span className="text-[8px] tracking-[0.35em] text-white/10 uppercase">
              ARCHIVAL ARTIFACT — IMMUTABLE
            </span>
          )}
          <span className="text-[8px] tracking-[0.3em] text-white/10 uppercase">
            Q-VAULT SOVEREIGN RUNTIME
          </span>
        </div>
      </div>
    </div>
  );
}
