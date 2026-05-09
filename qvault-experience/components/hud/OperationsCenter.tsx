// ═══════════════════════════════════════════════════════════════
// ARCHIVAL OPERATIONS CENTER — Phase XVI
// Command-grade operational room aesthetic.
// Operator consoles. Deployment authority feed. Archival logs.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useSovereignState } from '@/lib/PersistentStateEngine';
import { useEffect, useState } from 'react';

// Sovereign state constants
const IS_AUTHORITY = true;

export function OperationsCenter() {
  const sys = useSovereignState();
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const newLog = `AUTH_EVENT: ${Math.random().toString(36).slice(2, 10).toUpperCase()} // NODE_${Math.floor(Math.random() * 99)} // COMMITTED`;
      setLogs(prev => [newLog, ...prev].slice(0, 12)); // 12 lines — readable at demo distance
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed inset-0 z-[120] bg-black pointer-events-none select-none font-mono text-white/40 p-12 overflow-hidden">
      {/* ── Background Grid (Very Subtle) ── */}
      <div className="absolute inset-0 opacity-[0.03] bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:50px_50px]" />

      {/* ── Top Command Bar ── */}
      <div className="relative flex justify-between items-start border-b border-white/5 pb-4 mb-8">
        <div>
          <div className="text-[12px] text-white/80 tracking-[0.6em] mb-1">OPERATIONS_CENTER_BETA</div>
          <div className="text-[9px] text-white/20 tracking-[0.4em]">DEPLOYMENT_AUTHORITY: VERIFIED</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-white/60 mb-1">SESSION_EPOCH: {Math.floor(sys.uptimeSeconds / 3600)}</div>
          <div className="text-[9px] text-white/20">UPTIME: {Math.floor(sys.uptimeSeconds / 60)}M {Math.floor(sys.uptimeSeconds % 60)}S</div>
        </div>
      </div>

      {/* ── Main Content Grid ── */}
      <div className="relative grid grid-cols-12 gap-8 h-[calc(100%-150px)]">
        
        {/* Left Console: Event Stream */}
        <div className="col-span-4 flex flex-col border-r border-white/5 pr-8">
          <div className="text-[10px] text-white/30 mb-4 tracking-[0.3em]">IMMUTABLE_LOG_STREAM</div>
          <div className="flex-1 overflow-hidden">
            {logs.map((log, i) => (
              <div key={i} className="text-[11px] mb-2.5 leading-relaxed whitespace-nowrap overflow-hidden text-ellipsis">
                <span className="text-white/10 mr-4">[{new Date().toLocaleTimeString()}]</span>
                <span className={i === 0 ? 'text-white/70' : 'text-white/30'}>{log}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Center Console: Visual Authority */}
        <div className="col-span-4 flex flex-col items-center justify-center border-r border-white/5">
          <div className="w-48 h-48 border border-white/5 flex items-center justify-center relative">
            <div className="absolute inset-4 border border-white/10 animate-pulse" />
            <div className="text-[24px] tracking-[0.4em] font-light text-white/90 mb-1">
              CORE
            </div>
            <div className="text-[48px] text-white/10 font-light">{sys.activeNodes}</div>
          </div>
          <div className="mt-8 text-[9px] text-white/20 tracking-[0.5em]">QUORUM_ESTABLISHED</div>
        </div>

        {/* Right Console: System Metrics */}
        <div className="col-span-4 flex flex-col pl-8">
          <div className="text-[10px] text-white/30 mb-4 tracking-[0.3em]">GOVERNANCE_STATE</div>
          <div className="space-y-6">
            <div>
              <div className="flex justify-between text-[9px] mb-1">
                <span>CONSENSUS_STABILITY</span>
                <span>{(sys.entropyPool * 100).toFixed(2)}%</span>
              </div>
              <div className="h-0.5 bg-white/5 relative">
                <div className="absolute inset-y-0 left-0 bg-white/40" style={{ width: `${sys.entropyPool * 100}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-[9px] mb-1">
                <span>NODE_SYNC_VELOCITY</span>
                <span>0.88 MS</span>
              </div>
              <div className="h-0.5 bg-white/5" />
            </div>
          </div>

          <div className="mt-auto pt-8 border-t border-white/5">
            <div className="text-[10px] text-white/30 mb-4 tracking-[0.3em]">ARCHIVE_REPLICATION</div>
            <div className="grid grid-cols-8 gap-2">
              {[...Array(24)].map((_, i) => (
                <div key={i} className={`h-1 ${i < (Math.floor(sys.uptimeSeconds / 60) % 24) ? 'bg-white/40' : 'bg-white/5'}`} />
              ))}
            </div>
          </div>
        </div>

      </div>

      {/* ── Bottom Authority Status ── */}
      <div className="absolute bottom-12 left-12 right-12 flex justify-between items-end">
        <div className="text-[8px] tracking-[0.4em] text-white/10 max-w-xs">
          THIS CONSOLE IS UNDER DIRECT SOVEREIGN AUTHORITY. UNAUTHORIZED ACCESS IS LOGGED TO THE IMMUTABLE FABRIC.
        </div>
        <div className="flex gap-12">
          <div className="text-right">
            <div className="text-[8px] text-white/10 uppercase mb-1">ENCLAVE_STATE</div>
            <div className="text-[12px] text-white/60 tracking-widest">SECURE_ROOT</div>
          </div>
          <div className="text-right">
            <div className="text-[8px] text-white/10 uppercase mb-1">REPLICATION</div>
            <div className="text-[12px] text-white/60 tracking-widest">IMMUTABLE</div>
          </div>
        </div>
      </div>
    </div>
  );
}
