import React, { useId, useMemo } from 'react';
import { rngFrom, hashString } from './engine.js';
import { Artwork } from '../components/Artwork.jsx';

/* ------------------------------------------------------------------
   Typography helpers
------------------------------------------------------------------- */

const SERIF = "'Instrument Serif', 'Times New Roman', Georgia, serif";
const GROTESK = "'Space Grotesk', 'Helvetica Neue', Arial, sans-serif";

export const FONT_SERIF = SERIF;
export const FONT_GROTESK = GROTESK;

function fitFont(text = '', max = 68, per = 0.6, track = 0.12) {
  const w = Math.max(1, text.length);
  const size = max / (w * (per + track));
  return Math.max(4, Math.min(18, size));
}

/** Text wrapped around a circle, drawn character by character. */
function CurvedText({
  text = '', cx = 50, cy = 50, radius = 36, fontSize = 6, letterSpacing = 0.18,
  fill = '#111', flip = false, family = GROTESK, weight = 500, opacity = 1,
}) {
  const chars = useMemo(() => {
    const arr = [...text];
    const widths = arr.map((c) => (c === ' ' ? fontSize * 0.42 : fontSize * 0.58) + letterSpacing);
    const total = widths.reduce((a, b) => a + b, 0);
    let acc = 0;
    return arr.map((c, i) => {
      const mid = acc + widths[i] / 2;
      acc += widths[i];
      const angle = (flip ? 90 : -90) + ((mid - total / 2) / radius) * (180 / Math.PI) * (flip ? -1 : 1);
      const rad = (angle * Math.PI) / 180;
      return {
        c,
        x: cx + radius * Math.cos(rad),
        y: cy + radius * Math.sin(rad),
        angle: angle + (flip ? -90 : 90),
      };
    });
  }, [text, cx, cy, radius, fontSize, letterSpacing, flip]);

  return (
    <g fontFamily={family} fontSize={fontSize} fontWeight={weight} fill={fill} opacity={opacity} textAnchor="middle">
      {chars.map((ch, i) =>
        ch.c.trim() ? (
          <text key={i} x={ch.x} y={ch.y} transform={`rotate(${ch.angle} ${ch.x} ${ch.y})`}
            dominantBaseline="middle">{ch.c}</text>
        ) : null
      )}
    </g>
  );
}

/* ------------------------------------------------------------------
   Glyph geometry
------------------------------------------------------------------- */

function Glyph({ g, fill = '#111', cx = 50, cy = 50, scale = 1 }) {
  const R = (g.radius || 0.3) * 100 * scale;
  const n = g.fold || 5;
  const sw = Math.max(0.25, (g.weight || 0.02) * 100 * scale);
  const nodes = [];
  const density = g.density || 3;

  for (let i = 0; i < n; i++) {
    const a = (360 / n) * i + (g.spin || 0);
    const t = `rotate(${a})`;
    const k = i;
    switch (g.motif) {
      case 'blades':
        nodes.push(
          <path key={k} transform={t} fill={fill} opacity={i % 2 ? 0.85 : 1}
            d={`M0 ${-R} L${R * 0.26} ${-R * 0.2} L0 ${-R * 0.42} L${-R * 0.26} ${-R * 0.2} Z`} />
        );
        break;
      case 'orbits':
        nodes.push(
          <ellipse key={k} transform={t} cx="0" cy={-R * 0.6} rx={R * 0.3} ry={R * 0.44}
            fill="none" stroke={fill} strokeWidth={sw * 1.2} />
        );
        break;
      case 'chevrons':
        nodes.push(
          <path key={k} transform={`translate(0 ${-R * 0.12}) ${t}`} fill="none" stroke={fill}
            strokeWidth={sw * 1.5} strokeLinecap="square"
            d={`M${-R * 0.56} ${R * 0.16} L0 ${-R * 0.5} L${R * 0.56} ${R * 0.16}`} />
        );
        break;
      case 'spikes':
        nodes.push(
          <g key={k} transform={t}>
            <line x1="0" y1={-R * 0.3} x2="0" y2={-R * (i % 2 ? 0.72 : 1)} stroke={fill} strokeWidth={sw} strokeLinecap="round" />
          </g>
        );
        break;
      case 'grid': {
        const cells = density + 1;
        const step = (R * 1.5) / cells;
        for (let x = 0; x < cells; x++) {
          for (let y = 0; y < cells; y++) {
            const px = (x - (cells - 1) / 2) * step;
            const py = (y - (cells - 1) / 2) * step;
            const dist = Math.hypot(px, py);
            if (dist < step * 0.55 || dist > R * 1.15) continue;
            nodes.push(<circle key={`${k}-${x}-${y}`} cx={px} cy={py} r={sw * 1.1} fill={fill} />);
          }
        }
        break;
      }
      case 'lattice': {
        const sides = g.fold > 6 ? 6 : g.fold > 4 ? 5 : 4;
        const pts = Array.from({ length: sides }, (_, j) => {
          const ang = (Math.PI * 2 * j) / sides - Math.PI / 2;
          return `${(Math.cos(ang) * R).toFixed(2)} ${(Math.sin(ang) * R).toFixed(2)}`;
        }).join(' ');
        nodes.push(<polygon key={k} transform={t} points={pts} fill="none" stroke={fill} strokeWidth={sw * 0.9} />);
        break;
      }
      case 'petals':
        nodes.push(
          <ellipse key={k} transform={t} cx="0" cy={-R * 0.5} rx={R * 0.19} ry={R * 0.46}
            fill={g.solid ? fill : 'none'} stroke={fill} strokeWidth={sw * 0.9} />
        );
        break;
      case 'arrows':
      default:
        nodes.push(
          <path key={k} transform={t} fill="none" stroke={fill} strokeWidth={sw * 1.3} strokeLinejoin="miter"
            d={`M${-R * 0.4} ${-R * 0.06} L0 ${-R * 0.8} L${R * 0.4} ${-R * 0.06}`} />
        );
    }
  }

  const centre = ['orbits', 'spikes', 'chevrons', 'lattice'].includes(g.motif);
  return (
    <g transform={`translate(${cx} ${cy})`}>
      {nodes}
      {centre && <circle r={R * 0.14} fill={fill} />}
      {!centre && g.motif !== 'grid' && <circle r={R * 0.07} fill={fill} />}
    </g>
  );
}

