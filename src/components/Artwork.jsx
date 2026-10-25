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
      content = <ReferenceArt spec={spec} uid={uid} transparent={transparent} />;
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

function ReferenceArt({ spec, uid, transparent = false }) {
  const { source, grid, gridSize = 84, levels = 5, contrast = 1.6, halftone = 0.6, dot = 2, invert = false } = spec;

  if (!source && !grid) {
    return (
      <g>
        <rect x="24" y="24" width="352" height="352" fill="none" stroke="#111110" strokeDasharray="6 6" strokeWidth="1.5" />
        <text x="200" y="192" textAnchor="middle" fontFamily="'Space Grotesk', Arial" fontSize="14"
          fill="#111110" letterSpacing="2">ADD A REFERENCE IMAGE</text>
        <text x="200" y="214" textAnchor="middle" fontFamily="'Space Grotesk', Arial" fontSize="9.5"
          fill="#111110" opacity="0.55" letterSpacing="1.6">WE VECTORISE IT INTO A 1-COLOUR PRINT</text>
      </g>
    );
  }

  // Vectorised halftone — the printable artwork.
  if (Array.isArray(grid) && grid.length) {
    const n = Math.round(Math.sqrt(grid.length)) || gridSize;
    const area = 360;
    const cell = area / n;
    const steps = Math.max(2, Math.min(8, Math.round(levels)));
    const inkColor = invert ? '#f7f7f2' : '#111110';
    const paperColor = invert ? '#111110' : '#f7f7f2';
    const dotScale = 0.55 + Math.min(1, Math.max(0, (dot - 0.6) / 3.4)) * 0.95;
    const round = halftone > 0.12;
    const cells = [];

    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const lum = grid[y * n + x] / 255;
        let v = Math.min(1, Math.max(0, (lum - 0.5) * contrast + 0.5));
        v = Math.round(v * (steps - 1)) / (steps - 1);
        // Invert swaps the ink, never the shape: light dots on a dark ground.
        const darkness = 1 - v;
        if (darkness < 0.06) continue;
        const cx = 20 + cell * (x + 0.5);
        const cy = 20 + cell * (y + 0.5);
        if (round) {
          const r = (cell / 2) * Math.sqrt(darkness) * dotScale;
          if (r > 0.08) cells.push(<circle key={`${x}-${y}`} cx={cx} cy={cy} r={r} fill={inkColor} />);
        } else {
          const side = cell * Math.sqrt(darkness) * dotScale * 1.1;
          cells.push(<rect key={`${x}-${y}`} x={cx - side / 2} y={cy - side / 2} width={side} height={side} fill={inkColor} />);
        }
      }
    }

    if (transparent) {
      // Pressed onto a garment: dots only, no paper ground, no captions.
      return <g shapeRendering="geometricPrecision">{cells}</g>;
    }

    return (
      <g>
        <rect x="20" y="20" width={area} height={area} fill={paperColor} />
        <g shapeRendering="geometricPrecision">{cells}</g>
        <rect x="20" y="20" width={area} height={area} fill="none" stroke="#111110" strokeWidth="1.2" opacity="0.5" />
        <text x="24" y="390" fontFamily="'Space Grotesk', Arial" fontSize="9" fill="#111110" letterSpacing="1.7" opacity="0.7">
          {`${steps} TONES · ${round ? 'HALFTONE' : 'POSTERISED'}${invert ? ' · INVERTED' : ''}`}
        </text>
        <text x="376" y="390" textAnchor="end" fontFamily="'Space Grotesk', Arial" fontSize="9" fill="#111110" letterSpacing="1.7" opacity="0.7">
          VECTORISED · 1 COLOUR
        </text>
      </g>
    );
  }

  // Fallback: the raw reference, tone-separated (before a grid is sampled).
  const filterId = `ref-${uid}`;
  const steps = Math.max(2, Math.min(8, Math.round(levels)));
  const table = Array.from({ length: steps }, (_, i) => (invert ? 1 - i / (steps - 1) : i / (steps - 1)).toFixed(3)).join(' ');
  return (
    <g>
      <defs>
        <filter id={filterId} x="0" y="0" width="100%" height="100%">
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncR type="linear" slope={contrast} intercept={(1 - contrast) / 2} />
            <feFuncG type="linear" slope={contrast} intercept={(1 - contrast) / 2} />
            <feFuncB type="linear" slope={contrast} intercept={(1 - contrast) / 2} />
          </feComponentTransfer>
          <feComponentTransfer>
            <feFuncR type="discrete" tableValues={table} />
            <feFuncG type="discrete" tableValues={table} />
            <feFuncB type="discrete" tableValues={table} />
          </feComponentTransfer>
        </filter>
      </defs>
      <image href={source} x="20" y="20" width="360" height="360" preserveAspectRatio="xMidYMid slice"
        filter={`url(#${filterId})`} />
      <rect x="20" y="20" width="360" height="360" fill="none" stroke="#111110" strokeWidth="1.2" opacity="0.5" />
      <text x="24" y="390" fontFamily="'Space Grotesk', Arial" fontSize="9" fill="#111110" letterSpacing="1.7" opacity="0.7">
        {`${steps} TONES · PREVIEW`}
      </text>
    </g>
  );
}

