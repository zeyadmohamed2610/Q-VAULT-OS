// ═══════════════════════════════════════════════════════════════
// SOVEREIGN RUNTIME
// Global timing authority for the entire Q-VAULT system.
// Deterministic simulation ticks, synchronized cinematic clocks,
// adaptive thermal scheduling, frame pacing normalization.
// This is not a website render loop — it is an infrastructure runtime.
// ═══════════════════════════════════════════════════════════════

export interface RuntimeMetrics {
  sessionId: string;           // Deterministic per-session UUID
  epoch: number;               // Simulation epoch (increments each full cycle)
  simulationTime: number;      // High-precision simulation clock (ms)
  realTime: number;            // Wall-clock time (ms)
  framePace: number;           // Target frame interval (ms)
  thermalState: 'nominal' | 'warm' | 'throttled';
  tickAccumulator: number;     // For fixed-step physics integration
  deterministicSeed: number;   // PRNG seed for reproducible simulation
  hardwarePurity: number;      // Institutional perception metric
  thermalSymmetry: number;     // Operational balance metric
}

type RuntimeListener = (metrics: RuntimeMetrics) => void;

class SovereignRuntime {
  private _metrics: RuntimeMetrics;
  private _listeners: Set<RuntimeListener> = new Set();
  private _tickListeners: Set<(dt: number, sim: number) => void> = new Set();
  private _intervalId: ReturnType<typeof setInterval> | null = null;
  private _startReal: number;
  private _lastTick: number;
  private _frameTimings: number[] = [];

  // Fixed simulation tick rate: 20Hz (50ms) — deterministic, decoupled from RAF
  private readonly TICK_MS = 50;
  private readonly THERMAL_WINDOW = 30; // samples

  constructor() {
    this._startReal = Date.now();
    this._lastTick = this._startReal;

    // Session ID — cryptographically styled, deterministic per load
    const sessionSeed = this._startReal.toString(36).toUpperCase().padStart(8, '0');
    const sessionId = `QVRT-${sessionSeed.slice(0, 4)}-${sessionSeed.slice(4)}`;

    this._metrics = {
      sessionId,
      epoch: 0,
      simulationTime: 0,
      realTime: 0,
      framePace: this.TICK_MS,
      thermalState: 'nominal',
      tickAccumulator: 0,
      deterministicSeed: this._startReal % 0xFFFF,
      hardwarePurity: 0.9999,
      thermalSymmetry: 0.9850,
    };
  }

  start() {
    if (this._intervalId) return;
    this._lastTick = Date.now();

    this._intervalId = setInterval(() => {
      const now = Date.now();
      const dt = now - this._lastTick;
      this._lastTick = now;

      // Accumulate frame timings for thermal detection
      this._frameTimings.push(dt);
      if (this._frameTimings.length > this.THERMAL_WINDOW) {
        this._frameTimings.shift();
      }

      // Update simulation clock
      this._metrics.simulationTime += dt;
      this._metrics.realTime = now - this._startReal;
      this._metrics.framePace = dt;

      // Epoch — every 60 minutes of simulation time
      this._metrics.epoch = Math.floor(this._metrics.simulationTime / (60 * 60 * 1000));

      // Thermal assessment
      if (this._frameTimings.length >= 10) {
        const avg = this._frameTimings.reduce((a, b) => a + b, 0) / this._frameTimings.length;
        if (avg > this.TICK_MS * 3.0) this._metrics.thermalState = 'throttled';
        else if (avg > this.TICK_MS * 1.8) this._metrics.thermalState = 'warm';
        else this._metrics.thermalState = 'nominal';
        
        // Drifting institutional metrics for realism
        this._metrics.hardwarePurity = 0.9998 + (Math.random() * 0.00015);
        this._metrics.thermalSymmetry = 0.9840 + (Math.random() * 0.0020);
      }

      // Advance deterministic seed (LCG — reproducible)
      this._metrics.deterministicSeed = (this._metrics.deterministicSeed * 1664525 + 1013904223) & 0xFFFFFFFF;

      // Notify frame listeners
      this._tickListeners.forEach(fn => fn(dt, this._metrics.simulationTime));
      this._listeners.forEach(fn => fn(this._metrics));
    }, this.TICK_MS);
  }

  stop() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  /** Subscribe to metric updates */
  subscribe(fn: RuntimeListener) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  /** Subscribe to simulation ticks (dt in ms, simTime in ms) */
  onTick(fn: (dt: number, simTime: number) => void) {
    this._tickListeners.add(fn);
    return () => this._tickListeners.delete(fn);
  }

  get metrics() { return this._metrics; }

  /** Deterministic random [0,1) using LCG seed */
  deterministicRandom(): number {
    this._metrics.deterministicSeed = (this._metrics.deterministicSeed * 1664525 + 1013904223) & 0xFFFFFFFF;
    return (this._metrics.deterministicSeed >>> 0) / 0x100000000;
  }
}

// Singleton — one runtime for the entire session
export const sovereignRuntime = new SovereignRuntime();

// Auto-start in browser
if (typeof window !== 'undefined') {
  sovereignRuntime.start();
}