/* ------------------------------------------------------------------
   Logo mark
------------------------------------------------------------------- */

export function LogoMark({ mark, size = 320, className = '', wash = 0, seedOffset = 0, title, background = false }) {
  const raw = useId();
  const uid = raw.replace(/[:]/g, '');
  const maskId = `lm-${uid}-${seedOffset}`;
  if (!mark) return null;

  const ink = mark.invert ? '#f7f7f2' : mark.ink || '#111110';
  const bg = mark.invert ? '#0b0b0b' : 'transparent';
  const { glyph, type, frame, brand, style } = mark;
  const name = brand || 'JARVIS';
  const track = type.tracking ?? 0.15;
  const family = type.family === 'serif' ? SERIF : GROTESK;
  const approx = type.family === 'serif' ? 0.48 : 0.62;
  const tagline = mark.tagline || '';

  const holes = useMemo(() => {
    if (!wash || wash < 0.02) return [];
    const r = rngFrom((mark.seed || 1) + seedOffset * 31);
    const count = Math.round(wash * 150);
    return Array.from({ length: count }, () => ({
      cx: r.range(2, 98),
      cy: r.range(2, 98),
      r: r.range(0.35, 1.9) * (0.6 + wash),
      o: r.range(0.45, 1),
    }));
  }, [mark.seed, wash, seedOffset]);

  let content = null;

  if (style === 'wordmark') {
    const fs = Math.min(18, fitFont(name, 82, approx, track));
    content = (
      <>
        <line x1="16" y1="22" x2="84" y2="22" stroke={ink} strokeWidth="0.6" opacity="0.9" />
        <Glyph g={glyph} fill={ink} scale={0.28} cy={34} />
        <text x="50" y="62" textAnchor="middle" fontFamily={family} fontSize={fs} fill={ink}
          letterSpacing={track * fs}>{type.caps ? name : name.toLowerCase()}</text>
        <line x1="16" y1="69" x2="84" y2="69" stroke={ink} strokeWidth="0.6" opacity="0.9" />
        {tagline && (
          <text x="50" y="80" textAnchor="middle" fontFamily={GROTESK} fontSize="3.4" fill={ink}
            letterSpacing="1.4" opacity="0.8">{tagline}</text>
        )}
      </>
    );
  } else if (style === 'monogram') {
    const clean = name.replace(/[^A-Z0-9]/gi, '') || name;
    const first = clean[0] || 'J';
    const second = clean[1] || clean[0] || 'V';
    content = (
      <>
        <text x="44" y="52" textAnchor="middle" fontFamily={SERIF} fontSize="44" fill={ink} opacity="0.22">{first}</text>
        <text x="58" y="66" textAnchor="middle" fontFamily={SERIF} fontSize="44" fill={ink}>{second}</text>
        <line x1="32" y1="75" x2="68" y2="75" stroke={ink} strokeWidth="0.7" />
        <text x="50" y="84" textAnchor="middle" fontFamily={GROTESK} fontSize="4" fill={ink}
          letterSpacing="1.5">{name}</text>
      </>
    );
  } else if (style === 'badge' || style === 'seal') {
    const double = frame === 'double-circle' || style === 'seal';
    const look = frame === 'rounded' && style === 'badge';
    content = (
      <>
        {look ? (
          <>
            <rect x="8" y="8" width="84" height="84" rx="12" fill="none" stroke={ink} strokeWidth="1.4" />
            <rect x="12.5" y="12.5" width="75" height="75" rx="8.5" fill="none" stroke={ink} strokeWidth="0.5" />
          </>
        ) : (
          <>
            <circle cx="50" cy="50" r="45" fill="none" stroke={ink} strokeWidth={double ? 1.1 : 1.5} />
            {double && <circle cx="50" cy="50" r="40.6" fill="none" stroke={ink} strokeWidth="0.6" />}
            <circle cx="50" cy="50" r="33" fill="none" stroke={ink} strokeWidth="0.45" opacity="0.75" />
          </>
        )}
        <CurvedText text={name} cx="50" cy="50" radius={look ? 37 : 36.2}
          fontSize={Math.min(6.6, fitFont(name, look ? 56 : 58, 0.66, 0.22))}
          letterSpacing={0.18} fill={ink} />
        <CurvedText text={`· ${tagline || 'ORIGINAL'} ·`} cx="50" cy="50" radius={look ? 37 : 36.2}
          fontSize="3.2" letterSpacing="0.3" fill={ink} flip opacity={0.9} />
        <Glyph g={glyph} fill={ink} scale={0.42} cy={50} />
      </>
    );
  } else if (style === 'emblem') {
    const shield = frame === 'shield' || frame === undefined;
    const outer = shield
      ? 'M50 7 L86 19 L86 51 C86 70 68 84 50 91 C32 84 14 70 14 51 L14 19 Z'
      : 'M50 6 L88 28 L88 72 L50 94 L12 72 L12 28 Z';
    const inner = shield
      ? 'M50 13 L80 23 L80 51 C80 65 66 77 50 84 C34 77 20 65 20 51 L20 23 Z'
      : 'M50 12 L82 30 L82 70 L50 88 L18 70 L18 30 Z';
    content = (
      <>
        <path d={outer} fill="none" stroke={ink} strokeWidth="1.5" strokeLinejoin="round" />
        <path d={inner} fill="none" stroke={ink} strokeWidth="0.45" opacity="0.8" strokeLinejoin="round" />
        <Glyph g={glyph} fill={ink} scale={0.36} cy={40} />
        <line x1="32" y1="62" x2="68" y2="62" stroke={ink} strokeWidth="0.4" opacity="0.8" />
        <text x="50" y="74" textAnchor="middle" fontFamily={GROTESK} fontSize={Math.min(6.4, fitFont(name, 54, 0.66, 0.18))}
          fill={ink} letterSpacing="1.7">{name}</text>
      </>
    );
  } else if (style === 'gothic') {
    content = (
      <>
        <path d="M50 5 L50 15 M44.5 10 L55.5 10" stroke={ink} strokeWidth="1.3" strokeLinecap="square" />
        <path d="M27 92 L27 45 C27 26 37 15 50 15 C63 15 73 26 73 45 L73 92" fill="none" stroke={ink} strokeWidth="1.2" />
        <path d="M33 92 L33 47 C33 32 40 21 50 21 C60 21 67 32 67 47 L67 92" fill="none" stroke={ink} strokeWidth="0.45" opacity="0.85" />
        <Glyph g={glyph} fill={ink} scale={0.34} cy={48} />
        <line x1="38" y1="66" x2="62" y2="66" stroke={ink} strokeWidth="0.5" opacity="0.8" />
        <text x="50" y="79" textAnchor="middle" fontFamily={SERIF} fontSize={Math.min(7.6, fitFont(name, 44, 0.46, 0.22))}
          fill={ink} letterSpacing="2.2">{name}</text>
        <text x="50" y="88" textAnchor="middle" fontFamily={GROTESK} fontSize="2.8" fill={ink}
          letterSpacing="1.2" opacity="0.85">{tagline}</text>
      </>
    );
  } else if (style === 'minimal') {
    content = (
      <>
        <Glyph g={glyph} fill={ink} scale={0.42} cy={37} />
        <text x="50" y="69" textAnchor="middle" fontFamily={GROTESK} fontSize={Math.min(9, fitFont(name, 80, 0.68, 0.34))}
          fill={ink} letterSpacing={3.4} fontWeight="400">{name.toLowerCase()}</text>
        <line x1="44" y1="77" x2="56" y2="77" stroke={ink} strokeWidth="0.6" />
      </>
    );
  } else if (style === 'brutal') {
    const words = name.length > 8
      ? [name.slice(0, Math.ceil(name.length / 2)), name.slice(Math.ceil(name.length / 2))]
      : [name];
    content = (
      <>
        <rect x="8" y="12" width="84" height="6" fill={ink} />
        <Glyph g={glyph} fill={ink} scale={0.24} cy={35} />
        <text x="50" y={words.length > 1 ? 57 : 64} textAnchor="middle" fontFamily={GROTESK}
          fontSize={words.length > 1 ? 17 : Math.min(24, fitFont(name, 84, 0.72, 0))}
          fontWeight="700" fill={ink} letterSpacing="-0.4">
          {words.map((w, i) => <tspan key={i} x="50" dy={i === 0 ? 0 : 17}>{w}</tspan>)}
        </text>
        <rect x="8" y="82" width="84" height="1.4" fill={ink} />
      </>
    );
  } else {
    const fs = Math.min(18, fitFont(name, 82, approx, track));
    content = (
      <text x="50" y="56" textAnchor="middle" fontFamily={family} fontSize={fs} fill={ink}
        letterSpacing={track * fs}>{name}</text>
    );
  }

  const hasBg = background || mark.invert;

  return (
    <svg viewBox="0 0 100 100" width={size} height={size} className={className}
      role="img" aria-label={title || `${name} logo`} style={{ display: 'block', overflow: 'visible' }}>
      <title>{title || `${name} logo`}</title>
      <defs>
        <mask id={maskId}>
          <rect width="100" height="100" fill="#fff" />
          {holes.map((h, i) => (
            <circle key={i} cx={h.cx} cy={h.cy} r={h.r} fill="#000" opacity={h.o} />
          ))}
        </mask>
      </defs>
      {hasBg && <rect width="100" height="100" fill={bg === 'transparent' ? '#fff' : bg} />}
      <g mask={wash ? `url(#${maskId})` : undefined}>{content}</g>
    </svg>
  );
}

