// ═══════════════════════════════════════════════════════════════
// AUDIO MANAGER
// Cinematic audio architecture for infrastructure-grade soundscapes.
// ═══════════════════════════════════════════════════════════════

import { Howl, Howler } from 'howler';

// In a real production, these would be actual URLs
const AUDIO_ASSETS = {
  infrastructure_hum: '/audio/infrastructure_hum.mp3', // Deep sub-bass
  cryptographic_pulse: '/audio/crypto_pulse.mp3', // Scene 4 handshake
  seal_impact: '/audio/seal_impact.mp3', // Scene 12 lock
  threat_alarm: '/audio/threat_alarm.mp3', // Scene 9 matrix
  transition_riser: '/audio/transition_riser.mp3', // Scene transitions
};

class AudioManager {
  private sounds: Map<string, Howl> = new Map();
  private initialized = false;
  private currentAmbient: string | null = null;
  private masterVolume = 1.0;

  init() {
    if (this.initialized) return;

    // Initialize core sound layers
    // Note: We're failing gracefully if files are missing in this demo
    try {
      this.sounds.set('hum', new Howl({ src: [AUDIO_ASSETS.infrastructure_hum], loop: true, volume: 0, html5: true }));
      this.sounds.set('pulse', new Howl({ src: [AUDIO_ASSETS.cryptographic_pulse], volume: 0.5 }));
      this.sounds.set('seal', new Howl({ src: [AUDIO_ASSETS.seal_impact], volume: 0.8 }));
      this.sounds.set('threat', new Howl({ src: [AUDIO_ASSETS.threat_alarm], loop: true, volume: 0 }));
      this.sounds.set('riser', new Howl({ src: [AUDIO_ASSETS.transition_riser], volume: 0.3 }));
    } catch (e) {
      console.warn('Audio assets missing, continuing silently.');
    }

    this.initialized = true;
  }

  startAmbient() {
    if (!this.initialized) this.init();
    const hum = this.sounds.get('hum');
    if (hum && !hum.playing()) {
      hum.play();
      hum.fade(0, 0.5 * this.masterVolume, 4000);
      this.currentAmbient = 'hum';
    }
  }

  setMasterVolume(vol: number) {
    this.masterVolume = Math.max(0, Math.min(1, vol));
    Howler.volume(this.masterVolume);
  }

  crossfadeAmbient(to: string, duration = 2000) {
    if (!this.initialized) return;
    const current = this.currentAmbient ? this.sounds.get(this.currentAmbient) : null;
    const next = this.sounds.get(to);

    if (current && current.playing()) {
      current.fade(current.volume(), 0, duration);
      setTimeout(() => current.pause(), duration);
    }

    if (next) {
      if (!next.playing()) next.play();
      next.fade(0, 0.5 * this.masterVolume, duration);
      this.currentAmbient = to;
    }
  }

  playEvent(name: string, volume = 1.0) {
    if (!this.initialized) return;
    const sound = this.sounds.get(name);
    if (sound) {
      sound.volume(volume * this.masterVolume);
      sound.play();
    }
  }

  setLowPassFilter(freq: number) {
    // In a real web audio setup, we'd pipe Howler master through a BiquadFilterNode
    // This provides a high-level API for it.
  }
}

export const audioManager = new AudioManager();
