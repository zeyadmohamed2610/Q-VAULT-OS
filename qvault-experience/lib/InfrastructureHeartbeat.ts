// ═══════════════════════════════════════════════════════════════
// INFRASTRUCTURE HEARTBEAT
// The central nervous system of the sovereign simulation.
// All live state derives from here. Zero allocations per tick.
// ═══════════════════════════════════════════════════════════════

export interface SovereignSystemState {
  // Core vitals
  uptimeSeconds: number;
  attestationCycles: number;
  entropyPool: number;         // 0.0 – 1.0  (QRNG saturation)
  trustScore: number;          // 0.0 – 1.0
  governancePropagation: number; // 0.0 – 1.0

  // Network state
  activeNodes: number;
  totalNodes: number;
  packetLoss: number;          // 0.0 – 1.0
  latencyMs: number;

  // Threat telemetry
  quantumPressure: number;     // 0.0 – 1.0
  interceptedThreats: number;
  activeAnomalies: number;

  // Environmental
  entropyDriftHz: number;      // ~0.3 – 3.0
  keystoreTemp: number;        // Kelvin, target 1.2K
  cryptoIntegrity: number;     // 0.0 – 1.0
  hardwarePurity: number;      // 0.0 - 1.0
  thermalSymmetry: number;     // 0.0 - 1.0
}

class InfrastructureHeartbeat {
  private _state: SovereignSystemState;
  private _startTime = Date.now();
  private _tick = 0;
  private _subscribers: Set<(state: SovereignSystemState) => void> = new Set();
  private _intervalId: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this._state = {
      uptimeSeconds: 0,
      attestationCycles: 78_419_223, // Already deep in operation
      entropyPool: 0.94,
      trustScore: 0.99,
      governancePropagation: 0.97,
      activeNodes: 247,
      totalNodes: 256,
      packetLoss: 0.001,
      latencyMs: 3.2,
      quantumPressure: 0.08,
      interceptedThreats: 4_891_042,
      activeAnomalies: 0,
      entropyDriftHz: 0.44,
      keystoreTemp: 1.2,
      cryptoIntegrity: 1.0,
      hardwarePurity: 0.9999,
      thermalSymmetry: 0.9850,
    };
  }

  start() {
    if (this._intervalId) return;
    this._startTime = Date.now();

    // 100ms tick — fast enough to feel alive, light enough for 60fps
    this._intervalId = setInterval(() => this._update(), 100);
  }

  stop() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  subscribe(fn: (state: SovereignSystemState) => void) {
    this._subscribers.add(fn);
    return () => this._subscribers.delete(fn);
  }

  get state(): SovereignSystemState {
    return this._state;
  }

  private _update() {
    this._tick++;
    const s = this._state;

    // Uptime
    s.uptimeSeconds = (Date.now() - this._startTime) / 1000;

    // Attestation cycles — count up at ~850/sec
    s.attestationCycles += 85;

    // Entropy pool — oscillates, replenished periodically
    s.entropyPool += (Math.random() - 0.5) * 0.003;
    if (s.entropyPool < 0.85) s.entropyPool += 0.01; // QRNG refill
    s.entropyPool = Math.min(1.0, Math.max(0.8, s.entropyPool));

    // Trust score — very stable, micro fluctuations
    s.trustScore += (Math.random() - 0.5) * 0.001;
    s.trustScore = Math.min(1.0, Math.max(0.96, s.trustScore));

    // Governance propagation — slower oscillation
    if (this._tick % 20 === 0) {
      s.governancePropagation += (Math.random() - 0.5) * 0.005;
      s.governancePropagation = Math.min(1.0, Math.max(0.92, s.governancePropagation));
    }

    // Node activity — occasional node drop/recovery
    if (this._tick % 50 === 0) {
      const delta = Math.floor((Math.random() - 0.4) * 3); // Slight bias toward stability
      s.activeNodes = Math.min(s.totalNodes, Math.max(240, s.activeNodes + delta));
    }

    // Latency — slight jitter
    s.latencyMs += (Math.random() - 0.5) * 0.5;
    s.latencyMs = Math.max(1.2, Math.min(12.0, s.latencyMs));

    // Quantum pressure — slow oscillation with rare spikes
    s.quantumPressure += (Math.random() - 0.52) * 0.003;
    if (this._tick % 300 === 0 && Math.random() > 0.7) {
      s.quantumPressure += 0.15; // Threat surge
    }
    s.quantumPressure = Math.max(0.02, Math.min(0.95, s.quantumPressure));

    // Intercepted threats — accumulate with quantum pressure
    s.interceptedThreats += Math.floor(s.quantumPressure * 12);

    // Active anomalies — correlated with quantum pressure
    if (this._tick % 30 === 0) {
      s.activeAnomalies = s.quantumPressure > 0.3
        ? Math.floor(s.quantumPressure * 8)
        : 0;
    }

    // Entropy drift
    s.entropyDriftHz += (Math.random() - 0.5) * 0.05;
    s.entropyDriftHz = Math.max(0.3, Math.min(3.0, s.entropyDriftHz));

    // Keystore temperature — near-absolute zero stability
    s.keystoreTemp += (Math.random() - 0.5) * 0.003;
    s.keystoreTemp = Math.max(1.18, Math.min(1.24, s.keystoreTemp));

    // Crypto integrity — near-perfect, degrades under anomalies
    const targetIntegrity = s.activeAnomalies > 0
      ? 1.0 - (s.activeAnomalies * 0.008)
      : 1.0;
    s.cryptoIntegrity += (targetIntegrity - s.cryptoIntegrity) * 0.1;
    
    // Perception metrics drift
    s.hardwarePurity = 0.9998 + (Math.random() * 0.00015);
    s.thermalSymmetry = 0.9840 + (Math.random() * 0.0020);

    // Notify subscribers
    this._subscribers.forEach(fn => fn(s));
  }
}

// Singleton — one heartbeat for the entire session
export const sovereignHeartbeat = new InfrastructureHeartbeat();
