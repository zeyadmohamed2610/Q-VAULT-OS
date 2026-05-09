// ═══════════════════════════════════════════════════════════════
// Q-VAULT EXPERIENCE — Act Marker
// 4 dots on right edge representing the 4 acts
// ═══════════════════════════════════════════════════════════════

'use client';

import { useExperienceStore } from '@/lib/store';
import { ACTS, SCENE_REGISTRY } from '@/lib/scenes';

export function ActMarker() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const activeAct = SCENE_REGISTRY[activeScene]?.act;

  return (
    <div className="fixed right-6 top-1/2 -translate-y-1/2 flex flex-col gap-4 select-none">
      {ACTS.map((act) => {
        const isActive = act.id === activeAct;
        return (
          <div
            key={act.id}
            className="group relative flex items-center justify-end"
          >
            {/* Label — visible on hover */}
            <span
              className="absolute right-5 font-mono text-[9px] tracking-[0.15em] uppercase opacity-0 group-hover:opacity-60 transition-opacity whitespace-nowrap"
              style={{
                color: 'var(--text-muted)',
                transitionDuration: 'var(--motion-snappy)',
              }}
            >
              {act.name}
            </span>

            {/* Dot */}
            <div
              className="rounded-full transition-all"
              style={{
                width: isActive ? 8 : 5,
                height: isActive ? 8 : 5,
                background: isActive ? 'var(--cyan)' : 'var(--steel)',
                boxShadow: isActive ? 'var(--glow-cyan)' : 'none',
                transitionDuration: 'var(--motion-smooth)',
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
