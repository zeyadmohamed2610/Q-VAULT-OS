# Q-VAULT 🏛️ Media Export Guide (Phase XVIII)

Authoritative technical instructions for capturing high-fidelity cinematic stills and 4K walkthrough footage of the Q-VAULT experience.

---

## 📸 Cinematic Stills Capture

### 1. Environment Setup
- **Browser**: Chrome/Edge (Chromium based).
- **Resolution**: Force `3840x2160` (4K) via Developer Tools (Device Emulation).
- **DPR**: Set Device Pixel Ratio to `2.0` or `3.0` for sub-pixel fidelity.

### 2. Capture Moments (Hero Angles)
- **VOID_BOOT**: Capture at `progress: 0.8` (Final text alignment).
- **THE_OBJECT**: Capture at `progress: 0.5` (Parallel to PCB plane).
- **GLOBAL_INFRA**: Capture in `/authority` mode (Full map spread).
- **SEAL**: Capture at `progress: 1.0` (Absolute monochromatic lock).

---

## 📹 4K Walkthrough Recording

### 1. OBS Configuration
- **Encoder**: NVIDIA NVENC H.264 (CQP).
- **CQ Level**: `16` (Visually lossless).
- **Bitrate**: `50,000 Kbps`.
- **Keyframe Interval**: `2s`.
- **Profile**: `high`.

### 2. Browser Performance Flags
Launch Chromium with these flags for maximum WebGL stability:
```bash
--disable-frame-rate-limit 
--force-device-scale-factor=1 
--enable-gpu-rasterization
```

---

## 🎨 Post-Production (Mastering)

### 1. Export LUT Recommendations
- **Gamma**: 2.2 (Sovereign Deep Black).
- **Contrast**: High (+15%).
- **Saturation**: -80% (Preserve only Safety Cyan).

### 2. Presentation Playback
- Use a physical OLED display if possible.
- Ensure room lighting is minimal to maximize the effect of "Institutional Silence."

---

© 2026 Q-VAULT INSTITUTIONAL. MEDIA MASTERING GUIDE.