/* ------------------------------------------------------------------
   Garment flats — 800 × 900 artboard
------------------------------------------------------------------- */

export const GARMENT_PATHS = {
  hoodie: 'M400 176 C356 176 330 184 316 198 L214 224 C180 234 156 258 148 292 L128 604 C124 630 138 650 164 652 L222 652 C246 652 260 636 260 612 L262 430 L262 690 C262 708 274 720 292 720 L508 720 C526 720 538 708 538 690 L538 430 L540 612 C540 636 554 652 578 652 L636 652 C662 650 676 630 672 604 L652 292 C644 258 620 234 586 224 L484 198 C470 184 444 176 400 176 Z',
  tee: 'M400 170 C354 170 328 180 314 194 L214 220 C180 232 152 258 142 292 L120 430 C114 456 128 476 156 476 L232 476 C252 476 264 462 264 442 L266 706 C266 724 278 736 296 736 L504 736 C522 736 534 724 534 706 L536 442 C536 462 548 476 568 476 L644 476 C672 476 686 456 680 430 L658 292 C648 258 620 232 586 220 L486 194 C472 180 446 170 400 170 Z',
  crew: 'M400 168 C354 168 328 178 316 192 L216 220 C182 232 156 256 146 290 L124 588 C118 614 132 634 160 634 L222 634 C244 634 258 618 258 596 L264 424 L264 664 C264 682 276 694 294 694 L506 694 C524 694 536 682 536 664 L536 424 L542 596 C542 618 556 634 578 634 L640 634 C668 634 682 614 676 588 L654 290 C644 256 618 232 584 220 L484 192 C472 178 446 168 400 168 Z',
  longsleeve: 'M400 170 C356 170 330 180 318 194 L218 222 C184 234 158 260 148 294 L112 660 C106 686 120 706 148 706 L210 706 C232 706 246 690 246 668 L262 436 L266 716 C266 734 278 746 296 746 L504 746 C522 746 534 734 534 716 L538 436 L554 668 C554 690 568 706 590 706 L652 706 C680 706 694 686 688 660 L652 294 C642 260 616 234 582 222 L482 194 C470 180 444 170 400 170 Z',
  bomber: 'M400 172 C356 172 332 182 320 196 L212 222 C178 234 152 258 142 292 L118 548 C112 574 126 594 154 594 L228 594 C250 594 262 578 262 556 L266 452 L266 640 L534 640 L534 452 L538 556 C538 578 550 594 572 594 L646 594 C674 594 688 574 682 548 L658 292 C648 258 622 234 588 222 L480 196 C468 182 444 172 400 172 Z',
  cargo: 'M268 200 L532 200 L532 252 C528 306 512 344 512 404 L516 690 C516 708 504 720 486 720 L424 720 C408 720 398 708 398 692 L400 486 L402 692 C402 708 392 720 376 720 L314 720 C296 720 284 708 284 690 L288 404 C288 344 272 306 268 252 Z',
  shorts: 'M268 200 L532 200 L532 252 C528 300 512 330 512 380 L514 486 C514 504 502 516 484 516 L424 516 C408 516 398 504 398 488 L400 374 L402 488 C402 504 392 516 376 516 L314 516 C296 516 284 504 284 486 L288 380 C288 330 272 300 268 252 Z',
  cap: 'M258 566 C258 392 320 302 400 302 C480 302 542 392 542 566 Z',
};

