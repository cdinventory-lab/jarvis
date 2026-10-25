import React, { useId, useMemo } from 'react';
import { rngFrom } from '../lib/engine.js';

/* One-colour print artwork, generated procedurally from a prompt. */

export function Artwork({ spec, ink = '#111110', className = '', size, transparent = false }) {
  const raw = useId().replace(/[:]/g, '');
  const uid = raw;
  if (!spec) return null;
  const r = useMemo(() => rngFrom(spec.seed || 1), [spec.seed]);
  const fg = spec.invert ? '#f7f7f2' : ink;
  const bg = spec.invert ? '#111110' : '#f7f7f2';

  let content = null;
  switch (spec.mode) {
    case 'reference':
      content = <ReferenceArt spec={spec} uid={uid} />;
      break;
    default:
      content = <ProceduralArt spec={spec} fg={fg} r={r} />;
  }

  return (
    <svg viewBox="0 0 400 400" width={size} height={size} className={`artwork ${className}`}
      role="img" aria-label="generated print artwork">
      {!transparent && <rect width="400" height="400" fill={bg} />}
      {content}
    </svg>
  );
}

function ProceduralArt({ spec, fg, r }) {
  const { motif, density, word, rotation } = spec;
  if (spec.mode === 'reference') return null;

  if (motif === 'halftone') {
    const step = 400 / density;
    const dots = [];
    for (let x = 0; x < density; x++) {
      for (let y = 0; y < density; y++) {
        const cx = step / 2 + x * step;
        const cy = step / 2 + y * step;
        const d = Math.hypot(cx - 200, cy - 200) / 240;
        const rad = Math.max(0.4, (1 - d) * (step * 0.48));
        dots.push(<circle key={`${x}-${y}`} cx={cx} cy={cy} r={rad} fill={fg} />);
      }
    }
    return <g>{dots}</g>;
  }
  if (motif === 'stripes') {
    const lines = [];
    const n = density * 3;
    for (let i = 0; i < n; i++) {
      lines.push(<line key={i} x1={-200 + i * (800 / n)} y1="-100" x2={-200 + i * (800 / n)} y2="500"
        stroke={fg} strokeWidth={i % 3 === 0 ? 10 : 3} />);
    }
    return (
      <g transform={`rotate(${rotation} 200 200)`}>
        <g clipPath="url(#none)">{lines}</g>
      </g>
    );
  }
  if (motif === 'arch') {
    return (
      <g fill="none" stroke={fg}>
        {Array.from({ length: density }, (_, i) => (
          <path key={i} d={`M${60 + i * 12} 340 C${60 + i * 12} ${180 - i * 8} ${340 - i * 12} ${180 - i * 8} ${340 - i * 12} 340`}
            strokeWidth={i % 2 ? 1.4 : 4} />
        ))}
        <line x1="40" y1="340" x2="360" y2="340" strokeWidth="4" />
      </g>
    );
  }
  if (motif === 'checker') {
    const n = Math.max(6, density);
    const cell = 400 / n;
    const cells = [];
    for (let x = 0; x < n; x++) {
      for (let y = 0; y < n; y++) {
        if ((x + y) % 2 === 0) cells.push(<rect key={`${x}-${y}`} x={x * cell} y={y * cell} width={cell} height={cell} fill={fg} />);
      }
    }
    return <g>{cells}</g>;
  }
  if (motif === 'brutal') {
    const words = word.slice(0, 6);
    return (
      <g fill={fg} fontFamily="'Space Grotesk', Arial, sans-serif" fontWeight="700">
        <rect x="24" y="24" width="352" height="10" />
        <text x="200" y="196" textAnchor="middle" fontSize="110" letterSpacing="-4">{words}</text>
        <text x="200" y="300" textAnchor="middle" fontSize="34" letterSpacing="10" fontFamily="'Space Grotesk', Arial">MONOCHROME</text>
        <rect x="24" y="366" width="352" height="10" />
      </g>
    );
  }
  if (motif === 'orbit') {
    const rings = [];
    for (let i = 1; i <= density; i++) {
      rings.push(<circle key={i} cx="200" cy="200" r={i * (170 / density)} fill="none" stroke={fg}
        strokeWidth={i % 2 ? 1.2 : 4} strokeDasharray={i % 3 === 0 ? '10 8' : undefined} />);
    }
    const ticks = Array.from({ length: 48 }, (_, i) => {
      const a = (Math.PI * 2 * i) / 48;
      const r1 = 150;
      const r2 = i % 4 === 0 ? 182 : 168;
      return <line key={i} x1={200 + r1 * Math.cos(a)} y1={200 + r1 * Math.sin(a)}
        x2={200 + r2 * Math.cos(a)} y2={200 + r2 * Math.sin(a)} stroke={fg} strokeWidth="3" />;
    });
    return <g>{rings}{ticks}<circle cx="200" cy="200" r="26" fill={fg} /></g>;
  }
  if (motif === 'type') {
    return (
      <g fill={fg} fontFamily="'Instrument Serif', Georgia, serif">
        {Array.from({ length: 9 }, (_, i) => (
          <text key={i} x={i % 2 ? 30 : 12} y={48 + i * 40} fontSize="40" letterSpacing="6">{word}</text>
        ))}
      </g>
    );
  }
  // gradient
  const id = `g-${spec.seed}`;
  return (
    <g>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={fg} stopOpacity="0" />
          <stop offset="55%" stopColor={fg} stopOpacity="0.55" />
          <stop offset="100%" stopColor={fg} stopOpacity="1" />
        </linearGradient>
        <pattern id={`d-${id}`} width="8" height="8" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1.1" fill={fg} opacity="0.5" />
          <circle cx="6" cy="6" r="0.7" fill={fg} opacity="0.35" />
        </pattern>
      </defs>
      <rect width="400" height="400" fill={`url(#${id})`} />
      <rect width="400" height="400" fill={`url(#d-${id})`} opacity="0.6" />
      <circle cx="200" cy="200" r="120" fill="none" stroke="#f7f7f2" strokeWidth="2" opacity="0.7" />
    </g>
  );
}

