// ═══════════════════════════════════════════════════════════════
// DIRECTIVE ENGINE
// Adaptive cinematic restraint. Pacing governance.
// Transition dignity enforcement. Visual-noise suppression.
// Deliberately directed — never procedurally random.
// ═══════════════════════════════════════════════════════════════

import { sovereignRuntime } from './SovereignRuntime';
import { sovereignHeartbeat } from './InfrastructureHeartbeat';

// Sovereign Authority is now the permanent state for the film.
const IS_AUTHORITY = true;

export interface DirectiveState {
  // Pacing
  sceneDwellMultiplier: number;  // 0.7 (rushed) — 1.6 (extended)
  transitionGravity: number;     // 0.0 (loose) — 1.0 (locked)

  // Visual restraint
  bloomSuppression: number;      // 0.0 — 1.0 (1.0 = no suppression)
  noiseFloor: number;            // Minimum noise opacity
  vignettePresence: number;      // 0.5 — 1.2 multiplier

  // Emotional tension
  tensionVector: number;         // −1.0 (release) to +1.0 (rise)
  silenceDepth: number;          // 0.0 = ambient, 1.0 = architectural silence

  // Camera
  restraintFactor: number;       // 0.0 = expressive, 1.0 = locked sovereign

  // Thermal adaptation
  thermalDerate: number;         // 0.0 = full power, 1.0 = minimal render
}

type DirectiveListener = (s: DirectiveState) => void;

class DirectiveEngine {
  private _state: DirectiveState = {
    sceneDwellMultiplier: 1.0,
    transitionGravity: 0.7,
    bloomSuppression: 1.0,
    noiseFloor: 0.04,
    vignettePresence: 1.0,
    tensionVector: 0.0,
    silenceDepth: 0.0,
    restraintFactor: 0.6,
    thermalDerate: 0.0,
  };

  private _listeners: Set<DirectiveListener> = new Set();
  private _unsubRuntime: (() => void) | null = null;
  private _isAuthority: boolean = IS_AUTHORITY;

  // Scene-specific directives — Phase OMEGA sovereignty table
  private readonly SCENE_DIRECTIVES: Record<number, Partial<DirectiveState>> = {
    // ACT I — THE SIGNAL (curiosity, restraint)
    0:  { sceneDwellMultiplier: 1.5, restraintFactor: 0.9, silenceDepth: 0.9, tensionVector: -0.1 },
    1:  { sceneDwellMultiplier: 1.1, restraintFactor: 0.65, silenceDepth: 0.4, tensionVector: 0.4 },
    2:  { sceneDwellMultiplier: 1.2, restraintFactor: 0.75, silenceDepth: 0.5, tensionVector: 0.2 },
    3:  { sceneDwellMultiplier: 1.1, restraintFactor: 0.70, silenceDepth: 0.3, tensionVector: 0.1 },

    // ACT II — ENGINEERED OBJECT (precision, desire)
    4:  { sceneDwellMultiplier: 1.0, restraintFactor: 0.65, silenceDepth: 0.2, tensionVector: 0.2 },
    5:  { sceneDwellMultiplier: 1.1, restraintFactor: 0.70, silenceDepth: 0.2, tensionVector: 0.1 },
    6:  { sceneDwellMultiplier: 1.0, restraintFactor: 0.60, silenceDepth: 0.2, tensionVector: 0.3 },
    7:  { sceneDwellMultiplier: 1.0, restraintFactor: 0.60, silenceDepth: 0.1, tensionVector: 0.3 },

    // ACT III — FULL REVEAL (authority, power)
    8:  { sceneDwellMultiplier: 1.4, restraintFactor: 0.85, silenceDepth: 0.4, tensionVector: 0.0 }, // HERO
    9:  { sceneDwellMultiplier: 1.2, restraintFactor: 0.75, silenceDepth: 0.2, tensionVector: 0.2 },
    10: { sceneDwellMultiplier: 1.3, restraintFactor: 0.80, silenceDepth: 0.3, tensionVector: 0.0 },

    // ACT IV — THREAT (urgency, kinetic, zero restraint)
    11: { sceneDwellMultiplier: 0.75, restraintFactor: 0.20, silenceDepth: 0.0, tensionVector: 0.95 },
    12: { sceneDwellMultiplier: 0.75, restraintFactor: 0.15, silenceDepth: 0.0, tensionVector: 1.00 },
    13: { sceneDwellMultiplier: 0.75, restraintFactor: 0.18, silenceDepth: 0.0, tensionVector: 0.95 },
    14: { sceneDwellMultiplier: 0.75, restraintFactor: 0.25, silenceDepth: 0.0, tensionVector: 0.85 },
    15: { sceneDwellMultiplier: 0.85, restraintFactor: 0.40, silenceDepth: 0.1, tensionVector: 0.60 },

    // ACT V — IMMORTALITY (legendary, eternal)
    16: { sceneDwellMultiplier: 1.6, restraintFactor: 0.88, silenceDepth: 0.6, tensionVector: -0.4 },
    17: { sceneDwellMultiplier: 1.8, restraintFactor: 0.92, silenceDepth: 0.7, tensionVector: -0.6 },
    18: { sceneDwellMultiplier: 2.5, restraintFactor: 1.0,  silenceDepth: 1.0, tensionVector: -1.0 }, // SEAL — eternal
  };

  start() {
    this._unsubRuntime = sovereignRuntime.onTick((dt) => {
      const sys = sovereignHeartbeat.state;
      const rt  = sovereignRuntime.metrics;

      // Thermal derate from runtime
      const thermalDerate =
        rt.thermalState === 'throttled' ? 0.7 :
        rt.thermalState === 'warm'      ? 0.3 : 0.0;
      this._state.thermalDerate += (thermalDerate - this._state.thermalDerate) * 0.05;

      // Bloom suppression — dampen when anomalies active
      // Authority mode (Phase XVI) calibrated for institutional clarity (0.5)
      const baseSuppression = this._isAuthority ? 0.5 : 1.0;
      const targetSuppression = (sys.activeAnomalies > 0 ? 0.8 : 1.0) * baseSuppression;
      this._state.bloomSuppression += (targetSuppression - this._state.bloomSuppression) * 0.02;

      // Restraint factor — calibrated for deliberate momentum (0.7)
      const targetRestraint = this._isAuthority ? 0.7 : this._state.restraintFactor;
      this._state.restraintFactor += (targetRestraint - this._state.restraintFactor) * 0.05;

      // Noise floor — rises during silence scenes
      const targetNoise = this._state.silenceDepth > 0.5 ? 0.02 : 0.055;
      this._state.noiseFloor += (targetNoise - this._state.noiseFloor) * 0.05;

      // Vignette presence — stronger under quantum pressure
      const targetVignette = 1.0 + sys.quantumPressure * 0.15;
      this._state.vignettePresence += (targetVignette - this._state.vignettePresence) * 0.04;

      this._listeners.forEach(fn => fn(this._state));
    });
  }

  stop() {
    this._unsubRuntime?.();
  }

  applySceneDirective(scene: number) {
    const directive = this.SCENE_DIRECTIVES[scene] ?? {};
    Object.assign(this._state, directive);
    this._listeners.forEach(fn => fn(this._state));
  }

  subscribe(fn: DirectiveListener) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  get state() { return this._state; }
}

export const directiveEngine = new DirectiveEngine();

if (typeof window !== 'undefined') {
  directiveEngine.start();
}
