# Q-VAULT Cinematic Experience
## Production Deployment Architecture

This document outlines the deployment strategy for the Q-VAULT web experience, hardened for production on Vercel.

### 1. Edge Strategy
- The application utilizes Next.js App Router with React Server Components (RSC) to serve the initial shell.
- The heavy 3D canvas and cinematic elements are dynamically imported (`next/dynamic` with `ssr: false`) to ensure fast Time-To-Interactive (TTI).
- Edge caching is applied to all static assets (`.glb`, textures, fonts).

### 2. Performance Safeguards
The application includes several autonomous diagnostic systems:
- **`usePerformanceGovernor`**: Continuously samples frame times over 60-frame windows. If thermal throttling or memory pressure is detected, it steps down the Device Pixel Ratio (DPR) and disables antialiasing.
- **Adaptive PostFX**: The `PostFX` component scales shader intensity based on scroll progress and bypasses expensive effects when memory pressure is critical.
- **GPU Pooling**: Instanced Meshes (`GovernanceCore`, `ThreatMatrix`) share geometry and materials, resulting in zero-allocation render loops.

### 3. Audio Architecture
- **Howler.js Integration**: The cinematic audio uses a layered architecture, gracefully failing if assets are blocked by the browser. 
- **Interaction Lock**: Audio is primed on the first user interaction (click/touch) to comply with modern browser autoplay policies.

### 4. Vercel Configuration
Ensure the following settings are configured in your Vercel project:

**Build Command:**
`npm run build`

**Output Directory:**
`.next`

**Environment Variables:**
None required for the public-facing static cinematic build.

**Cache Headers (next.config.mjs):**
```js
module.exports = {
  async headers() {
    return [
      {
        source: '/models/:all*(glb|gltf)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          }
        ],
      }
    ];
  },
};
```

### 5. SEO & Metadata
The `layout.tsx` should be configured with robust social preview graphs:
- `title`: Q-VAULT | Post-Quantum Trust Preserved
- `description`: Sovereign cryptographic infrastructure visualization.
- `openGraph`: Immersive 3D web experience.

### 6. Fallbacks
If WebGL context is lost (mobile memory limits), the UI degrades gracefully. The HUD remains active, allowing users to scroll and read the narrative even if the 3D canvas collapses.
