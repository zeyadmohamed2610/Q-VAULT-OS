// ═══════════════════════════════════════════════════════════════
// TELEMETRY CORE
// Persistent classified HUD — live infrastructure diagnostics.
// Industrial. Minimal. High-authority. Always present.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useSovereignState, formatUptime, formatLargeNumber, getSystemStatus } from '@/lib/PersistentStateEngine';
import { useExperienceStore } from '@/lib/store';
import { useEffect, useState } from 'react';

function SparkBar({ value, color = '#00e6ff' }: { value: number; color?: string }) {
  const bars = 8;
  const filled = Math.round(value * bars);
  return (
    <span className="inline-flex gap-[2px] items-end">
      {Array.from({ length: bars }).map((_, i) => (
        <span
          key={i}
          style={{
            display: 'inline-block',
            width: 3,
            height: 6 + (i % 3) * 2,
            background: i < filled ? color : 'rgba(255,255,255,0.08)',
            transition: 'background 0.3s',
          }}
        />
      ))}
    </span>
  );
}

function MetricRow({
  label,
  value,
  unit = '',
  danger = false,
}: {
  label: string;
  value: string;
  unit?: string;
  danger?: boolean;
}) {
  return (
    <div className="flex justify-between items-baseline gap-4">
      <span className="text-white/30 text-[9px] tracking-[0.2em] uppercase">{label}</span>
      <span
        className="text-[10px] font-mono tracking-wider tabular-nums"
        style={{ color: danger ? '#ff4466' : 'rgba(0,230,255,0.75)' }}
      >
        {value}
        {unit && <span className="text-white/20 ml-0.5 text-[8px]">{unit}</span>}
      </span>
    </div>
  );
}

export function TelemetryCore() {
  const sys = useSovereignState();
  const activeScene = useExperienceStore((s) => s.activeScene);
  const status = getSystemStatus(sys);
  const [pulse, setPulse] = useState(false);

  // Heartbeat flash every attestation cycle
  useEffect(() => {
    const t = setInterval(() => {
      setPulse(true);
      setTimeout(() => setPulse(false), 120);
    }, 1400);
    return () => clearInterval(t);
  }, []);

  // Hide during Intro (scene -1) and seal (scene 12 progress >0.9)
  const hidden = activeScene < 0;
  if (hidden) return null;

  const isCritical = status === 'CRITICAL';
  const isElevated = status === 'ELEVATED';
  const statusColor = isCritical ? '#ff1a44' : isElevated ? '#ffaa00' : '#00e6ff';

  return (
    <div
      className="fixed top-4 right-14 z-[50] pointer-events-none select-none"
      style={{ opacity: 0.85 }}
    >
      <div
        className="font-mono text-white"
        style={{
          background: 'rgba(2,4,8,0.92)',
          border: `1px solid rgba(0,230,255,0.08)`,
          borderLeft: `1px solid ${statusColor}30`,
          padding: '10px 14px',
          minWidth: 200,
          backdropFilter: 'blur(8px)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-[8px] tracking-[0.4em] text-white/25 uppercase">SYS/TELEMETRY</span>
          <span
            className="text-[8px] tracking-[0.3em] uppercase font-mono"
            style={{ color: statusColor }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 mb-[1px]"
              style={{
                background: statusColor,
                opacity: pulse ? 1 : 0.5,
                transition: 'opacity 0.1s',
                display: 'inline-block',
              }}
            />
            {status}
          </span>
        </div>

        {/* Divider */}
        <div className="h-px bg-white/5 mb-3" />

        {/* Core metrics */}
        <div className="flex flex-col gap-1.5">
          <MetricRow label="UPTIME" value={formatUptime(sys.uptimeSeconds)} />
          <MetricRow label="ATTEST" value={formatLargeNumber(sys.attestationCycles)} unit="/cyc" />
          <MetricRow
            label="INTEGRITY"
            value={(sys.cryptoIntegrity * 100).toFixed(2)}
            unit="%"
            danger={sys.cryptoIntegrity < 0.96}
          />
          <MetricRow label="LATENCY" value={sys.latencyMs.toFixed(1)} unit="ms" />
        </div>

        <div className="h-px bg-white/5 my-3" />

        {/* Entropy pool */}
        <div className="flex justify-between items-center mb-1">
          <span className="text-[9px] tracking-[0.2em] text-white/30 uppercase">ENTROPY</span>
          <SparkBar value={sys.entropyPool} />
        </div>

        {/* Quantum pressure */}
        <div className="flex justify-between items-center">
          <span className="text-[9px] tracking-[0.2em] text-white/30 uppercase">Q-PRESS</span>
          <SparkBar
            value={sys.quantumPressure}
            color={sys.quantumPressure > 0.5 ? '#ff4466' : '#00e6ff'}
          />
        </div>

        <div className="h-px bg-white/5 my-3" />

        {/* Node count */}
        <div className="flex justify-between items-baseline">
          <span className="text-[9px] tracking-[0.2em] text-white/30 uppercase">NODES</span>
          <span className="text-[10px] font-mono text-[rgba(0,230,255,0.75)]">
            {sys.activeNodes}
            <span className="text-white/20">/{sys.totalNodes}</span>
          </span>
        </div>

        {/* Anomalies — only shown if active */}
        {sys.activeAnomalies > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <span
              className="text-[9px] tracking-[0.25em] uppercase animate-pulse"
              style={{ color: '#ff1a44' }}
            >
              ⚠ {sys.activeAnomalies} ANOMAL{sys.activeAnomalies > 1 ? 'IES' : 'Y'}
            </span>
          </div>
        )}

        {/* Intercepted threats — bottom strip */}
        <div className="mt-3 pt-2 border-t border-white/5">
          <div className="text-[8px] text-white/15 tracking-widest uppercase">
            THREATS NEUTRALIZED
          </div>
          <div className="text-[10px] font-mono" style={{ color: 'rgba(0,230,255,0.4)' }}>
            {formatLargeNumber(sys.interceptedThreats)}
          </div>
        </div>
      </div>
    </div>
  );
}