export const GARMENT_EXTRA = {
  hoodie: 'M316 200 C296 148 306 90 344 68 C360 58 380 74 400 74 C420 74 440 58 456 68 C494 90 504 148 484 200 C460 214 340 214 316 200 Z',
  cap: 'M538 508 C620 500 692 536 706 578 C660 604 570 594 532 560 Z',
  tee: '',
  crew: '',
  longsleeve: '',
  bomber: '',
  cargo: '',
  shorts: '',
};

export function GarmentShape({ garment = 'tee', fill = '#232322', stroke = 'rgba(255,255,255,0.14)' }) {
  const d = GARMENT_PATHS[garment] || GARMENT_PATHS.tee;
  return <path d={d} fill={fill} stroke={stroke} strokeWidth="2" strokeLinejoin="round" />;
}

function Details({ garment, ink, dim }) {
  const thin = { stroke: dim, fill: 'none', strokeWidth: 2, strokeLinecap: 'round' };
  const hair = { stroke: dim, fill: 'none', strokeWidth: 1.3, strokeLinecap: 'round', opacity: 0.8 };
  const heavy = { stroke: dim, fill: 'none', strokeWidth: 2.6, strokeLinecap: 'round' };

  if (garment === 'hoodie') {
    return (
      <g>
        <path d="M318 198 C330 246 360 268 400 268 C440 268 470 246 482 198"
          fill="rgba(0,0,0,0.32)" stroke={dim} strokeWidth="2.2" />
        <path d="M330 204 C342 246 368 262 400 262 C432 262 458 246 470 204" {...hair} />
        <path d="M368 258 C364 310 358 356 352 404" stroke={ink} strokeWidth="7" strokeLinecap="round" />
        <path d="M432 258 C436 306 442 348 448 378" stroke={ink} strokeWidth="7" strokeLinecap="round" />
        <rect x="345" y="402" width="14" height="26" rx="5" fill={ink} />
        <rect x="441" y="376" width="14" height="26" rx="5" fill={ink} />
        <path d="M316 476 L484 476 L484 636 C484 648 476 656 464 656 L336 656 C324 656 316 648 316 636 Z"
          fill="rgba(0,0,0,0.15)" stroke={dim} strokeWidth="2" strokeLinejoin="round" />
        <path d="M316 628 L484 628" {...hair} />
        <path d="M266 688 L534 688" {...heavy} />
        <path d="M130 606 L254 606" {...heavy} />
        <path d="M546 606 L670 606" {...heavy} />
        <path d="M150 296 C190 300 230 316 258 346" {...hair} />
        <path d="M650 296 C610 300 570 316 542 346" {...hair} />
      </g>
    );
  }
  if (garment === 'crew') {
    return (
      <g>
        <path d="M318 194 C330 240 360 262 400 262 C440 262 470 240 482 194"
          fill="rgba(0,0,0,0.26)" stroke={dim} strokeWidth="2.2" />
        <path d="M330 200 C342 240 368 256 400 256 C432 256 458 240 470 200" {...hair} />
        <path d="M332 190 C346 228 370 244 400 244 C430 244 454 228 468 190" {...hair} opacity="0.5" />
        <path d="M266 662 L534 662" {...heavy} />
        <path d="M130 560 L254 560" {...heavy} />
        <path d="M546 560 L670 560" {...heavy} />
        <path d="M152 306 C200 330 236 380 252 452" {...hair} opacity="0.5" />
        <path d="M648 306 C600 330 564 380 548 452" {...hair} opacity="0.5" />
        <path d="M268 300 C266 460 266 560 266 640" {...hair} opacity="0.4" />
      </g>
    );
  }
  if (garment === 'tee') {
    return (
      <g>
        <path d="M316 196 C328 240 358 262 400 262 C442 262 472 240 484 196"
          fill="rgba(0,0,0,0.22)" stroke={dim} strokeWidth="2.2" />
        <path d="M328 202 C340 240 366 256 400 256 C434 256 460 240 472 202" {...hair} />
        <path d="M268 704 L532 704" {...heavy} />
        <path d="M132 434 L254 434" {...heavy} />
        <path d="M546 434 L668 434" {...heavy} />
        <path d="M158 300 C196 320 232 356 250 404" {...hair} opacity="0.5" />
        <path d="M642 300 C604 320 568 356 550 404" {...hair} opacity="0.5" />
        <path d="M532 470 L532 700" {...hair} opacity="0.35" />
      </g>
    );
  }
  if (garment === 'longsleeve') {
    return (
      <g>
        <path d="M318 196 C330 240 358 262 400 262 C442 262 470 240 482 196"
          fill="rgba(0,0,0,0.22)" stroke={dim} strokeWidth="2.2" />
        <path d="M330 202 C342 240 368 256 400 256 C432 256 458 240 470 202" {...hair} />
        <path d="M268 714 L532 714" {...heavy} />
        <path d="M118 630 L246 630" {...heavy} />
        <path d="M554 630 L682 630" {...heavy} />
        <path d="M152 306 C198 340 238 470 244 630" {...hair} opacity="0.5" />
        <path d="M648 306 C602 340 562 470 556 630" {...hair} opacity="0.5" />
      </g>
    );
  }
  if (garment === 'bomber') {
    return (
      <g>
        <path d="M320 196 C340 168 460 168 480 196 L480 218 C456 238 344 238 320 218 Z"
          fill="rgba(0,0,0,0.26)" stroke={dim} strokeWidth="2" strokeLinejoin="round" />
        <path d="M334 206 L466 206" {...hair} />
        <line x1="400" y1="238" x2="400" y2="640" stroke={dim} strokeWidth="3" />
        <circle cx="400" cy="252" r="7" fill={ink} />
        <rect x="266" y="596" width="268" height="44" rx="5" fill="rgba(0,0,0,0.22)" stroke={dim} strokeWidth="2" />
        <path d="M266 618 L534 618" {...hair} />
        <path d="M126 588 L252 588" {...heavy} />
        <path d="M548 588 L674 588" {...heavy} />
        <rect x="300" y="392" width="74" height="16" rx="4" fill="rgba(0,0,0,0.18)" stroke={dim} strokeWidth="1.6" />
        <rect x="426" y="392" width="74" height="16" rx="4" fill="rgba(0,0,0,0.18)" stroke={dim} strokeWidth="1.6" />
        <path d="M300 480 L360 520" {...hair} opacity="0.5" />
        <path d="M500 480 L440 520" {...hair} opacity="0.5" />
        <path d="M148 300 C186 314 220 336 248 366" {...hair} />
        <path d="M652 300 C614 314 580 336 552 366" {...hair} />
      </g>
    );
  }
  if (garment === 'cargo' || garment === 'shorts') {
    const bottom = garment === 'cargo';
    return (
      <g>
        <rect x="268" y="200" width="264" height="46" fill="rgba(0,0,0,0.2)" stroke={dim} strokeWidth="2" />
        <path d="M268 224 L532 224" {...hair} />
        <line x1="400" y1="246" x2="400" y2="300" {...hair} />
        <circle cx="400" cy="216" r="5" fill={ink} />
        <rect x="286" y={bottom ? 300 : 272} width="60" height={bottom ? 100 : 66} rx="5"
          fill="rgba(0,0,0,0.16)" stroke={dim} strokeWidth="1.8" />
        <rect x="454" y={bottom ? 300 : 272} width="60" height={bottom ? 100 : 66} rx="5"
          fill="rgba(0,0,0,0.16)" stroke={dim} strokeWidth="1.8" />
        <path d={`M290 ${bottom ? 322 : 294} L342 ${bottom ? 322 : 294}`} {...hair} />
        <path d={`M458 ${bottom ? 322 : 294} L510 ${bottom ? 322 : 294}`} {...hair} />
        <line x1="288" y1={bottom ? 688 : 480} x2="512" y2={bottom ? 688 : 480} {...heavy} />
        <path d={`M402 ${bottom ? 486 : 356} L402 ${bottom ? 660 : 460}`} {...hair} />
        <path d={`M290 300 L290 ${bottom ? 660 : 460}`} {...hair} opacity="0.35" />
      </g>
    );
  }
  if (garment === 'cap') {
    return (
      <g>
        <path d="M258 546 C300 562 500 562 542 546" fill="rgba(0,0,0,0.2)" stroke={dim} strokeWidth="2" />
        <path d="M400 302 L400 566" {...hair} />
        <path d="M322 340 C300 400 288 480 286 552" {...hair} opacity="0.7" />
        <path d="M478 340 C500 400 512 480 514 552" {...hair} opacity="0.7" />
        <path d="M360 312 C340 390 330 480 328 552" {...hair} opacity="0.4" />
        <path d="M440 312 C460 390 470 480 472 552" {...hair} opacity="0.4" />
        <circle cx="400" cy="306" r="10" fill={ink} />
        <circle cx="330" cy="440" r="4" fill={dim} />
        <circle cx="470" cy="440" r="4" fill={dim} />
      </g>
    );
  }
  return null;
}

