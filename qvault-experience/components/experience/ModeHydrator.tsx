// ═══════════════════════════════════════════════════════════════
// MODE HYDRATOR — Deliverable Modes logic
// Injects environment states based on route or store.
// ═══════════════════════════════════════════════════════════════

'use client';

import { useEffect } from 'react';
import { useExperienceStore } from '@/lib/store';

export type OperationalMode = 'standard' | 'executive' | 'investor' | 'presentation' | 'museum' | 'kiosk';

export function ModeHydrator({ mode }: { mode: OperationalMode }) {
  const setActiveScene = useExperienceStore((s) => s.setActiveScene);

  useEffect(() => {
    // Apply mode-specific initializations
    if (mode === 'executive') {
      // Logic for executive: start at a specific bookmark
      setActiveScene(0);
    }
    
    if (mode === 'presentation') {
      // Force slower pacing via Directive Engine (inferred)
    }

    // Set a global attribute for CSS selectors
    document.documentElement.setAttribute('data-mode', mode);
    
    return () => {
      document.documentElement.removeAttribute('data-mode');
    };
  }, [mode, setActiveScene]);

  return null;
}
