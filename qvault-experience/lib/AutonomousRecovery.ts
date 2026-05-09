// ═══════════════════════════════════════════════════════════════
// AUTONOMOUS RECOVERY
// Ultra-long runtime stability.
// Memory leak auditing, WebGL recovery, kiosk-safe loop mode.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect, useRef } from 'react';

const MEMORY_CHECK_INTERVAL_MS = 30_000;  // every 30s
const MEMORY_LIMIT_MB = 800;              // aggressive recovery above 800MB
const WEBGL_RECOVERY_DELAY_MS = 2_000;

export function useAutonomousRecovery() {
  const contextLostRef = useRef(false);
  const memoryCheckRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // ── WebGL Context Loss Recovery ──
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const handleContextLost = (e: Event) => {
        e.preventDefault();
        contextLostRef.current = true;
        console.warn('[AutonomousRecovery] WebGL context lost — scheduling recovery...');

        setTimeout(() => {
          console.warn('[AutonomousRecovery] Attempting WebGL context restore...');
          // Force re-render by dispatching a custom event
          window.dispatchEvent(new CustomEvent('qvault:context-restore'));
        }, WEBGL_RECOVERY_DELAY_MS);
      };

      const handleContextRestored = () => {
        contextLostRef.current = false;
        console.info('[AutonomousRecovery] WebGL context restored.');
      };

      canvas.addEventListener('webglcontextlost', handleContextLost);
      canvas.addEventListener('webglcontextrestored', handleContextRestored);

      return () => {
        canvas.removeEventListener('webglcontextlost', handleContextLost);
        canvas.removeEventListener('webglcontextrestored', handleContextRestored);
      };
    }
  }, []);

  useEffect(() => {
    // ── Memory Pressure Monitoring ──
    if (!('memory' in performance)) return;

    memoryCheckRef.current = setInterval(() => {
      const mem = (performance as any).memory;
      const usedMB = mem.usedJSHeapSize / 1_048_576;

      if (usedMB > MEMORY_LIMIT_MB) {
        console.warn(`[AutonomousRecovery] High memory: ${usedMB.toFixed(0)}MB — requesting GC...`);
        // Force GC in environments that support it
        if ((window as any).gc) (window as any).gc();
      }
    }, MEMORY_CHECK_INTERVAL_MS);

    return () => {
      if (memoryCheckRef.current) clearInterval(memoryCheckRef.current);
    };
  }, []);

  useEffect(() => {
    // ── Kiosk Loop Mode ──
    // If document is hidden for >10 minutes, soft reset scroll to start
    let hiddenAt: number | null = null;
    const KIOSK_RESET_MS = 10 * 60 * 1000;

    const handleVisibility = () => {
      if (document.hidden) {
        hiddenAt = Date.now();
      } else if (hiddenAt !== null) {
        const away = Date.now() - hiddenAt;
        if (away > KIOSK_RESET_MS) {
          console.info('[AutonomousRecovery] Kiosk reset: scrolling to top after long inactivity.');
          window.scrollTo({ top: 0, behavior: 'instant' });
        }
        hiddenAt = null;
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, []);
}