/* ------------------------------------------------------------------
   Mockup
------------------------------------------------------------------- */

export const COLOR_FILLS = {
  'washed-black': { base: '#2a2a28', light: '#3a3a37', dark: '#141413', isLight: false },
  ink: { base: '#101010', light: '#1e1e1e', dark: '#000000', isLight: false },
  charcoal: { base: '#4b4b48', light: '#5c5c58', dark: '#2c2c2a', isLight: false },
  grey: { base: '#a8a8a2', light: '#bcbcb6', dark: '#85857f', isLight: true },
  bone: { base: '#d8d4c8', light: '#e6e3d9', dark: '#b8b3a6', isLight: true },
  ivory: { base: '#eeece6', light: '#f8f7f3', dark: '#d2cfc6', isLight: true },
};

export function GarmentMockup({
  garment = 'hoodie', colorway = 'washed-black', mark, ink, placement = 'chest',
  scale = 'medium', wash = 0.16, invert = false, className = '', showShadow = true,
  withGrain = true, size, artSpec = null,
}) {
  const raw = useId();
  const uid = raw.replace(/[:]/g, '');
  const color = COLOR_FILLS[colorway] || COLOR_FILLS['washed-black'];
  const light = color.isLight;
  const printInk = invert ? (light ? '#111110' : '#f3f3ee') : ink || (light ? '#111110' : '#f4f4ef');
  const zone = {
    chest: { x: 400, y: garment === 'cap' ? 440 : 420, s: garment === 'cargo' || garment === 'shorts' ? 180 : 220 },
    back: { x: 400, y: 430, s: 310 },
    sleeve: { x: garment === 'cargo' || garment === 'shorts' ? 400 : 590, y: 330, s: 110 },
  }[placement] || { x: 400, y: 380, s: 230 };
  const sizeMul = { small: 0.66, medium: 1, large: 1.32 }[scale] || 1;
  const markSize = zone.s * sizeMul;
  const isBottom = garment === 'cargo' || garment === 'shorts';
  const isCap = garment === 'cap';
  const dim = light ? 'rgba(0,0,0,0.26)' : 'rgba(255,255,255,0.3)';

  return (
    <svg viewBox="0 0 800 900" width={size} height={size ? (size * 900) / 800 : undefined}
      className={`gm ${className}`} role="img" aria-label={`${garment} mockup`}>
      <defs>
        <linearGradient id={`fab-${uid}`} x1="0.15" y1="0" x2="0.7" y2="1">
          <stop offset="0%" stopColor={color.light} />
          <stop offset="45%" stopColor={color.base} />
          <stop offset="100%" stopColor={color.dark} />
        </linearGradient>
        <radialGradient id={`sheen-${uid}`} cx="0.34" cy="0.26" r="0.68">
          <stop offset="0%" stopColor="#fff" stopOpacity={light ? 0.55 : 0.14} />
          <stop offset="70%" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`shade-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#000" stopOpacity="0.16" />
          <stop offset="30%" stopColor="#000" stopOpacity="0" />
          <stop offset="70%" stopColor="#000" stopOpacity="0" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.2" />
        </linearGradient>
        <filter id={`soft-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="16" />
        </filter>
        <mask id={`print-${uid}`}>
          <rect width="800" height="900" fill="#fff" />
          {wash > 0.02 && <rect width="800" height="900" fill="#000" opacity={Math.min(0.62, 0.1 + wash * 0.8)}
            style={{ mixBlendMode: 'multiply' }} />}
        </mask>
        <clipPath id={`clip-${uid}`}>
          <path d={GARMENT_PATHS[garment] || GARMENT_PATHS.tee} />
          {GARMENT_EXTRA[garment] ? <path d={GARMENT_EXTRA[garment]} /> : null}
        </clipPath>
        <pattern id={`grain-${uid}`} width="4" height="4" patternUnits="userSpaceOnUse">
          <rect width="4" height="4" fill="none" />
          <circle cx="1" cy="1" r="0.45" fill="#fff" opacity="0.16" />
          <circle cx="3" cy="2.5" r="0.35" fill="#000" opacity="0.18" />
        </pattern>
      </defs>

      {showShadow && (
        <ellipse cx="400" cy={isBottom ? 744 : isCap ? 676 : 706} rx="190" ry="22"
          fill="#000" opacity="0.14" filter={`url(#soft-${uid})`} />
      )}

      {GARMENT_EXTRA[garment] && (
        <path d={GARMENT_EXTRA[garment]} fill={`url(#fab-${uid})`} stroke={dim} strokeWidth="2" strokeLinejoin="round" />
      )}
      {GARMENT_EXTRA[garment] && (
        <g clipPath={`url(#clip-${uid})`}><rect width="800" height="900" fill={`url(#shade-${uid})`} /></g>
      )}

      <path d={GARMENT_PATHS[garment] || GARMENT_PATHS.tee} fill={`url(#fab-${uid})`} stroke="none" />
      <g clipPath={`url(#clip-${uid})`}>
        <rect width="800" height="900" fill={`url(#sheen-${uid})`} />
        <rect width="800" height="900" fill={`url(#shade-${uid})`} />
        {withGrain && <rect width="800" height="900" fill={`url(#grain-${uid})`} />}
        <Details garment={garment} ink={printInk} dim={dim} />
        {mark && (
          <g transform={`translate(${zone.x - markSize / 2} ${zone.y - markSize / 2}) scale(${markSize / 100})`}>
            <LogoMark mark={{ ...mark, ink: printInk, invert: false }} size={100} wash={wash} seedOffset={5} />
          </g>
        )}
        {artSpec && (
          <g transform={`translate(${zone.x - markSize / 2} ${zone.y - markSize / 2})`}
            style={{ mixBlendMode: light ? 'multiply' : 'normal' }}>
            <Artwork spec={artSpec} ink={printInk} size={markSize} transparent />
          </g>
        )}
      </g>
      <path d={GARMENT_PATHS[garment] || GARMENT_PATHS.tee} fill="none"
        stroke={light ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.16)'} strokeWidth="2.2" strokeLinejoin="round" />
    </svg>
  );
}

