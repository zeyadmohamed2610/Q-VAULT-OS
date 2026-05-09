// ═══════════════════════════════════════════════════════════════
// ADAPTIVE CINEMA DIRECTOR
// Autonomous orchestration of scene pacing, camera tension,
// and emotional rhythm. Not automated — directed.
// ═══════════════════════════════════════════════════════════════

import { sovereignHeartbeat } from './InfrastructureHeartbeat';
import { useExperienceStore } from './store';

export interface DirectorState {
  tensionLevel: number;       // 0.0 – 1.0
  exposurePacing: number;     // multiplier on PostFX
  cameraRestraint: number;    // 0=free, 1=locked
  rhythmPhase: 'rise' | 'hold' | 'release';
  durationMultiplier: number; // slow scenes feel longer
}

class AdaptiveCinemaDirector {
  private _state: DirectorState = {
    tensionLevel: 0,
    exposurePacing: 1.0,
    cameraRestraint: 0.5,
    rhythmPhase: 'hold',
    durationMultiplier: 1.0,
  };

  private _subscribers: Set<(s: DirectorState) => void> = new Set();
  private _intervalId: ReturnType<typeof setInterval> | null = null;

  start() {
    if (this._intervalId) return;

    this._intervalId = setInterval(() => {
      const sys = sovereignHeartbeat.state;

      // Tension derives from quantum pressure and anomalies
      const rawTension = sys.quantumPressure * 0.6 + (sys.activeAnomalies / 10) * 0.4;
      this._state.tensionLevel += (rawTension - this._state.tensionLevel) * 0.08;

      // Exposure pacing — compress in high tension
      this._state.exposurePacing = 1.0 - this._state.tensionLevel * 0.3;

      // Camera restraint — tighter during conflict
      this._state.cameraRestraint = 0.4 + this._state.tensionLevel * 0.5;

      // Rhythm phase
      if (this._state.tensionLevel > 0.6) this._state.rhythmPhase = 'rise';
      else if (this._state.tensionLevel < 0.2) this._state.rhythmPhase = 'release';
      else this._state.rhythmPhase = 'hold';

      // Duration multiplier — deep scenes feel eternal
      this._state.durationMultiplier =
        this._state.rhythmPhase === 'release' ? 1.4 :
        this._state.rhythmPhase === 'rise' ? 0.8 : 1.0;

      this._subscribers.forEach(fn => fn(this._state));
    }, 200);
  }

  stop() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  subscribe(fn: (s: DirectorState) => void) {
    this._subscribers.add(fn);
    return () => this._subscribers.delete(fn);
  }

  get state() { return this._state; }
}

export const cinematicDirector = new AdaptiveCinemaDirector();

// Start immediately in browser
if (typeof window !== 'undefined') {
  cinematicDirector.start();
}
