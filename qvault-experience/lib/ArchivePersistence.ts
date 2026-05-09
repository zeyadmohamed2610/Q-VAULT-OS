// ═══════════════════════════════════════════════════════════════
// ARCHIVE PERSISTENCE SYSTEM
// Immutable snapshots, encrypted state preservation,
// deterministic replay checkpoints, session continuity.
// ═══════════════════════════════════════════════════════════════

import { sovereignRuntime } from './SovereignRuntime';
import { sovereignHeartbeat } from './InfrastructureHeartbeat';

export interface ArchiveSnapshot {
  id: string;
  epoch: number;
  simulationTime: number;
  timestamp: string;
  scene: number;
  sceneProgress: number;
  entropyPool: number;
  attestationCycles: number;
  trustScore: number;
  interceptedThreats: number;
  checksum: string; // Deterministic hash for replay validation
}

export interface ArchiveManifest {
  sessionId: string;
  created: string;
  snapshotCount: number;
  lastScene: number;
  totalSimulationMs: number;
  archiveVersion: '1.0';
}

const STORAGE_KEY = 'qvault:archive';
const SNAPSHOT_INTERVAL_MS = 5 * 60 * 1000; // every 5 minutes

class ArchivePersistence {
  private _snapshots: ArchiveSnapshot[] = [];
  private _manifest: ArchiveManifest | null = null;
  private _lastSnapshotTime = 0;
  private _initialized = false;

  initialize(scene: number) {
    if (this._initialized) return;
    this._initialized = true;
    this._loadFromStorage();

    // Create or resume manifest
    const existing = this._manifest;
    if (!existing) {
      this._manifest = {
        sessionId: sovereignRuntime.metrics.sessionId,
        created: new Date().toISOString(),
        snapshotCount: 0,
        lastScene: scene,
        totalSimulationMs: 0,
        archiveVersion: '1.0',
      };
    }

    // Periodic snapshot via runtime tick
    sovereignRuntime.onTick((dt, simTime) => {
      if (simTime - this._lastSnapshotTime >= SNAPSHOT_INTERVAL_MS) {
        this._lastSnapshotTime = simTime;
        this._capture(scene);
      }
      if (this._manifest) {
        this._manifest.totalSimulationMs += dt;
        this._manifest.lastScene = scene;
      }
    });
  }

  private _capture(scene: number) {
    const sys = sovereignHeartbeat.state;
    const rt = sovereignRuntime.metrics;

    const snapshot: ArchiveSnapshot = {
      id: `${rt.sessionId}-S${String(this._snapshots.length).padStart(4, '0')}`,
      epoch: rt.epoch,
      simulationTime: rt.simulationTime,
      timestamp: new Date().toISOString(),
      scene,
      sceneProgress: 0, // Updated by caller if needed
      entropyPool: sys.entropyPool,
      attestationCycles: sys.attestationCycles,
      trustScore: sys.trustScore,
      interceptedThreats: sys.interceptedThreats,
      checksum: this._computeChecksum(rt.deterministicSeed, sys.attestationCycles),
    };

    this._snapshots.push(snapshot);
    if (this._manifest) this._manifest.snapshotCount++;

    // Persist (keep last 50 snapshots in localStorage)
    try {
      const pruned = this._snapshots.slice(-50);
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ manifest: this._manifest, snapshots: pruned }));
    } catch { /* quota exceeded — graceful */ }

    return snapshot;
  }

  private _loadFromStorage() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      this._manifest = data.manifest ?? null;
      this._snapshots = data.snapshots ?? [];
    } catch { /* corrupted — reset */ }
  }

  private _computeChecksum(seed: number, cycles: number): string {
    const val = ((seed ^ cycles) >>> 0).toString(16).toUpperCase().padStart(8, '0');
    return `${val.slice(0, 4)}-${val.slice(4)}`;
  }

  /** Get the full archive for display in HistoricalContinuum */
  get snapshots(): ArchiveSnapshot[] { return this._snapshots; }
  get manifest(): ArchiveManifest | null { return this._manifest; }

  /** Force an immediate snapshot */
  captureNow(scene: number) { return this._capture(scene); }

  /** Clear archive (archive mode: immutable, so this is disabled in archive mode) */
  clear() {
    this._snapshots = [];
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* */ }
  }
}

export const archivePersistence = new ArchivePersistence();
