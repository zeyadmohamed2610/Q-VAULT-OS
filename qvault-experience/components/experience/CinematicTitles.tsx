'use client';

// ═══════════════════════════════════════════════════════════════
// CINEMATIC TITLES — PHASE XL: PERFORMANCE RECONSTRUCTION
//
// 10-scene copy system. Zero JS animation overhead.
// Pure CSS transitions only.
// ═══════════════════════════════════════════════════════════════

import { useEffect, useRef, useState } from 'react';
import { useExperienceStore } from '@/lib/store';

interface TitleCard {
  scene:       number;
  act?:        string;
  title:       string;
  sub?:        string;
  badge?:      string;
  badgeColor?: string;
  isFinal?:    boolean;
  isHero?:     boolean;
  holdMs:      number;
  enterDelay:  number;
}

const CARDS: TitleCard[] = [
  { scene:0, title:'',              sub:'',                                    holdMs:0,    enterDelay:200 },
  { scene:1, act:'I',  title:'THE SIGNAL',       sub:'HARDWARE AUTHENTICATION INITIALIZING', badge:'BOOT',      badgeColor:'rgba(127,232,255,0.55)', holdMs:3000, enterDelay:400 },
  { scene:2, act:'II', title:'PHYSICAL TRUST',   sub:'HARDWARE-BOUND IDENTITY',              holdMs:2500, enterDelay:300 },
  { scene:3, act:'II', title:'SILICON CORE',     sub:'ESP32-S3 · CLASSIFIED ARCHITECTURE',  badge:'CLASSIFIED', badgeColor:'rgba(200,220,255,0.45)', holdMs:2500, enterDelay:300 },
  { scene:4, act:'II', title:'MACHINED PRECISION',sub:'MILITARY-GRADE ENCLOSURE',            holdMs:2200, enterDelay:300 },
  { scene:5, act:'II', title:'SOVEREIGN CORE',   sub:'POST-QUANTUM VERIFIED',               badge:'SOVEREIGN',  badgeColor:'rgba(127,232,255,0.65)', holdMs:3500, enterDelay:500, isHero:true },
  { scene:6, act:'III',title:'ZERO NETWORK',     sub:'AIR-GAPPED · NO CLOUD · NO COMPROMISE', holdMs:4500, enterDelay:400 },
  { scene:7, act:'III',title:'IMMUTABLE MEMORY', sub:'ZERO-KNOWLEDGE ACTIVE · ML-KEM-768',  badge:'SECURE',     badgeColor:'rgba(127,232,255,0.55)', holdMs:4000, enterDelay:400 },
  { scene:8, act:'IV', title:'PRECISION ASSEMBLY',sub:'CRYPTOGRAPHIC INTEGRITY SEALED',     holdMs:4000, enterDelay:400 },
  { scene:9, act:'',   title:'Q-VAULT',          sub:'THE HARDWARE NEVER LIES.',             holdMs:9000, enterDelay:1400, isFinal:true },
];

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
      timers.current.push(setTimeout(() => setPhase('hidden'), 450));
      return;
    }

    const enterDelay = found.enterDelay;
    const holdEnd    = enterDelay + 350 + found.holdMs;

    setPhase('exit');
    timers.current.push(setTimeout(() => { setCard(found); setPhase('enter'); }, enterDelay));
    timers.current.push(setTimeout(() => setPhase('hold'),  enterDelay + 350));
    timers.current.push(setTimeout(() => setPhase('exit'),  holdEnd));
    timers.current.push(setTimeout(() => setPhase('hidden'), holdEnd + 550));

    return () => timers.current.forEach(clearTimeout);
  }, [activeScene]);

  if (phase === 'hidden' || !card || !card.title) return null;

  const entering = phase === 'enter';
  const visible  = phase === 'hold';
  const isFinal  = card.isFinal ?? false;
  const isHero   = card.isHero ?? false;
  const op       = entering ? 0 : visible ? 1 : 0;
  const ty       = entering ? 18 : visible ? 0 : -10;

  const dur    = isFinal ? '0.9s' : isHero ? '0.55s' : '0.40s';
  const durOut = isFinal ? '1.1s' : '0.60s';
  const tr     = `opacity ${entering ? dur : durOut} cubic-bezier(0.2,0,0.1,1),
                  transform ${entering ? dur : durOut} cubic-bezier(0.2,0,0.1,1)`;

  const titleColor = isFinal
    ? 'rgba(235,248,255,1.0)'
    : isHero
    ? 'rgba(240,248,255,0.98)'
    : 'rgba(225,238,252,0.95)';

  const titleSize = isFinal
    ? 'clamp(2.8rem,4.5vw,4.5rem)'
    : isHero
    ? 'clamp(1.8rem,2.8vw,2.8rem)'
    : 'clamp(1.2rem,1.9vw,1.9rem)';

  const letterSpacing = isFinal ? '0.60em' : isHero ? '0.38em' : '0.30em';
  const fontWeight    = isFinal ? 100 : isHero ? 200 : 300;

  return (
    <>
      {/* Act label — top-left, minimal */}
      {card.act && (
        <div aria-hidden style={{
          position:'fixed', top:'2rem', left:'2.4rem',
          display:'flex', alignItems:'center', gap:'0.7rem',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize:'0.46rem', letterSpacing:'0.32em',
          textTransform:'uppercase',
          color:'rgba(127,232,255,0.35)',
          opacity: entering ? 0 : visible ? 1 : 0,
          transition:`opacity ${entering ? '0.5s' : '0.7s'} ease`,
          pointerEvents:'none', userSelect:'none',
        }}>
          {card.act && `ACT ${card.act}`}
          {card.badge && card.badgeColor && (
            <span style={{
              border:`1px solid ${card.badgeColor}`,
              color: card.badgeColor,
              padding:'0.06rem 0.30rem',
              fontSize:'0.38rem',
              letterSpacing:'0.20em',
              borderRadius:'1px',
            }}>
              {card.badge}
            </span>
          )}
        </div>
      )}

      {/* Decorative rule — hero + final only */}
      {(isHero || isFinal) && (
        <div aria-hidden style={{
          position:'fixed',
          bottom: isFinal ? 'calc(50% + 3.2rem)' : '7.4rem',
          left:'50%', transform:'translateX(-50%)',
          width: entering ? '0px' : visible ? 'clamp(80px,10vw,120px)' : '0px',
          height:'1px',
          background:'rgba(127,232,255,0.22)',
          transition:`width ${entering ? '0.9s' : '0.5s'} cubic-bezier(0.4,0,0.2,1)`,
          pointerEvents:'none',
        }} />
      )}

      {/* Main title */}
      <div
        aria-live="polite"
        style={{
          position:'fixed',
          bottom: isFinal ? '50%' : '4.5rem',
          left:'50%',
          transform:`translateX(-50%) ${isFinal ? 'translateY(50%)' : ''} translateY(${ty}px)`,
          textAlign:'center',
          fontFamily:'var(--font-inter),system-ui,sans-serif',
          fontWeight,
          fontSize: titleSize,
          letterSpacing,
          textTransform:'uppercase',
          color: titleColor,
          opacity: op,
          transition: tr,
          pointerEvents:'none', userSelect:'none',
          whiteSpace:'nowrap',
          textShadow: isHero || isFinal
            ? '0 0 50px rgba(127,232,255,0.15)'
            : 'none',
        }}
      >
        {card.title}
      </div>

      {/* Sub-line */}
      {card.sub && (
        <div aria-hidden style={{
          position:'fixed',
          bottom: isFinal ? 'calc(50% - 3.8rem)' : '2.6rem',
          left:'50%',
          transform:'translateX(-50%)',
          textAlign:'center',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize: isFinal ? '0.68rem' : '0.55rem',
          letterSpacing: isFinal ? '0.22em' : '0.18em',
          textTransform:'uppercase',
          color: isFinal
            ? 'rgba(127,232,255,0.72)'
            : 'rgba(127,232,255,0.50)',
          opacity: entering ? 0 : visible ? 0.95 : 0,
          transition:`opacity ${entering ? '0.6s' : '0.75s'} ease`,
          pointerEvents:'none', userSelect:'none',
        }}>
          {card.sub}
        </div>
      )}

      {/* Scene progress bar — right edge */}
      <div aria-hidden style={{
        position:'fixed', right:'1.6rem', top:'50%',
        transform:'translateY(-50%)',
        width:'1px', height:'80px',
        background:'rgba(255,255,255,0.04)',
        pointerEvents:'none',
      }}>
        <div style={{
          width:'100%',
          height:`${(activeScene / 9) * 100}%`,
          background:'rgba(127,232,255,0.30)',
          transition:'height 0.6s cubic-bezier(0.4,0,0.2,1)',
        }} />
      </div>
    </>
  );
}
