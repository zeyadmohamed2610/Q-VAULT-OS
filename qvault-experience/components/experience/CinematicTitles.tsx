'use client';

// ═══════════════════════════════════════════════════════════════
// CINEMATIC TITLES — PHASE XXXV: SOVEREIGN COPY
//
// Principle: fewer words, more weight.
// Each card = ONE emotional idea.
// Typography supports the product. Never competes with it.
//
// Hold: 2.8s (scene duration 3-5s → exits with 0.5-1.5s to spare)
// Enter: 0.25s | Exit: 0.7s
// ═══════════════════════════════════════════════════════════════

import { useEffect, useRef, useState } from 'react';
import { useExperienceStore } from '@/lib/store';

interface TitleCard {
  scene:   number;
  act?:    string;
  title:   string;
  sub?:    string;
  badge?:  string;
  badgeColor?: string;
}

// ── Sovereign copy — minimal, powerful ────────────────────────
const CARDS: TitleCard[] = [
  // ACT I — THE SIGNAL
  { scene: 0,  title: '',                   sub: '' },
  { scene: 1,  act:'ACT I',                 title: 'THE SIGNAL',             sub: 'HARDWARE AUTHENTICATION INITIALIZING',  badge:'BOOT',        badgeColor:'rgba(0,200,255,0.5)' },
  { scene: 2,  act:'ACT I',                 title: 'Q-VAULT',                sub: 'SOVEREIGN MEMORY ARCHITECTURE',         badge:'IDENTITY',     badgeColor:'rgba(0,200,255,0.4)' },

  // ACT II — THE OBJECT
  { scene: 3,  act:'ACT II',                title: 'PHYSICAL TRUST',         sub: 'HARDWARE-BOUND IDENTITY' },
  { scene: 4,  act:'ACT II',                title: 'MACHINED PRECISION',      sub: 'MILITARY-GRADE ENCLOSURE' },
  { scene: 5,  act:'ACT II',                title: 'SILICON CORE',           sub: 'ESP32-S3 SECURE PROCESSOR',             badge:'CLASSIFIED',  badgeColor:'rgba(200,220,255,0.45)' },

  // ACT III — THE SYSTEM
  { scene: 6,  act:'ACT III',               title: 'SOVEREIGN CORE',         sub: 'POST-QUANTUM VERIFIED',                 badge:'SOVEREIGN',   badgeColor:'rgba(0,200,255,0.55)' },
  { scene: 7,  act:'ACT III',               title: 'PRECISION ASSEMBLY',     sub: 'CRYPTOGRAPHIC INTEGRITY SEALED' },
  { scene: 8,  act:'ACT III',               title: 'ZERO NETWORK',           sub: 'AIR-GAPPED AUTHORITY · NO CLOUD · NO COMPROMISE' },

  // ACT IV — THE THREAT
  { scene: 9,  act:'ACT IV',                title: 'THREAT INTERCEPTED',     sub: 'QUANTUM ATTACK SURFACE: ZERO',          badge:'CRITICAL',    badgeColor:'rgba(255,80,40,0.70)' },
  { scene: 10, act:'ACT IV',                title: 'IMMUTABLE MEMORY',       sub: 'ZERO-KNOWLEDGE ACTIVE · ML-KEM-768' },

  // ACT V — IMMORTALITY
  { scene: 11, act:'ACT V',                 title: 'HARDWARE IMMORTALITY',   sub: 'CRYPTOGRAPHIC CONTINUITY PRESERVED',    badge:'SOVEREIGN',   badgeColor:'rgba(0,200,255,0.55)' },
  { scene: 12, act:'',                      title: 'Q-VAULT',                sub: 'THE HARDWARE NEVER LIES.' },
];

