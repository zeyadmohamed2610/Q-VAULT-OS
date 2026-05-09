// ═══════════════════════════════════════════════════════════════
// FILM DIRECTOR — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// Runtime: 55 seconds. 10 scenes. No filler.
// Every second earns its place.
//
// ACT I   IDENTITY      0–5s    (2 scenes)
// ACT II  HARDWARE      5–18s   (4 scenes)
// ACT III SECURITY      18–32s  (2 scenes)
// ACT IV  ASSEMBLY      32–44s  (1 scene)
// ACT V   AUTHORITY     44–55s  (1 scene)
//
// Performance decisions:
//   Fewer scenes = fewer material transitions = fewer GC spikes
//   Minimum 4s per scene = camera has time to settle
//   No rapid-fire micro-scenes that spike frame time
// ═══════════════════════════════════════════════════════════════

import { useExperienceStore } from './store';
import { transitionDirector } from './TransitionDirector';
import { directiveEngine } from './DirectiveEngine';

export const SCENE_DURATIONS: Record<number, number> = {
  // ACT I — IDENTITY
  0: 3500,   // Black void — signal pulse
  1: 4500,   // Hero emergence — device rises from nothing

  // ACT II — HARDWARE REVEAL
  2: 3500,   // Macro: USB-C port, physical trust
  3: 3500,   // Macro: PCB surface, classified architecture
  4: 3000,   // Macro: enclosure edge, machined precision
  5: 3500,   // Full product: assembled, hero frontal

  // ACT III — SECURITY
  6: 6000,   // Post-quantum architecture — sovereignty statement
  7: 5500,   // Zero network — air-gap authority

  // ACT IV — ASSEMBLY
  8: 5500,   // Exploded + magnetic assembly snap

  // ACT V — AUTHORITY
  9: 12000,  // Final: assembled. Static. Monument. Q-VAULT.
};

const TOTAL_DURATION = Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0);
const END_HOLD       = 4000;
const SCENE_COUNT    = Object.keys(SCENE_DURATIONS).length;

class FilmDirector {
  private _startTime = 0;
  private _rafId: number | null = null;
  private _running   = false;
  private _ended     = false;
  private _lastScene = -1;

  start() {
    this.stop();
    this._running   = true;
    this._ended     = false;
    this._lastScene = -1;
    this._startTime = performance.now();
    this._tick();
  }

  stop() {
    this._running = false;
    if (this._rafId !== null) cancelAnimationFrame(this._rafId);
    this._rafId = null;
  }

  private _tick() {
    if (!this._running) return;

    const elapsed = (performance.now() - this._startTime) % (TOTAL_DURATION + END_HOLD);

    let acc = 0;
    let activeScene   = 0;
    let sceneProgress = 0;

    for (let i = 0; i < SCENE_COUNT; i++) {
      const dur = SCENE_DURATIONS[i] ?? 5000;
      if (elapsed < acc + dur) {
        activeScene   = i;
        sceneProgress = (elapsed - acc) / dur;
        break;
      }
      acc += dur;
      if (i === SCENE_COUNT - 1) {
        activeScene   = i;
        sceneProgress = 1.0;
        if (elapsed >= acc + END_HOLD && !this._ended) this._onEnd();
      }
    }

    const store = useExperienceStore.getState();
    if (activeScene !== this._lastScene) {
      this._lastScene = activeScene;
      transitionDirector.transitionTo(activeScene);
      directiveEngine.applySceneDirective(activeScene);
      store.setActiveScene(activeScene);
    }
    store.setSceneProgress(sceneProgress);
    store.setGlobalProgress(Math.min(1, elapsed / TOTAL_DURATION));

    this._rafId = requestAnimationFrame(() => this._tick());
  }

  private _onEnd() { this._ended = true; }

  get isEnded()       { return this._ended; }
  get totalDuration() { return TOTAL_DURATION; }
  get sceneCount()    { return SCENE_COUNT; }
  get info()          { return `${Math.round(TOTAL_DURATION / 1000)}s / ${SCENE_COUNT} scenes`; }
}

export const filmDirector = new FilmDirector();