/* ------------------------------------------------------------------
   Technical drawing
------------------------------------------------------------------- */

export function TechDrawing({ garment = 'hoodie', stroke = '#111110', showNotes = true, printMark = null, className = '' }) {
  const uid = useId().replace(/[:]/g, '');
  const isBottom = garment === 'cargo' || garment === 'shorts';
  const isCap = garment === 'cap';
  return (
    <svg viewBox="0 0 800 900" className={`tech-svg ${className}`} role="img" aria-label="technical drawing">
      <defs>
        <pattern id={`hatch-${uid}`} width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="7" stroke={stroke} strokeWidth="0.5" opacity="0.22" />
        </pattern>
      </defs>
      {GARMENT_EXTRA[garment] && (
        <path d={GARMENT_EXTRA[garment]} fill={`url(#hatch-${uid})`} stroke={stroke} strokeWidth="1.8" strokeLinejoin="round" />
      )}
      <path d={GARMENT_PATHS[garment] || GARMENT_PATHS.tee} fill={`url(#hatch-${uid})`} stroke={stroke}
        strokeWidth="2.2" strokeLinejoin="round" />
      <Details garment={garment} ink={stroke} dim={stroke} />
      {printMark && !isBottom && (
        <g transform={`translate(${isCap ? 400 : 400} ${isCap ? 430 : 380}) scale(1.5) translate(-50 -50)`}>
          <LogoMark mark={{ ...printMark, ink: stroke }} size={100} />
        </g>
      )}
      {showNotes && (
        <g stroke={stroke} fill={stroke} fontFamily={GROTESK}>
          <g>
            <line x1="266" y1={isBottom ? 300 : 400} x2={isBottom ? 534 : 534} y2={isBottom ? 300 : 400}
              strokeWidth="0.7" strokeDasharray="6 5" />
            <line x1="266" y1={isBottom ? 290 : 390} x2="266" y2={isBottom ? 310 : 410} strokeWidth="0.7" />
            <line x1="534" y1={isBottom ? 290 : 390} x2="534" y2={isBottom ? 310 : 410} strokeWidth="0.7" />
            <text x="400" y={isBottom ? 288 : 388} textAnchor="middle" fontSize="14" letterSpacing="2.4">
              {isBottom ? 'WAIST 1/2' : 'CHEST 1/2'}
            </text>
          </g>
          <g>
            <line x1="664" y1={isBottom ? 248 : 240} x2="664" y2={isBottom ? 714 : 690} strokeWidth="0.7" strokeDasharray="6 5" />
            <line x1="654" y1={isBottom ? 248 : 240} x2="674" y2={isBottom ? 248 : 240} strokeWidth="0.7" />
            <line x1="654" y1={isBottom ? 714 : 690} x2="674" y2={isBottom ? 714 : 690} strokeWidth="0.7" />
            <text x="684" y={(isBottom ? 481 : 465)} fontSize="14" letterSpacing="2.2" transform={`rotate(90 684 ${isBottom ? 481 : 465})`}>
              TOTAL LENGTH
            </text>
          </g>
          <circle cx="110" cy="150" r="30" fill="none" strokeWidth="0.8" />
          <text x="110" y="146" textAnchor="middle" fontSize="11">FRONT</text>
          <text x="110" y="160" textAnchor="middle" fontSize="9" opacity="0.7">SCALE 1:6</text>
        </g>
      )}
    </svg>
  );
}

/* ------------------------------------------------------------------
   Vector artwork
------------------------------------------------------------------- */

export function VectorArt({ mark, size = 400 }) {
  if (!mark) return null;
  return (
    <svg viewBox="0 0 400 400" width={size} height={size} className="vector-art" role="img" aria-label="vector artwork">
      <rect width="400" height="400" fill="#fff" />
      <circle cx="200" cy="200" r="186" fill="none" stroke="#111" strokeWidth="0.7" strokeDasharray="3 7" />
      <g transform="translate(64 64) scale(2.72)">
        <LogoMark mark={{ ...mark, ink: '#111110', invert: false }} size={100} />
      </g>
      <text x="200" y="384" textAnchor="middle" fontFamily={GROTESK} fontSize="7" fill="#111" letterSpacing="3">
        {mark.brand} · VECTOR · 1 COLOUR
      </text>
    </svg>
  );
}

export function Mark({ mark, ...rest }) {
  const seed = (mark && hashString(mark.id || 'x')) % 97;
  return <LogoMark mark={mark} seedOffset={seed} {...rest} />;
}
