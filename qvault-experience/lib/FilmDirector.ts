// ═══════════════════════════════════════════════════════════════
// FILM DIRECTOR — PHASE XXXV: CINEMATIC RE-DIRECTION
//
// Target runtime: 57 seconds.
// Structure: 13 scenes across 5 acts.
// Philosophy: the viewer EARNS the full product reveal.
//
// ACT I   THE SIGNAL      (0–10.5s)  — darkness, curiosity
// ACT II  THE OBJECT     (10.5–21s)  — partial macro reveals
// ACT III THE SYSTEM     (21–34s)   — FIRST FULL REVEAL
// ACT IV  THE THREAT     (34–40.5s) — urgency, defense
// ACT V   IMMORTALITY    (40.5–57s) — legend, final seal
// ═══════════════════════════════════════════════════════════════

import { SCENE_REGISTRY } from './scenes';
import { useExperienceStore } from './store';
import { transitionDirector } from './TransitionDirector';
import { directiveEngine } from './DirectiveEngine';

// ── XXXV timing — 57 seconds total ────────────────────────────
const SCENE_DURATIONS: Record<number, number> = {
  // ACT I — THE SIGNAL (10.5s)
  0: 3500,  // Void / boot signal — pure darkness, curiosity
  1: 4000,  // Metal edge macro — cyan rim cuts the black
  2: 3000,  // Logo silhouette — identity emerges

  // ACT II — THE OBJECT (10.5s)
  3: 3500,  // USB-C port macro — physical trust interface
  4: 3500,  // Enclosure corner — machined precision
  5: 3500,  // PCB overhead — silicon core reveal

  // ACT III — THE SYSTEM (13s)
  6: 5000,  // FIRST FULL HERO REVEAL — assembled product
  7: 4000,  // Exploded view — mechanical authority
  8: 4000,  // Low-angle authority — sovereign form

  // ACT IV — THE THREAT (6.5s)
  9: 3500,  // Threat close — amber urgency
  10:3000,  // Interception — contained, controlled

  // ACT V — IMMORTALITY (11.5s)
  11:5000,  // Majestic celestial — the device transcends
  12:6500,  // Final seal — legend, fade to black
};

const TOTAL_DURATION = Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0);
const END_HOLD       = 3500;

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

    for (let i = 0; i < SCENE_REGISTRY.length; i++) {
      const dur = SCENE_DURATIONS[i] ?? 4000;
      if (elapsed < acc + dur) {
        activeScene   = i;
        sceneProgress = (elapsed - acc) / dur;
        break;
      }
      acc += dur;
      if (i === SCENE_REGISTRY.length - 1) {
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
  get info()          { return `${Math.round(TOTAL_DURATION / 1000)}s / ${SCENE_REGISTRY.length} scenes`; }
}

export const filmDirector = new FilmDirector();
