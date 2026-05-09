// ═══════════════════════════════════════════════════════════════
// PERSISTENT STATE ENGINE
// React hook bridging InfrastructureHeartbeat into component tree.
// ═══════════════════════════════════════════════════════════════

import { useEffect, useState } from 'react';
import { sovereignHeartbeat, type SovereignSystemState } from './InfrastructureHeartbeat';

// Initialize once at module level — starts immediately
if (typeof window !== 'undefined') {
  sovereignHeartbeat.start();
}

export function useSovereignState(): SovereignSystemState {
  const [state, setState] = useState<SovereignSystemState>(() => sovereignHeartbeat.state);

  useEffect(() => {
    const unsub = sovereignHeartbeat.subscribe(setState);
    return () => {
      unsub();
    };
  }, []);

  return state;
}

// Formatted helpers for display
export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

export function formatLargeNumber(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function getSystemStatus(state: SovereignSystemState): 'NOMINAL' | 'ELEVATED' | 'CRITICAL' {
  if (state.activeAnomalies > 5 || state.cryptoIntegrity < 0.95) return 'CRITICAL';
  if (state.quantumPressure > 0.4 || state.activeAnomalies > 0) return 'ELEVATED';
  return 'NOMINAL';
}
