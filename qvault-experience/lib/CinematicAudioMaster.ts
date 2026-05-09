// ═══════════════════════════════════════════════════════════════
// CINEMATIC AUDIO MASTER
// Layered ambient zones, adaptive dynamic range,
// and silence as a weapon.
// ═══════════════════════════════════════════════════════════════

import { Howl, Howler } from 'howler';

// ── Layer Architecture ──
// Each layer is independently faded and mixed.
interface AudioLayer {
  id: string;
  howl: Howl | null;
  volume: number;  // current
  target: number;  // lerp target
}

// ── Act-based ambient zones ──
const ACT_AMBIENT: Record<string, string> = {
  origin:    '/audio/ambient_origin.mp3',    // Act I: low-frequency hardware hum, deep drones
  mechanism: '/audio/ambient_mechanism.mp3', // Act II: industrial resonance, manufacturing rhythm
  command:   '/audio/ambient_command.mp3',   // Act III: tense authority, deep synchronized pulses
  horizon:   '/audio/ambient_horizon.mp3',   // Act IV: archival drones, silent vastness
};

const SCENE_STINGERS: Record<number, string> = {
  0:  '/audio/stinger_boot.mp3',             // Power on, relay clicks
  2:  '/audio/stinger_object.mp3',           // Heavy physical emergence
  4:  '/audio/stinger_assembly.mp3',         // Enclosure sealing sounds
  5:  '/audio/stinger_seal.mp3',             // Magnetic closure click
  7:  '/audio/stinger_sync.mp3',             // Deep synchronized network pulse
  9:  '/audio/stinger_threat.mp3',           // Low frequency warning boom
  12: '/audio/stinger_vault.mp3',            // Heavy vault closure, emotional silence follows
};

class CinematicAudioMaster {
  private layers: Map<string, AudioLayer> = new Map();
  private initialized = false;
  private masterVolume = 0.8;
  private currentAct = '';
  private lerpInterval: ReturnType<typeof setInterval> | null = null;

  init() {
    if (this.initialized || typeof window === 'undefined') return;

    Howler.volume(this.masterVolume);

    // Initialize base layers (graceful fail if files missing)
    Object.entries(ACT_AMBIENT).forEach(([act, src]) => {
      try {
        const howl = new Howl({
          src: [src],
          loop: true,
          volume: 0,
          html5: true,
          preload: false, // lazy load
        });
        this.layers.set(act, { id: act, howl, volume: 0, target: 0 });
      } catch {
        this.layers.set(act, { id: act, howl: null, volume: 0, target: 0 });
      }
    });

    // Start volume lerp loop
    this.lerpInterval = setInterval(() => this._lerpVolumes(), 50);

    this.initialized = true;
  }

  private _lerpVolumes() {
    this.layers.forEach((layer) => {
      if (!layer.howl) return;
      const diff = layer.target - layer.volume;
      if (Math.abs(diff) < 0.001) {
        layer.volume = layer.target;
      } else {
        layer.volume += diff * 0.05; // very slow crossfade
      }
      layer.howl.volume(Math.max(0, Math.min(1, layer.volume * this.masterVolume)));
    });
  }

  setAct(act: string) {
    if (!this.initialized || act === this.currentAct) return;
    this.currentAct = act;

    this.layers.forEach((layer, id) => {
      const isTarget = id === act;
      layer.target = isTarget ? 0.5 : 0;

      if (isTarget && layer.howl && !layer.howl.playing()) {
        layer.howl.load();
        layer.howl.play();
      }
    });
  }

  playStinger(sceneIndex: number) {
    if (!this.initialized) return;
    const src = SCENE_STINGERS[sceneIndex];
    if (!src) return;

    try {
      const stinger = new Howl({ src: [src], volume: 0.7 * this.masterVolume });
      stinger.play();
    } catch { /* graceful */ }
  }

  // Silence gap — used at seal transition
  ducked(duration = 3000) {
    if (!this.initialized) return;
    const prev = this.masterVolume;
    
    // Fade all layers to zero
    this.layers.forEach(l => l.target = 0);
    
    // Restore after duration
    setTimeout(() => {
      this.setAct(this.currentAct);
    }, duration);
  }

  setMaster(vol: number) {
    this.masterVolume = Math.max(0, Math.min(1, vol));
  }

  unlock() {
    this.init();
  }

  destroy() {
    if (this.lerpInterval) clearInterval(this.lerpInterval);
    Howler.unload();
  }
}

export const cinematicAudio = new CinematicAudioMaster();

// Scene index → act name mapping
export function sceneToAct(sceneIndex: number): string {
  if (sceneIndex <= 2) return 'origin';
  if (sceneIndex <= 6) return 'mechanism';
  if (sceneIndex <= 9) return 'command';
  return 'horizon';
}