// ─────────────────────────────────────────────────────────────
export function CinematicTitles() {
  const activeScene = useExperienceStore((s) => s.activeScene);
  const prevScene   = useRef(-1);
  const [card, setCard]   = useState<TitleCard | null>(null);
  const [phase, setPhase] = useState<'hidden'|'enter'|'hold'|'exit'>('hidden');
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (activeScene === prevScene.current) return;
    prevScene.current = activeScene;
    timers.current.forEach(clearTimeout);
    timers.current = [];

    const found = CARDS.find((c) => c.scene === activeScene);
    if (!found || !found.title) {
      setPhase('exit');
      timers.current.push(setTimeout(() => setPhase('hidden'), 600));
      return;
    }

    // Commercial pacing: instant exit → fast enter → hold → exit
    setPhase('exit');
    timers.current.push(setTimeout(() => { setCard(found); setPhase('enter'); }, 250));
    timers.current.push(setTimeout(() => setPhase('hold'),  680));
    timers.current.push(setTimeout(() => setPhase('exit'),  2800));
    timers.current.push(setTimeout(() => setPhase('hidden'),3500));

    return () => timers.current.forEach(clearTimeout);
  }, [activeScene]);

  if (phase === 'hidden' || !card || !card.title) return null;

  const entering = phase === 'enter';
  const visible  = phase === 'hold';
  const isFinal  = card.scene === 12;
  const op       = entering ? 0 : visible ? 1 : 0;
  const ty       = entering ? 16 : visible ? 0 : -8;

  const trTitle = `opacity ${entering ? '0.45s' : '0.75s'} cubic-bezier(0.2,0,0.1,1),
                   transform ${entering ? '0.45s' : '0.75s'} cubic-bezier(0.2,0,0.1,1)`;
  const trSub   = `opacity ${entering ? '0.6s' : '0.9s'} cubic-bezier(0.25,0,0.1,1)`;
  const trAux   = `opacity ${entering ? '0.7s' : '1.0s'} cubic-bezier(0.25,0,0.1,1)`;

  return (
    <>
      {/* ── Act designation — top-left, barely there ──────────── */}
      {card.act && (
        <div aria-hidden style={{
          position:'fixed', top:'2rem', left:'2.4rem',
          display:'flex', alignItems:'center', gap:'0.6rem',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize:'0.50rem', letterSpacing:'0.30em',
          textTransform:'uppercase',
          color:'rgba(0,200,255,0.38)',
          opacity: entering ? 0 : visible ? 1 : 0,
          transition: trAux,
          pointerEvents:'none', userSelect:'none',
        }}>
          {card.act}
          {card.badge && card.badgeColor && (
            <span style={{
              border:`1px solid ${card.badgeColor}`,
              color: card.badgeColor,
              padding:'0.08rem 0.35rem',
              fontSize:'0.42rem',
              letterSpacing:'0.18em',
              borderRadius:'1px',
            }}>
              {card.badge}
            </span>
          )}
        </div>
      )}

      {/* ── MAIN TITLE — bottom center, dominant ──────────────── */}
      <div
        aria-live="polite"
        style={{
          position:'fixed',
          bottom: isFinal ? '50%' : '4.5rem',
          left:'50%',
          transform: `translateX(-50%) ${isFinal ? 'translateY(50%)' : ''} translateY(${ty}px)`,
          textAlign:'center',
          fontFamily:'var(--font-inter),system-ui,sans-serif',
          fontWeight: isFinal ? 100 : 200,
          fontSize: isFinal
            ? 'clamp(2.4rem,4vw,4rem)'
            : 'clamp(1.3rem,2.1vw,2.1rem)',
          letterSpacing: isFinal ? '0.55em' : '0.30em',
          textTransform:'uppercase',
          color: isFinal ? 'rgba(235,248,255,1.0)' : 'rgba(228,240,252,0.95)',
          opacity: op,
          transition: trTitle,
          pointerEvents:'none', userSelect:'none',
          whiteSpace:'nowrap',
        }}
      >
        {card.title}
      </div>

      {/* ── Sub-line — restrained technical copy ──────────────── */}
      {card.sub && (
        <div aria-hidden style={{
          position:'fixed',
          bottom: isFinal ? 'calc(50% - 3.5rem)' : '2.7rem',
          left:'50%',
          transform:'translateX(-50%)',
          textAlign:'center',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize: isFinal ? '0.70rem' : '0.58rem',
          letterSpacing:'0.20em',
          textTransform:'uppercase',
          color: isFinal ? 'rgba(0,200,255,0.70)' : 'rgba(0,200,255,0.48)',
          opacity: entering ? 0 : visible ? 0.9 : 0,
          transition: trSub,
          pointerEvents:'none', userSelect:'none',
        }}>
          {card.sub}
        </div>
      )}

      {/* ── Right-side progress bar ───────────────────────────── */}
      <div aria-hidden style={{
        position:'fixed', right:'1.8rem', top:'50%',
        transform:'translateY(-50%)',
        width:'1px', height:'100px',
        background:'rgba(255,255,255,0.05)',
        pointerEvents:'none',
      }}>
        <div style={{
          width:'100%',
          height:`${(activeScene / 12) * 100}%`,
          background:'rgba(0,200,255,0.30)',
          transition:'height 0.7s cubic-bezier(0.4,0,0.2,1)',
        }} />
      </div>
    </>
  );
}
