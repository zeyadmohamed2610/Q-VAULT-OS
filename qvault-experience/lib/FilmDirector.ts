// ═══════════════════════════════════════════════════════════════
// FILM DIRECTOR — PHASE OMEGA: CINEMATIC REBIRTH
//
// Target runtime: 72 seconds.
// Theme: "THE DEVICE THAT OUTLIVES SYSTEMS."
// Structure: 17 scenes across 5 acts.
//
// ACT I   THE SIGNAL        (0–12s)   — darkness, obsession, curiosity
// ACT II  ENGINEERED OBJECT (12–26s)  — fragments, texture, desire
// ACT III FULL REVEAL       (26–40s)  — sovereign hero, dominance
// ACT IV  THE THREAT        (40–52s)  — rapid cuts, kinetic urgency
// ACT V   IMMORTALITY       (52–72s)  — monumental, timeless, sealed
//
// Pacing philosophy:
//   ACT I/II: 3-4s scenes — earn the curiosity
//   ACT III:  4-5s scenes — let the reveal breathe
//   ACT IV:   2-3s scenes — aggressive, kinetic, addictive
//   ACT V:    4-6s scenes — legendary stillness
// ═══════════════════════════════════════════════════════════════

import { SCENE_REGISTRY } from './scenes';
import { useExperienceStore } from './store';
import { transitionDirector } from './TransitionDirector';
import { directiveEngine } from './DirectiveEngine';

// ── OMEGA timing — 72 seconds total ───────────────────────────
export const SCENE_DURATIONS: Record<number, number> = {
  // ── ACT I — THE SIGNAL (12s) ──────────────────────────────
  0: 3000,  // Void: pure black. Power pulse. Bass drop.
  1: 3500,  // LED blink: ultra-close eye of the device. First contact.
  2: 2800,  // Edge macro: cyan rim splits the void. Identity.
  3: 2700,  // Boot glyphs: surface texture, circuit geography.

  // ── ACT II — ENGINEERED OBJECT (14s) ──────────────────────
  4: 3500,  // USB-C port: telephoto compression. Physical trust.
  5: 3000,  // Enclosure seam: machined precision, chamfered edge.
  6: 3500,  // PCB overhead: silicon core. Classified circuitry.
  7: 4000,  // Reflection sweep: light rakes across the shell.

  // ── ACT III — FULL REVEAL (14s) ───────────────────────────
  8: 5000,  // HERO SHOT: assembled device. Full frontal. 80% fill.
  9: 4000,  // Exploded lock: shells separate with ballistic authority.
  10:5000,  // Low-angle pedestal: camera looks up. Sovereign monument.

  // ── ACT IV — THE THREAT (12s) — RAPID CUTS ────────────────
  11:2500,  // Threat impact: amber flash. Attack detected.
  12:2500,  // Shockwave: device holds. Unshaken.
  13:2500,  // Interception: hard diagonal. Zero compromise.
  14:2500,  // Containment: device center. Threat neutralized.
  15:2000,  // Zero knowledge: confirmation flash.

  // ── ACT V — IMMORTALITY (20s) ─────────────────────────────
  16:5000,  // Majestic rise: device ascends from void.
  17:5500,  // Logo reveal: slow push. Identity confirmed.
  18:9500,  // Final seal: absolute stillness. Monument. Q-VAULT.
};

const TOTAL_DURATION = Object.values(SCENE_DURATIONS).reduce((a, b) => a + b, 0);
const END_HOLD       = 4000;
const SCENE_COUNT    = Object.keys(SCENE_DURATIONS).length; // 19 (0–18)

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
      const dur = SCENE_DURATIONS[i] ?? 4000;
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
