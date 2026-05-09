'use client';

// ═══════════════════════════════════════════════════════════════
// CINEMATIC TITLES — PHASE OMEGA: SOVEREIGN CINEMA
//
// Typography philosophy: "Fewer words. More weight."
//
// Each card = ONE emotional idea.
// Max 3 words in title. No filler.
// Typography serves the product. Never competes.
//
// Timing:
//   ACT I/II: enter at 0.3s, exit at 2.5s (short scenes)
//   ACT III:  enter at 0.4s, exit at 3.5s (hero scenes linger)
//   ACT IV:   enter at 0.2s, exit at 1.8s (RAPID — kinetic)
//   ACT V:    enter at 0.5s, exit at 4.0s (monumental hold)
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
  holdMs:      number;  // how long to hold before exit
  enterDelay:  number;  // ms before entering
}

// ── SOVEREIGN COPY — minimal, powerful, unforgettable ─────────
const CARDS: TitleCard[] = [
  // ── ACT I — THE SIGNAL
  { scene: 0,  title: '',                   sub: '',                                  holdMs:0,    enterDelay:300 },
  { scene: 1,  act:'I',  title:'FIRST CONTACT',       sub:'HARDWARE AUTHENTICATION INITIALIZING', badge:'BOOT',      badgeColor:'rgba(127,232,255,0.55)', holdMs:2400, enterDelay:300 },
  { scene: 2,  act:'I',  title:'THE SIGNAL',           sub:'SOVEREIGN HARDWARE DETECTED',          badge:'ACTIVE',    badgeColor:'rgba(127,232,255,0.50)', holdMs:2100, enterDelay:280 },
  { scene: 3,  act:'I',  title:'SURFACE SCAN',         sub:'IDENTITY INITIALIZING',                                                                         holdMs:2000, enterDelay:300 },

  // ── ACT II — ENGINEERED OBJECT
  { scene: 4,  act:'II', title:'PHYSICAL TRUST',       sub:'HARDWARE-BOUND IDENTITY',                                                                        holdMs:2500, enterDelay:280 },
  { scene: 5,  act:'II', title:'MACHINED PRECISION',   sub:'MILITARY-GRADE ENCLOSURE',                                                                       holdMs:2200, enterDelay:280 },
  { scene: 6,  act:'II', title:'SILICON CORE',         sub:'ESP32-S3 · CLASSIFIED ARCHITECTURE',  badge:'CLASSIFIED', badgeColor:'rgba(200,220,255,0.45)', holdMs:2500, enterDelay:280 },
  { scene: 7,  act:'II', title:'SOVEREIGN METAL',      sub:'BRUSHED TITANIUM · MILITARY-GRADE',                                                              holdMs:2800, enterDelay:280 },

  // ── ACT III — FULL REVEAL
  { scene: 8,  act:'III', title:'SOVEREIGN CORE',      sub:'POST-QUANTUM VERIFIED',               badge:'SOVEREIGN',  badgeColor:'rgba(127,232,255,0.65)', holdMs:3800, enterDelay:500, isHero:true },
  { scene: 9,  act:'III', title:'PRECISION ASSEMBLY',  sub:'CRYPTOGRAPHIC INTEGRITY SEALED',                                                                 holdMs:3200, enterDelay:400 },
  { scene: 10, act:'III', title:'ZERO NETWORK',        sub:'AIR-GAPPED · NO CLOUD · NO COMPROMISE',                                                          holdMs:3500, enterDelay:400 },

  // ── ACT IV — THE THREAT (RAPID CUTS — short holds)
  { scene: 11, act:'IV', title:'THREAT INTERCEPTED',  sub:'QUANTUM ATTACK SURFACE: ZERO',         badge:'CRITICAL',   badgeColor:'rgba(255,100,0,0.80)',   holdMs:1600, enterDelay:150 },
  { scene: 12, act:'IV', title:'UNSHAKEN',            sub:'ATTACK CONTAINED · HARDWARE SURVIVES',                                                            holdMs:1600, enterDelay:150 },
  { scene: 13, act:'IV', title:'ZERO KNOWLEDGE',      sub:'ML-KEM-768 · ACTIVE',                  badge:'SECURE',     badgeColor:'rgba(255,140,0,0.75)',   holdMs:1600, enterDelay:150 },
  { scene: 14, act:'IV', title:'CONTAINED',           sub:'THREAT NEUTRALIZED · DEVICE INTACT',                                                              holdMs:1600, enterDelay:150 },
  { scene: 15, act:'IV', title:'IMMUTABLE CORE',      sub:'ZERO-KNOWLEDGE SEALED · PQC ACTIVE',  badge:'CONFIRMED',  badgeColor:'rgba(127,232,255,0.70)', holdMs:1400, enterDelay:150 },

  // ── ACT V — IMMORTALITY
  { scene: 16, act:'V',  title:'HARDWARE IMMORTALITY',sub:'CRYPTOGRAPHIC CONTINUITY PRESERVED',  badge:'SOVEREIGN',  badgeColor:'rgba(127,232,255,0.65)', holdMs:4000, enterDelay:500 },
  { scene: 17, act:'V',  title:'THE DEVICE THAT',    sub:'OUTLIVES SYSTEMS',                                                                                holdMs:4500, enterDelay:500 },
  { scene: 18, act:'',   title:'Q-VAULT',            sub:'THE HARDWARE NEVER LIES.',                                                                         holdMs:8000, enterDelay:1200, isFinal:true },
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
      timers.current.push(setTimeout(() => setPhase('hidden'), 500));
      return;
    }

    const enterDelay = found.enterDelay;
    const holdEnd    = enterDelay + 380 + found.holdMs;

    setPhase('exit');
    timers.current.push(setTimeout(() => { setCard(found); setPhase('enter'); }, enterDelay));
    timers.current.push(setTimeout(() => setPhase('hold'),  enterDelay + 380));
    timers.current.push(setTimeout(() => setPhase('exit'),  holdEnd));
    timers.current.push(setTimeout(() => setPhase('hidden'), holdEnd + 600));

    return () => timers.current.forEach(clearTimeout);
  }, [activeScene]);

  if (phase === 'hidden' || !card || !card.title) return null;

  const entering = phase === 'enter';
  const visible  = phase === 'hold';
  const isFinal  = card.isFinal ?? false;
  const isHero   = card.isHero ?? false;
  const isThreat = activeScene >= 11 && activeScene <= 15;
  const op       = entering ? 0 : visible ? 1 : 0;
  const ty       = entering ? (isThreat ? 8 : 20) : visible ? 0 : (isThreat ? -8 : -12);

  // Threat: faster, more aggressive transition
  const dur      = isThreat ? '0.22s' : isFinal ? '0.9s' : isHero ? '0.55s' : '0.40s';
  const durOut   = isThreat ? '0.18s' : isFinal ? '1.1s' : '0.65s';
  const trTitle  = `opacity ${entering ? dur : durOut} cubic-bezier(0.2,0,0.1,1),
                    transform ${entering ? dur : durOut} cubic-bezier(0.2,0,0.1,1)`;
  const trSub    = `opacity ${entering ? dur : durOut} cubic-bezier(0.25,0,0.1,1)`;

  // Threat scenes: red/amber color override
  const titleColor  = isThreat
    ? (visible ? 'rgba(255,200,130,0.98)' : 'rgba(255,200,130,0)')
    : isFinal
    ? (visible ? 'rgba(235,248,255,1.0)'  : 'rgba(235,248,255,0)')
    : isHero
    ? (visible ? 'rgba(240,248,255,0.98)' : 'rgba(240,248,255,0)')
    : (visible ? 'rgba(228,240,252,0.95)' : 'rgba(228,240,252,0)');

  const subColor = isThreat
    ? (visible ? 'rgba(255,140,60,0.80)' : 'rgba(255,140,60,0)')
    : isFinal
    ? (visible ? 'rgba(127,232,255,0.75)' : 'rgba(127,232,255,0)')
    : (visible ? 'rgba(127,232,255,0.55)' : 'rgba(127,232,255,0)');

  const titleSize = isFinal
    ? 'clamp(2.8rem,4.5vw,4.5rem)'
    : isHero
    ? 'clamp(1.8rem,2.8vw,2.8rem)'
    : isThreat
    ? 'clamp(1.4rem,2.2vw,2.2rem)'
    : 'clamp(1.2rem,1.9vw,1.9rem)';

  const letterSpacing = isFinal ? '0.60em' : isHero ? '0.38em' : isThreat ? '0.22em' : '0.30em';
  const fontWeight    = isFinal ? 100 : isHero ? 200 : 300;

  return (
    <>
      {/* ── Act designation — top-left, barely there ─────────── */}
      {card.act && (
        <div aria-hidden style={{
          position:'fixed', top:'2rem', left:'2.4rem',
          display:'flex', alignItems:'center', gap:'0.7rem',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize:'0.48rem', letterSpacing:'0.32em',
          textTransform:'uppercase',
          color: isThreat ? 'rgba(255,120,40,0.55)' : 'rgba(127,232,255,0.38)',
          opacity: entering ? 0 : visible ? 1 : 0,
          transition: `opacity ${entering ? dur : durOut} ease`,
          pointerEvents:'none', userSelect:'none',
        }}>
          ACT {card.act}
          {card.badge && card.badgeColor && (
            <span style={{
              border:`1px solid ${card.badgeColor}`,
              color: card.badgeColor,
              padding:'0.06rem 0.32rem',
              fontSize:'0.40rem',
              letterSpacing:'0.20em',
              borderRadius:'1px',
            }}>
              {card.badge}
            </span>
          )}
        </div>
      )}

      {/* ── Thin horizontal rule — appears on hero/final ─────── */}
      {(isHero || isFinal) && (
        <div aria-hidden style={{
          position:'fixed',
          bottom: isFinal ? 'calc(50% + 3.2rem)' : '7.4rem',
          left:'50%', transform:'translateX(-50%)',
          width: entering ? '0px' : visible ? 'clamp(80px,12vw,140px)' : '0px',
          height:'1px',
          background:'rgba(127,232,255,0.25)',
          transition:`width ${entering ? '0.8s' : '0.5s'} cubic-bezier(0.4,0,0.2,1)`,
          pointerEvents:'none',
        }} />
      )}

      {/* ── MAIN TITLE — bottom center or final center ────────── */}
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
          transition: trTitle,
          pointerEvents:'none', userSelect:'none',
          whiteSpace:'nowrap',
          textShadow: isThreat
            ? '0 0 40px rgba(255,100,0,0.35)'
            : isHero || isFinal
            ? '0 0 60px rgba(127,232,255,0.18)'
            : 'none',
        }}
      >
        {card.title}
      </div>

      {/* ── Sub-line — sparse, technical copy ─────────────────── */}
      {card.sub && (
        <div aria-hidden style={{
          position:'fixed',
          bottom: isFinal ? 'calc(50% - 4.0rem)' : '2.6rem',
          left:'50%',
          transform:'translateX(-50%)',
          textAlign:'center',
          fontFamily:'var(--font-jetbrains),monospace',
          fontSize: isFinal ? '0.72rem' : isThreat ? '0.54rem' : '0.56rem',
          letterSpacing: isFinal ? '0.22em' : '0.18em',
          textTransform:'uppercase',
          color: subColor,
          opacity: entering ? 0 : visible ? 0.95 : 0,
          transition: trSub,
          pointerEvents:'none', userSelect:'none',
        }}>
          {card.sub}
        </div>
      )}

      {/* ── Scene progress indicator — right edge ─────────────── */}
      <div aria-hidden style={{
        position:'fixed', right:'1.6rem', top:'50%',
        transform:'translateY(-50%)',
        width:'1px', height:'90px',
        background:'rgba(255,255,255,0.04)',
        pointerEvents:'none',
      }}>
        <div style={{
          width:'100%',
          height:`${(activeScene / 18) * 100}%`,
          background: isThreat
            ? 'rgba(255,140,0,0.45)'
            : 'rgba(127,232,255,0.35)',
          transition:'height 0.6s cubic-bezier(0.4,0,0.2,1)',
        }} />
      </div>
    </>
  );
}