function ReferenceArt({ spec, uid }) {
  const filterId = `ref-${uid}`;
  if (!spec.source) {
    return (
      <g>
        <rect x="24" y="24" width="352" height="352" fill="none" stroke="#111110" strokeDasharray="6 6" strokeWidth="1.5" />
        <text x="200" y="200" textAnchor="middle" fontFamily="'Space Grotesk', Arial" fontSize="15"
          fill="#111110" letterSpacing="2">ADD A REFERENCE IMAGE</text>
      </g>
    );
  }
  return (
    <g>
      <defs>
        <filter id={filterId}>
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncR type="linear" slope={1.7} intercept={-0.35} />
            <feFuncG type="linear" slope={1.7} intercept={-0.35} />
            <feFuncB type="linear" slope={1.7} intercept={-0.35} />
          </feComponentTransfer>
        </filter>
        <pattern id={`h-${uid}`} width="5" height="5" patternUnits="userSpaceOnUse">
          <circle cx="2.5" cy="2.5" r="1.7" fill="#111110" opacity={0.35 + spec.halftone * 0.6} />
        </pattern>
      </defs>
      <image href={spec.source} x="20" y="20" width="360" height="360" preserveAspectRatio="xMidYMid slice"
        filter={`url(#${filterId})`} />
      {spec.halftone > 0.05 && (
        <rect x="20" y="20" width="360" height="360" fill={`url(#h-${uid})`} style={{ mixBlendMode: 'multiply' }} />
      )}
      <rect x="20" y="20" width="360" height="360" fill="none" stroke="#111110" strokeWidth="1.5" />
      <text x="200" y="392" textAnchor="middle" fontFamily="'Space Grotesk', Arial" fontSize="10"
        fill="#111110" letterSpacing="2.4">REFERENCE · 1 COLOUR CONVERSION</text>
    </g>
  );
}
