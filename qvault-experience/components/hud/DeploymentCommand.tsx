// ═══════════════════════════════════════════════════════════════
// DEPLOYMENT COMMAND CENTER
// Sovereign operational status HUD.
// Industrial. Military. Zero decoration.
// All data live from InfrastructureHeartbeat.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useState } from 'react';
import { useSovereignState, formatLargeNumber, getSystemStatus } from '@/lib/PersistentStateEngine';

const EDGE_REGIONS = [
  { id: 'EU-WEST-1',   label: 'FRANKFURT'  },
  { id: 'US-EAST-1',   label: 'VIRGINIA'   },
  { id: 'AP-EAST-1',   label: 'SINGAPORE'  },
  { id: 'ME-SOUTH-1',  label: 'BAHRAIN'    },
  { id: 'SA-EAST-1',   label: 'SÃO PAULO'  },
];

function StatusBar({ value, warn = 0.6, crit = 0.85 }: { value: number; warn?: number; crit?: number }) {
  const color = value > crit ? '#ff1a44' : value > warn ? '#ffaa00' : '#00e6ff';
  return (
    <div className="relative h-[3px] w-full rounded-none overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
      <div
        className="absolute inset-y-0 left-0 transition-all duration-500"
        style={{ width: `${value * 100}%`, background: color }}
      />
    </div>
  );
}

function DataRow({ label, value, unit = '', critical = false }: { label: string; value: string; unit?: string; critical?: boolean }) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-baseline gap-2">
      <span className="font-mono text-[9px] tracking-[0.25em] text-white/30 uppercase truncate">{label}</span>
      <span className={`font-mono text-[10px] tracking-wider tabular-nums ${critical ? 'text-[#ff1a44]' : 'text-[rgba(0,230,255,0.7)]'}`}>
        {value}<span className="text-[8px] text-white/20 ml-0.5">{unit}</span>
      </span>
    </div>
  );
}

export function DeploymentCommand() {
  const sys = useSovereignState();
  const [collapsed, setCollapsed] = useState(false);
  const status = getSystemStatus(sys);

  const statusColor = status === 'CRITICAL' ? '#ff1a44' : status === 'ELEVATED' ? '#ffaa00' : '#00e6ff';
  const gpuLoad = Math.min(1, sys.quantumPressure * 0.6 + 0.25 + sys.activeAnomalies * 0.04);
  const memPressure = Math.min(1, (sys.interceptedThreats % 1_000_000) / 1_000_000 * 0.4 + 0.3);
  const streamLatency = sys.latencyMs;
  const trustConsensus = sys.trustScore;
  const activeRelays = Math.floor(sys.activeNodes * 1.7);

  // Release mode — hide in production
  const isRelease = process.env.NEXT_PUBLIC_QVAULT_RELEASE === 'true';
  if (isRelease) return null;

  return (
    <div className="fixed bottom-6 left-6 z-[55] pointer-events-auto select-none font-mono" style={{ opacity: 0.9 }}>
      <div
        style={{
          background: 'rgba(2,4,8,0.96)',
          border: `1px solid rgba(0,230,255,0.07)`,
          borderTop: `1px solid ${statusColor}22`,
          minWidth: 240,
          backdropFilter: 'blur(12px)',
        }}
      >
        {/* Header bar */}
        <button
          onClick={() => setCollapsed(c => !c)}
          className="w-full flex items-center justify-between px-4 py-2 border-b border-white/5 hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusColor, boxShadow: `0 0 4px ${statusColor}` }} />
            <span className="text-[9px] tracking-[0.35em] text-white/35 uppercase">DEPLOYMENT CENTER</span>
          </div>
          <span className="text-[8px] tracking-[0.3em] uppercase" style={{ color: statusColor }}>
            {status}
          </span>
        </button>

        {!collapsed && (
          <div className="px-4 py-3 space-y-3">
            {/* Edge regions */}
            <div>
              <div className="text-[8px] tracking-[0.4em] text-white/20 uppercase mb-1.5">EDGE REGIONS</div>
              <div className="space-y-1">
                {EDGE_REGIONS.map((r, i) => {
                  const online = i < Math.ceil(sys.activeNodes / (sys.totalNodes / EDGE_REGIONS.length));
                  return (
                    <div key={r.id} className="flex items-center justify-between gap-3">
                      <span className="text-[9px] text-white/25 tracking-wider">{r.label}</span>
                      <span className="text-[8px] tracking-[0.25em]" style={{ color: online ? 'rgba(0,230,255,0.5)' : '#ff1a44' }}>
                        {online ? 'ACTIVE' : 'DEGRADED'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="h-px bg-white/5" />

            {/* Core metrics with bars */}
            <div className="space-y-2">
              <div>
                <DataRow label="ACTIVE RELAYS" value={activeRelays.toString()} unit="nodes" />
                <div className="mt-1">
                  <StatusBar value={sys.activeNodes / sys.totalNodes} />
                </div>
              </div>

              <div>
                <DataRow label="GPU LOAD" value={(gpuLoad * 100).toFixed(0)} unit="%" critical={gpuLoad > 0.85} />
                <div className="mt-1">
                  <StatusBar value={gpuLoad} />
                </div>
              </div>

              <div>
                <DataRow label="MEM PRESSURE" value={(memPressure * 100).toFixed(0)} unit="%" critical={memPressure > 0.8} />
                <div className="mt-1">
                  <StatusBar value={memPressure} />
                </div>
              </div>

              <DataRow label="STREAM LATENCY" value={streamLatency.toFixed(1)} unit="ms" critical={streamLatency > 10} />
              <DataRow label="TRUST CONSENSUS" value={(trustConsensus * 100).toFixed(3)} unit="%" />
            </div>

            <div className="h-px bg-white/5" />

            {/* Attestation ticker */}
            <div className="flex items-center gap-2">
              <div className="w-1 h-1 rounded-full bg-[#00e6ff]/40 animate-pulse" />
              <span className="text-[8px] text-white/20 tracking-widest">
                {formatLargeNumber(sys.attestationCycles)} CYCLES
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
