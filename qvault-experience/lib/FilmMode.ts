// ═══════════════════════════════════════════════════════════════
// AUTONOMOUS FILM MODE — Phase XIX
// Self-running cinematic progression. Idle-driven scene pacing.
// Eliminates need for user interaction. Institutional film mode.
// ═══════════════════════════════════════════════════════════════

'use client';

import { SCENE_REGISTRY } from './scenes';
import { useExperienceStore } from './store';

const IDLE_TIMEOUT_MS = 12000;   // 12s idle before auto-advance (more patient)
const SETTLE_DURATION_MS = 3000; // 3.0s scene settle buffer (architectural dignity)

class FilmMode {
  private _idleTimer: ReturnType<typeof setTimeout> | null = null;
  private _settleTimer: ReturnType<typeof setTimeout> | null = null;
  private _enabled = false;
  private _locked = false; // Scene entry lock — prevents skipping first 15%
  private _lastActivity = 0;

  enable() {
    this._enabled = true;
    this._lastActivity = Date.now();
    this._scheduleAdvance();
    if (typeof window !== 'undefined') {
      window.addEventListener('pointermove', this._onActivity, { passive: true });
      window.addEventListener('keydown', this._onActivity, { passive: true });
      window.addEventListener('wheel', this._onActivity, { passive: true });
    }
  }

  disable() {
    this._enabled = false;
    this._clearTimers();
    if (typeof window !== 'undefined') {
      window.removeEventListener('pointermove', this._onActivity);
      window.removeEventListener('keydown', this._onActivity);
      window.removeEventListener('wheel', this._onActivity);
    }
  }

  get isLocked() { return this._locked; }
  get isEnabled() { return this._enabled; }

  // Called when a scene change is initiated
  onSceneEntry(sceneIndex: number) {
    this._locked = true;
    this._clearTimers();

    // Calculate settle duration — slower for hardware scenes
    const isHeroScene = sceneIndex === 2 || sceneIndex === 6 || sceneIndex === 12;
    const settle = isHeroScene ? SETTLE_DURATION_MS * 1.8 : SETTLE_DURATION_MS;

    this._settleTimer = setTimeout(() => {
      this._locked = false;
      if (this._enabled) this._scheduleAdvance();
    }, settle);
  }

  private _onActivity = () => {
    this._lastActivity = Date.now();
    if (this._enabled) {
      // Reset auto-advance on user activity
      this._clearTimers();
      this._scheduleAdvance();
    }
  };

  private _scheduleAdvance() {
    if (!this._enabled) return;
    this._idleTimer = setTimeout(() => {
      this._advance();
    }, IDLE_TIMEOUT_MS);
  }

  private _advance() {
    const store = useExperienceStore.getState();
    const current = store.activeScene;
    const next = current + 1;
    
    // Attempt to scroll to the next scene trigger
    if (typeof window !== 'undefined') {
      const nextId = next < SCENE_REGISTRY.length ? SCENE_REGISTRY[next].id : SCENE_REGISTRY[0].id;
      const targetEl = document.getElementById(`scene-${nextId}`);
      if (targetEl) {
        // Use smooth scrolling for cinematic progression
        const rect = targetEl.getBoundingClientRect();
        window.scrollBy({ top: rect.top, behavior: 'smooth' });
      }
    }
  }

  private _clearTimers() {
    if (this._idleTimer) clearTimeout(this._idleTimer);
    if (this._settleTimer) clearTimeout(this._settleTimer);
    this._idleTimer = null;
    this._settleTimer = null;
  }
}

export const filmMode = new FilmMode();
