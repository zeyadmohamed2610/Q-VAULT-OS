// ═══════════════════════════════════════════════════════════════
// DISPLAY ORCHESTRATOR
// Multi-display synchronization, panoramic installation support,
// keynote stage routing, deterministic timing sync.
// ═══════════════════════════════════════════════════════════════

import { sovereignRuntime } from './SovereignRuntime';

export type DisplayRole = 'primary' | 'auxiliary-telemetry' | 'auxiliary-map' | 'control';

export interface DisplayConfig {
  role: DisplayRole;
  displayId: string;
  syncGroup: string;
  offsetMs: number;        // Timing offset for panoramic sync
  aspectRatio: string;     // e.g. '16:9' | '21:9' | '9:16' (vertical)
  isVertical: boolean;
}

export interface SyncFrame {
  simTime: number;
  scene: number;
  frameId: number;
  sessionId: string;
}

type SyncListener = (frame: SyncFrame) => void;

class DisplayOrchestrator {
  private _config: DisplayConfig;
  private _syncListeners: Set<SyncListener> = new Set();
  private _channel: BroadcastChannel | null = null;
  private _frameId = 0;

  constructor() {
    // Detect role from URL param: ?display=auxiliary-telemetry
    const role = this._detectRole();
    const aspectRatio = this._detectAspectRatio();

    this._config = {
      role,
      displayId: this._generateDisplayId(),
      syncGroup: 'qvault-default',
      offsetMs: 0,
      aspectRatio,
      isVertical: window.innerHeight > window.innerWidth,
    };
  }

  initialize() {
    // BroadcastChannel for same-origin multi-window sync
    if (typeof BroadcastChannel !== 'undefined') {
      this._channel = new BroadcastChannel('qvault:display-sync');
      this._channel.onmessage = (e) => {
        if (e.data?.type === 'sync-frame') {
          const frame = e.data.frame as SyncFrame;
          this._syncListeners.forEach(fn => fn(frame));
        }
      };
    }

    // Primary display broadcasts sync frames
    if (this._config.role === 'primary') {
      sovereignRuntime.onTick((_, simTime) => {
        const frame: SyncFrame = {
          simTime,
          scene: 0, // Updated externally
          frameId: ++this._frameId,
          sessionId: sovereignRuntime.metrics.sessionId,
        };
        this._channel?.postMessage({ type: 'sync-frame', frame });
      });
    }
  }

  broadcastScene(scene: number) {
    if (this._config.role !== 'primary') return;
    const frame: SyncFrame = {
      simTime: sovereignRuntime.metrics.simulationTime,
      scene,
      frameId: ++this._frameId,
      sessionId: sovereignRuntime.metrics.sessionId,
    };
    this._channel?.postMessage({ type: 'scene-change', frame });
  }

  onSync(fn: SyncListener) {
    this._syncListeners.add(fn);
    return () => this._syncListeners.delete(fn);
  }

  get config() { return this._config; }
  get isPrimary() { return this._config.role === 'primary'; }

  private _detectRole(): DisplayRole {
    if (typeof window === 'undefined') return 'primary';
    const params = new URLSearchParams(window.location.search);
    const role = params.get('display') as DisplayRole | null;
    return role ?? 'primary';
  }

  private _detectAspectRatio(): string {
    if (typeof window === 'undefined') return '16:9';
    const r = window.innerWidth / window.innerHeight;
    if (r > 2.0) return '21:9';
    if (r < 0.8) return '9:16';
    return '16:9';
  }

  private _generateDisplayId(): string {
    return `DISP-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
  }

  destroy() {
    this._channel?.close();
  }
}

// Lazy singleton — only instantiate in browser
let _orchestrator: DisplayOrchestrator | null = null;

export function getDisplayOrchestrator(): DisplayOrchestrator {
  if (!_orchestrator && typeof window !== 'undefined') {
    _orchestrator = new DisplayOrchestrator();
    _orchestrator.initialize();
  }
  return _orchestrator!;
}
