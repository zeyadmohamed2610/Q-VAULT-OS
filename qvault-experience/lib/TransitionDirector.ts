// ═══════════════════════════════════════════════════════════════
// TRANSITION DIRECTOR
// IMAX-documentary scene blending.
// Exposure carry-over, bloom inertia, fog interpolation,
// audio crossfade orchestration. No game-engine cuts.
// ═══════════════════════════════════════════════════════════════

import { SCENE_BLOOM, SCENE_EXPOSURE, SCENE_VIGNETTE, SCENE_FOG } from './MasteringPipeline';

export interface TransitionState {
  // Interpolated values between scenes
  bloomIntensity: number;
  bloomThreshold: number;
  vignetteOffset: number;
  vignetteDarkness: number;
  fogDensity: number;
  exposure: number;     // 0.0–1.0 normalized
  crossfadeAlpha: number; // 0.0 = prev scene, 1.0 = next scene
  inTransition: boolean;
}

type Listener = (s: TransitionState) => void;

class TransitionDirector {
  private _state: TransitionState;
  private _targetScene = 0;
  private _fromScene = 0;
  private _progress = 1.0; // 1.0 = settled
  private _listeners: Set<Listener> = new Set();
  private _rafId: number | null = null;
  private _lastTime = 0;

  // Transition duration per scene (seconds).
  // ACT IV threat cuts: ultra-fast (0.25s) for kinetic urgency.
  // ACT III hero: 0.80s — gravitas.
  // ACT V final: 1.20s — monumental.
  private readonly DURATIONS: Record<number, number> = {
    0:  0.55,   // Void boot
    1:  0.50,   // LED blink
    2:  0.55,   // Edge macro
    3:  0.50,   // Boot texture
    4:  0.45,   // USB-C
    5:  0.45,   // Seam
    6:  0.55,   // PCB core
    7:  0.50,   // Reflection sweep
    8:  0.80,   // HERO REVEAL — gravitas
    9:  0.55,   // Exploded
    10: 0.60,   // Pedestal
    11: 0.25,   // Threat cut — kinetic
    12: 0.25,
    13: 0.25,
    14: 0.25,
    15: 0.35,   // ZK — slight settle
    16: 0.70,   // Majestic rise
    17: 0.65,   // Logo reveal
    18: 1.20,   // Final seal — monumental
  };

  constructor() {
    const b = SCENE_BLOOM[0];
    const v = SCENE_VIGNETTE[0];
    this._state = {
      bloomIntensity: b.intensity,
      bloomThreshold: b.threshold,
      vignetteOffset: v.offset,
      vignetteDarkness: v.darkness,
      fogDensity: SCENE_FOG[0],
      exposure: this._exposureMultiplier(0),
      crossfadeAlpha: 1.0,
      inTransition: false,
    };
  }

  transitionTo(scene: number) {
    if (scene === this._targetScene && this._progress >= 1.0) return;
    this._fromScene = this._targetScene;
    this._targetScene = scene;
    this._progress = 0.0;
    this._state.inTransition = true;
    this._lastTime = performance.now();

    if (!this._rafId) this._tick();
  }

  private _tick() {
    const now = performance.now();
    const delta = (now - this._lastTime) / 1000;
    this._lastTime = now;

    const duration = this.DURATIONS[this._targetScene] ?? 2.0;
    this._progress = Math.min(1.0, this._progress + delta / duration);

    // Smooth step easing — no snap, no bounce
    const t = this._smoothstep(this._progress);

    const fromB = SCENE_BLOOM[this._fromScene]   ?? { intensity: 1.2, threshold: 0.2 };
    const toB   = SCENE_BLOOM[this._targetScene] ?? { intensity: 1.2, threshold: 0.2 };
    const fromV = SCENE_VIGNETTE[this._fromScene]   ?? { offset: 0.25, darkness: 1.1 };
    const toV   = SCENE_VIGNETTE[this._targetScene] ?? { offset: 0.25, darkness: 1.1 };
    const fromF = SCENE_FOG[this._fromScene]   ?? 0.01;
    const toF   = SCENE_FOG[this._targetScene] ?? 0.01;
    const fromE = this._exposureMultiplier(this._fromScene);
    const toE   = this._exposureMultiplier(this._targetScene);

    this._state.bloomIntensity  = this._lerp(fromB.intensity,  toB.intensity,  t);
    this._state.bloomThreshold  = this._lerp(fromB.threshold,  toB.threshold,  t);
    this._state.vignetteOffset  = this._lerp(fromV.offset,     toV.offset,     t);
    this._state.vignetteDarkness= this._lerp(fromV.darkness,   toV.darkness,   t);
    this._state.fogDensity      = this._lerp(fromF,            toF,            t);
    this._state.crossfadeAlpha  = t;
    this._state.exposure        = this._lerp(fromE, toE, t);

    if (this._progress >= 1.0) {
      this._state.inTransition = false;
      this._rafId = null;
    } else {
      this._rafId = requestAnimationFrame(() => this._tick());
    }

    this._listeners.forEach(fn => fn(this._state));
  }

  private _lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
  private _exposureMultiplier(scene: number) {
    const stops = SCENE_EXPOSURE[scene] ?? 0;
    return Math.min(1.22, Math.max(0.74, Math.pow(2, stops * 0.45)));
  }
  private _smoothstep(t: number) { 
    // Perlin's Smootherstep — zero first and second derivatives at endpoints
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
  }

  subscribe(fn: Listener) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }

  get state() { return this._state; }
}

export const transitionDirector = new TransitionDirector();
