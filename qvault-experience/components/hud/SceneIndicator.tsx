// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Scene Indicator
// Displays current scene name in monospace, top-left
// ═══════════════════════════════════════════════════════════════

'use client';

import { useExperienceStore } from '@/lib/store';
import { SCENE_REGISTRY } from '@/lib/scenes';

export function SceneIndicator() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const config = SCENE_REGISTRY[activeScene];

  if (!config) return null;

  return (
    <div
      className="fixed top-6 left-6 font-mono text-xs tracking-[0.2em] uppercase select-none transition-opacity"
      style={{
        color: 'var(--text-muted)',
        opacity: 0.6,
        transitionDuration: 'var(--motion-smooth)',
      }}
    >
      <span style={{ color: 'var(--cyan-dim)' }}>
        {String(config.index).padStart(2, '0')}
      </span>
      <span className="mx-2" style={{ color: 'var(--steel)' }}>
        /
      </span>
      <span>{config.name}</span>
    </div>
  );
}
