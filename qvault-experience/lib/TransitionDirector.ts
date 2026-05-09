// ═══════════════════════════════════════════════════════════════
// TRANSITION DIRECTOR — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// 10-scene timing. Transitions target 0.5–0.7s.
// Perlin smootherstep easing on all interpolations.
// ═══════════════════════════════════════════════════════════════

import { SCENE_BLOOM, SCENE_EXPOSURE, SCENE_VIGNETTE, SCENE_FOG } from './MasteringPipeline';

export interface TransitionState {
  bloomIntensity:   number;
  bloomThreshold:   number;
  vignetteOffset:   number;
  vignetteDarkness: number;
  fogDensity:       number;
  exposure:         number;
  crossfadeAlpha:   number;
  inTransition:     boolean;
}

type Listener = (s: TransitionState) => void;

class TransitionDirector {
  private _state: TransitionState;
  private _targetScene = 0;
  private _fromScene   = 0;
  private _progress    = 1.0;
  private _listeners: Set<Listener> = new Set();
  private _rafId: number | null = null;
  private _lastTime = 0;

  // Transition durations — clean, not rushed, not sluggish
  private readonly DURATIONS: Record<number, number> = {
    0: 0.50,
    1: 0.65,
    2: 0.50,
    3: 0.50,
    4: 0.50,
    5: 0.70,   // Hero reveal — extra gravitas
    6: 0.60,
    7: 0.60,
    8: 0.55,
    9: 0.90,   // Final seal — deliberate, cinematic
  };

  constructor() {
    const b = SCENE_BLOOM[0]    ?? { intensity: 0.05, threshold: 0.92 };
    const v = SCENE_VIGNETTE[0] ?? { offset: 0.44, darkness: 0.42 };
    this._state = {
      bloomIntensity:   b.intensity,
      bloomThreshold:   b.threshold,
      vignetteOffset:   v.offset,
      vignetteDarkness: v.darkness,
      fogDensity:       SCENE_FOG[0] ?? 0.0005,
      exposure:         this._expMul(0),
      crossfadeAlpha:   1.0,
      inTransition:     false,
    };
  }

  transitionTo(scene: number) {
    if (scene === this._targetScene && this._progress >= 1.0) return;
    this._fromScene   = this._targetScene;
    this._targetScene = scene;
    this._progress    = 0.0;
    this._state.inTransition = true;
    this._lastTime = performance.now();
    if (!this._rafId) this._tick();
  }

  private _tick() {
    const now   = performance.now();
    const delta = (now - this._lastTime) / 1000;
    this._lastTime = now;

    const dur = this.DURATIONS[this._targetScene] ?? 0.6;
    this._progress = Math.min(1.0, this._progress + delta / dur);
    const t = this._smooth(this._progress);

    const fromB = SCENE_BLOOM[this._fromScene]    ?? { intensity: 0.10, threshold: 0.90 };
    const toB   = SCENE_BLOOM[this._targetScene]  ?? { intensity: 0.10, threshold: 0.90 };
    const fromV = SCENE_VIGNETTE[this._fromScene] ?? { offset: 0.55, darkness: 0.25 };
    const toV   = SCENE_VIGNETTE[this._targetScene] ?? { offset: 0.55, darkness: 0.25 };
    const fromF = SCENE_FOG[this._fromScene]    ?? 0.0002;
    const toF   = SCENE_FOG[this._targetScene]  ?? 0.0002;

    this._state.bloomIntensity   = this._lerp(fromB.intensity,  toB.intensity,  t);
    this._state.bloomThreshold   = this._lerp(fromB.threshold,  toB.threshold,  t);
    this._state.vignetteOffset   = this._lerp(fromV.offset,     toV.offset,     t);
    this._state.vignetteDarkness = this._lerp(fromV.darkness,   toV.darkness,   t);
    this._state.fogDensity       = this._lerp(fromF,            toF,            t);
    this._state.crossfadeAlpha   = t;
    this._state.exposure         = this._lerp(this._expMul(this._fromScene), this._expMul(this._targetScene), t);

    if (this._progress >= 1.0) {
      this._state.inTransition = false;
      this._rafId = null;
    } else {
      this._rafId = requestAnimationFrame(() => this._tick());
    }

    this._listeners.forEach(fn => fn(this._state));
  }

  private _lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
  private _expMul(scene: number) {
    const stops = SCENE_EXPOSURE[scene] ?? 0.70;
    return Math.min(1.20, Math.max(0.72, Math.pow(2, stops * 0.40)));
  }
  private _smooth(t: number) {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
  }

  subscribe(fn: Listener) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  get state() { return this._state; }
}

export const transitionDirector = new TransitionDirector();
