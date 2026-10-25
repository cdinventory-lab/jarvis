import React, { useEffect, useRef, useState } from 'react';
import { GarmentMockup, LogoMark, TechDrawing, VectorArt, COLOR_FILLS, GARMENT_PATHS } from '../lib/Garments.jsx';
import { buildGarmentMesh, buildGlb, buildPdf, samplePathPoints } from '../lib/glb.js';
import { Artwork } from './Artwork.jsx';
import {
  garmentById, colorwayById, MODEL_PHOTOS, priceEstimate, TOOLS, slug, sizeChart, FABRICS, PRINTS,
} from '../lib/engine.js';

/* ------------------------------ exports -------------------------- */

/** Export helpers may be handed a wrapper element — always resolve to an <svg>. */
function asSvg(el) {
  if (!el) return null;
  if (el.tagName && el.tagName.toLowerCase() === 'svg') return el;
  if (el.querySelector) return el.querySelector('svg');
  return null;
}

export function downloadSvg(wrapper, name = 'jarvis') {
  const el = asSvg(wrapper);
  if (!el) return;
  const clone = el.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  if (!clone.getAttribute('width')) clone.setAttribute('width', '1200');
  if (!clone.getAttribute('height')) clone.setAttribute('height', '1200');
  clone.removeAttribute('class');
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = `text{font-family:'Space Grotesk',Helvetica,Arial,sans-serif}`;
  clone.insertBefore(style, clone.firstChild);
  const blob = new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml' });
  triggerDownload(URL.createObjectURL(blob), `${slug(name)}.svg`);
}

export function downloadPng(wrapper, name = 'jarvis', scale = 2) {
  const el = asSvg(wrapper);
  if (!el) return;
  const vb = el.viewBox?.baseVal;
  const w = (vb?.width || 800) * scale;
  const h = (vb?.height || 800) * scale;
  const clone = el.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  clone.setAttribute('width', w);
  clone.setAttribute('height', h);
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = `text{font-family:'Space Grotesk',Helvetica,Arial,sans-serif}`;
  clone.insertBefore(style, clone.firstChild);
  const svg = new XMLSerializer().serializeToString(clone);
  const img = new Image();
  const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);
    canvas.toBlob((blob) => {
      if (blob) triggerDownload(URL.createObjectURL(blob), `${slug(name)}.png`);
      URL.revokeObjectURL(url);
    }, 'image/png');
  };
  img.src = url;
}

export function downloadCsv(rows, name = 'chart') {
  const csv = rows.map((r) => r.join(',')).join('\n');
  triggerDownload(URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), `${slug(name)}.csv`);
}

/** Serialise an SVG node into JPEG bytes (used by the PDF and GLB writers). */
function svgToJpegBytes(wrapper, size = 1024, quality = 0.9) {
  return new Promise((resolve) => {
    const el = asSvg(wrapper);
    if (!el) return resolve(null);
    const vb = el.viewBox?.baseVal;
    const w = vb?.width || 800;
    const h = vb?.height || 800;
    const scale = size / Math.max(w, h);
    const clone = el.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', Math.round(w * scale));
    clone.setAttribute('height', Math.round(h * scale));
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = "text{font-family:'Space Grotesk',Helvetica,Arial,sans-serif}";
    clone.insertBefore(style, clone.firstChild);

    const svgText = new XMLSerializer().serializeToString(clone);
    const url = URL.createObjectURL(new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' }));
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(w * scale);
      canvas.height = Math.round(h * scale);
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(async (blob) => {
        URL.revokeObjectURL(url);
        resolve(blob ? new Uint8Array(await blob.arrayBuffer()) : null);
      }, 'image/jpeg', quality);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
    img.src = url;
  });
}

/** Lay a JPEG out on paper and download it as a real PDF. */
export async function downloadPdf(wrapper, name = 'jarvis', { a4 = true } = {}) {
  const el = asSvg(wrapper);
  const vb = el?.viewBox?.baseVal;
  const width = Math.round((vb?.width || 800) * 2);
  const height = Math.round((vb?.height || 800) * 2);
  const jpeg = await svgToJpegBytes(el, 1600);
  if (!jpeg) return false;
  const pdf = buildPdf(jpeg, { width, height, a4, title: name });
  const url = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' }));
  triggerDownload(url, `${slug(name)}.pdf`);
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return true;
}

/** Build a real glTF-binary garment from the rendered mockup and download it. */
export async function downloadGlb(wrapper, garment = 'hoodie', name = 'jarvis-garment') {
  const jpeg = await svgToJpegBytes(wrapper, 1024, 0.88);
  if (!jpeg) return false;
  const path = GARMENT_PATHS[garment] || GARMENT_PATHS.hoodie;
  const pts = samplePathPoints(path, 160);
  const mesh = buildGarmentMesh(pts, { thickness: 0.09 });
  const { glb } = buildGlb(mesh, jpeg, { name: `${name} · ${garment}` });
  const url = URL.createObjectURL(new Blob([glb], { type: 'model/gltf-binary' }));
  triggerDownload(url, `${slug(name)}.glb`);
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return true;
}

function triggerDownload(href, filename) {
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/* ------------------------------- pieces -------------------------- */

export function SvgBox({ children, name, ratio = '1 / 1', bg = 'bone', className = '', actions = true, download = 'svg' }) {
  const ref = useRef(null);
  return (
    <div className={`svgbox svgbox-${bg} ${className}`}>
      <div className="svgbox-inner" style={{ aspectRatio: ratio }} ref={ref}>{children}</div>
      {actions && (
        <div className="svgbox-tools">
          <button className="mini" onClick={() => downloadSvg(ref.current, name)}>SVG</button>
          <button className="mini" onClick={() => downloadPng(ref.current, name, 2)}>PNG</button>
          <button className="mini" onClick={() => downloadPdf(ref.current, name)}>PDF</button>
        </div>
      )}
    </div>
  );
}

export function MarkTile({ mark, label, active, onSelect, bg = 'bone' }) {
  return (
    <button className={`mark-tile ${active ? 'is-active' : ''} bg-${bg}`} onClick={onSelect} type="button">
      <span className="mark-tile-art"><LogoMark mark={mark} size={140} wash={0.08} seedOffset={2} /></span>
      <span className="mark-tile-meta"><span>{label}</span>{active && <em>selected</em>}</span>
    </button>
  );
}

/* --------------------------- photoshoot -------------------------- */

export function Photoshoot({ artifact, onRefine, variant = 'photo' }) {
  const photo = MODEL_PHOTOS.find((p) => p.id === artifact.params.photoId) || MODEL_PHOTOS[0];
  const mark = artifact.mark;
  const [pose, setPose] = useState(photo.id);
  const active = MODEL_PHOTOS.find((p) => p.id === pose) || photo;
  const playing = variant === 'video';
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!playing) return;
    const i = setInterval(() => setTick((t) => (t + 1) % 100), 60);
    return () => clearInterval(i);
  }, [playing]);

  return (
    <div className={`shoot ${playing ? 'is-video' : ''}`}>
      <div className="shoot-frame" style={{ aspectRatio: active.id === 'flat' ? '16 / 9' : '4 / 5' }}>
        <img src={active.src} alt={`Model wearing ${artifact.params.brand}`} className="shoot-photo"
          style={{ transform: playing ? `scale(${1.04 + Math.min(tick, 92) * 0.0016}) translateX(${Math.sin(tick / 18) * 4}px)` : undefined }} />
        {mark && (
          <div className="shoot-print" style={{
            left: `${active.zone.left * 100}%`,
            top: `${active.zone.top * 100}%`,
            width: `${active.zone.w * 100}%`,
            transform: `rotate(${active.zone.tilt}deg)`,
            mixBlendMode: active.blend === 'light' ? 'screen' : 'multiply',
            opacity: active.blend === 'light' ? 0.9 : 0.86,
          }}>
            <LogoMark mark={{ ...mark, ink: active.blend === 'light' ? '#f4f4ef' : '#141412' }} size={300} wash={0.14} />
          </div>
        )}
        <div className="shoot-hud">
          <span className="hud-pill">{active.label}</span>
          <span className="hud-pill">{active.backdrop}</span>
        </div>
        {playing && (
          <div className="shoot-video-ui">
            <span className="hud-pill live"><i /> 9:16 · 1080p · 5s</span>
            <div className="shoot-progress"><span style={{ width: `${tick}%` }} /></div>
          </div>
        )}
      </div>
      <div className="shoot-poses">
        {MODEL_PHOTOS.map((p) => (
          <button key={p.id} type="button" className={`pose-chip ${p.id === pose ? 'is-active' : ''}`} onClick={() => setPose(p.id)}>
            <img src={p.src} alt="" />
            <span>{p.label.split(' · ')[0]}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------ 3D ------------------------------- */

export function Turntable({ artifact }) {
  const [angle, setAngle] = useState(-18);
  const [wire, setWire] = useState(false);
  const [busy, setBusy] = useState(false);
  const drag = useRef(null);
  const solidRef = useRef(null);

  const exportGlb = async () => {
    setBusy(true);
    const ok = await downloadGlb(
      solidRef.current,
      artifact.params.garment,
      `${artifact.params.brand}-${artifact.params.garment}`
    );
    setBusy(false);
    if (!ok) window.alert('Could not render the texture for export in this browser.');
  };

  const onDown = (e) => {
    drag.current = { x: e.clientX ?? e.touches?.[0]?.clientX ?? 0, a: angle };
  };
  const onMove = (e) => {
    if (!drag.current) return;
    const x = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
    setAngle(Math.max(-70, Math.min(70, drag.current.a + (x - drag.current.x) * 0.6)));
  };
  const onUp = () => { drag.current = null; };

  return (
    <div className="turntable">
      <div className="turntable-stage"
        onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
        onTouchStart={onDown} onTouchMove={onMove} onTouchEnd={onUp}>
        <div className="turntable-card" style={{ transform: `rotateY(${angle}deg)` }}>
          {wire ? (
            <TechDrawing garment={artifact.params.garment} showNotes={false} printMark={artifact.mark} />
          ) : (
            <GarmentMockup garment={artifact.params.garment} colorway={artifact.params.colorway}
              mark={artifact.mark} placement={artifact.params.placement} scale={artifact.params.scale}
              wash={artifact.params.wash} withGrain={false} showShadow={false} />
          )}
        </div>
        <div className="turntable-floor" />
        <div className="turntable-offscreen" aria-hidden="true">
          <div ref={solidRef}>
            <GarmentMockup garment={artifact.params.garment} colorway={artifact.params.colorway}
              mark={artifact.mark} placement={artifact.params.placement} scale={artifact.params.scale}
              wash={artifact.params.wash} invert={artifact.params.invert} artSpec={artifact.art || null}
              showShadow={false} />
          </div>
        </div>
      </div>
      <div className="turntable-bar">
        <span className="mono-xs">.GLB · {(angle).toFixed(0)}°</span>
        <div className="turntable-actions">
          <button className="mini" onClick={() => setWire((w) => !w)}>{wire ? 'Solid' : 'Wireframe'}</button>
          <button className="mini" onClick={() => setAngle((a) => (a > 30 ? -18 : a + 45))}>Rotate</button>
          <button className="mini" onClick={exportGlb} disabled={busy}>{busy ? 'Packing…' : 'Download .glb'}</button>
        </div>
      </div>
    </div>
  );
}

/* --------------------------- tech pack --------------------------- */

const DEFAULT_CONSTRUCTION = [
  'Coverstitched hem and cuffs, 6 mm',
  'Twin-needle shoulder seams with tape',
  'Bartack at pocket and sleeve openings',
  'Screen print cured at 160 °C',
];

export function TechPack({ artifact }) {
  const { params } = artifact;
  const g = garmentById(params.garment);
  const cw = colorwayById(params.colorway);
  const drawingRef = useRef(null);
  const rows = ['chest', 'length', 'sleeve', 'shoulder'];
  const chart = artifact.chart && artifact.chart.length ? artifact.chart : sizeChart(params.garment, params.fit, params.unit);
  const fabric = FABRICS[params.garment] || FABRICS.hoodie;
  const gsm = fabric.name.match(/(\d{3})/)?.[1] || '380';
  const printLabel = (PRINTS[params.printMethod] || PRINTS.screen).name;
  return (
    <div className="techpack paper">
      <div className="tp-head">
        <div>
          <p className="mono-xs dim">TECH PACK · {params.unit === 'in' ? 'INCHES' : 'CM'}</p>
          <h4>{params.brand} {g.name}</h4>
          <p className="mono-xs dim">JV-{params.garment.slice(0, 3).toUpperCase()}-{String(params.seed).slice(-4)} · REV {artifact.revision || 1}</p>
        </div>
        <div className="tp-swatches">
          <span className="swatch" style={{ background: cw.hex }} />
          <span className="mono-xs">{cw.name}</span>
        </div>
      </div>
      <div className="tp-grid">
        <div className="tp-drawing">
          <div ref={drawingRef}><TechDrawing garment={params.garment} printMark={artifact.mark} /></div>
          <button className="mini tp-pdf" type="button" onClick={() => downloadPdf(drawingRef.current, `${params.brand}-${params.garment}-techpack`, { a4: true })}>
            PDF · A4
          </button>
        </div>
        <div className="tp-side">
          <dl className="tp-list">
            <div><dt>Fabric</dt><dd>{fabric.name}</dd></div>
            <div><dt>Weight</dt><dd>{gsm} GSM</dd></div>
            <div><dt>Fit</dt><dd>{params.fit}</dd></div>
            <div><dt>Print</dt><dd>{printLabel} · {params.placement}</dd></div>
            <div><dt>Colour</dt><dd>{cw.name}</dd></div>
            <div><dt>Colourways</dt><dd>{(artifact.params.colourways || [cw.name, 'Bone', 'Heather grey']).join(' · ')}</dd></div>
          </dl>
          <table className="tp-table">
            <thead>
              <tr><th>Point</th><th>XS</th><th>S</th><th>M</th><th>L</th><th>XL</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r}>
                  <td className="cap">{r}</td>
                  {chart.slice(0, 5).map((c) => <td key={c.size}>{c[r] ?? '—'}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="tp-construction">
            <p className="mono-xs dim">CONSTRUCTION CALLOUTS</p>
            <ol>
              {(artifact.params.construction || DEFAULT_CONSTRUCTION).map((c, i) => (
                <li key={c}><span className="tp-callout mono-xs">{String(i + 1).padStart(2, '0')}</span>{c}</li>
              ))}
            </ol>
          </div>
          <div className="tp-bom">
            <p className="mono-xs dim">BILL OF MATERIALS</p>
            {[['Shell', 'Cotton fleece 450 GSM', '1.4 m'], ['Ribbing', '2×2 cotton rib', '0.25 m'],
              ['Print', 'Water-based ink', '1 pass'], ['Labels', 'Woven main + care', '2 pcs']].map(([a, b, c]) => (
              <div key={a} className="tp-bom-row"><span>{a}</span><span>{b}</span><span>{c}</span></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------- size chart / cost --------------------- */

export function SizeChart({ artifact }) {
  const chart = artifact.chart || [];
  const keys = Object.keys(chart[0] || {}).filter((k) => k !== 'size');
  return (
    <div className="sizechart">
      <table>
        <thead>
          <tr><th>{artifact.params.unit === 'in' ? 'inch' : 'cm'}</th>{chart.map((c) => <th key={c.size}>{c.size}</th>)}</tr>
        </thead>
        <tbody>
          {keys.map((k) => (
            <tr key={k}>
              <td className="cap">{k === 'inseam' ? 'Inseam' : k}</td>
              {chart.map((c) => <td key={c.size}>{c[k]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="sizechart-foot">
        <span className="mono-xs dim">{artifact.params.fit} fit · {garmentById(artifact.params.garment).name}</span>
        <button className="mini" onClick={() => downloadCsv([['size', ...keys], ...chart.map((r) => [r.size, ...keys.map((k) => r[k])])], `${artifact.params.brand}-size-chart`)}>
          CSV
        </button>
      </div>
    </div>
  );
}

export function Estimate({ artifact }) {
  const e = artifact.estimate;
  const max = Math.max(...e.breakdown.map((b) => b.value));
  return (
    <div className="estimate">
      <div className="estimate-head">
        <div>
          <p className="mono-xs dim">PER PIECE · {e.qty} PCS</p>
          <p className="estimate-price">${e.perLow}<span>–</span>${e.perHigh}</p>
        </div>
        <div className="estimate-total">
          <p className="mono-xs dim">ORDER TOTAL</p>
          <p>${e.totalLow.toLocaleString()}–${e.totalHigh.toLocaleString()}</p>
          <p className="mono-xs dim">+ ${e.tooling} tooling</p>
        </div>
      </div>
      <div className="bars">
        {e.breakdown.map((b) => (
          <div className="bar-row" key={b.label}>
            <span className="mono-xs">{b.label}</span>
            <span className="bar"><i style={{ width: `${(b.value / max) * 100}%` }} /></span>
            <span className="mono-xs">${b.value.toFixed(2)}</span>
          </div>
        ))}
      </div>
      <p className="mono-xs dim">Fabric: {e.fabricName} · {e.printName}</p>
    </div>
  );
}

/* --------------------------- artifact card ----------------------- */

export function ArtifactView({ artifact, onSelectMark, onAction, compact = false }) {
  switch (artifact.kind) {
    case 'logo':
      return (
        <div className="logo-batch">
          {artifact.marks.map((m, i) => (
            <MarkTile key={m.id} mark={m} label={m.style} active={(artifact.selected || 0) === i}
              onSelect={() => onSelectMark?.(i)} bg={i % 3 === 1 ? 'ink' : 'bone'} />
          ))}
        </div>
      );
    case 'mockup':
      return (
        <SvgBox name={`${artifact.params.brand}-${artifact.params.garment}`} ratio="8 / 9" bg="bone">
          <GarmentMockup garment={artifact.params.garment} colorway={artifact.params.colorway}
            mark={artifact.mark} placement={artifact.params.placement} scale={artifact.params.scale}
            wash={artifact.params.wash} invert={artifact.params.invert} artSpec={artifact.art || null} />
        </SvgBox>
      );
    case 'photoshoot':
      return <Photoshoot artifact={artifact} />;
    case 'video':
      return <Photoshoot artifact={artifact} variant="video" />;
    case 'vector':
      return (
        <SvgBox name={`${artifact.params.brand}-vector`} ratio="1 / 1" bg="paper">
          <VectorArt mark={artifact.mark} size={undefined} />
        </SvgBox>
      );
    case 'techpack':
      return <TechPack artifact={artifact} />;
    case 'sizechart':
      return <SizeChart artifact={artifact} />;
    case 'estimate':
      return <Estimate artifact={artifact} />;
    case 'model3d':
      return <Turntable artifact={artifact} />;
    case 'art':
      return (
        <div className="art-view">
          <SvgBox name={`${artifact.params.brand}-artwork`} ratio="1 / 1" bg="paper">
            <Artwork spec={artifact.art} ink={artifact.ink} />
          </SvgBox>
          <div className="art-meta">
            <span className="mono-xs dim">
              {artifact.art.mode === 'reference' ? 'Reference · 1 colour' : `${artifact.art.motif} · procedural`}
            </span>
            {artifact.appliedTo && <span className="mono-xs dim">on {garmentById(artifact.appliedTo).short}</span>}
          </div>
        </div>
      );
    default:
      return null;
  }
}

export function ArtifactActions({ artifact, onAction, showRefine, pro = false }) {
  const common = [];
  if (artifact.kind === 'logo') {
    common.push(
      { id: 'use-mark', label: 'Use on garment' },
      { id: 'variations', label: 'More variations' },
      { id: 'vectorize', label: 'Vectorise' }
    );
  } else if (artifact.kind === 'mockup') {
    common.push(
      { id: 'photoshoot', label: 'Photoshoot' },
      { id: 'techpack', label: 'Tech pack' },
      { id: 'estimate', label: 'Estimate' },
      { id: 'sizechart', label: 'Size chart' },
      { id: 'model3d', label: '3D model' }
    );
  } else if (artifact.kind === 'photoshoot') {
    common.push(
      { id: 'video', label: pro ? 'Make a 5s video' : 'Make a 5s video · PRO', locked: !pro },
      { id: 'vector', label: 'Vectorise print' }
    );
  } else if (artifact.kind === 'art') {
    if (artifact.art?.mode === 'reference' && !artifact.art.source) {
      common.push({ id: 'upload', label: 'Choose reference image' });
    } else {
      common.push({ id: 'apply', label: 'Apply to garment' }, { id: 'logo', label: 'Turn into a mark' });
    }
  } else if (artifact.kind === 'techpack') {
    common.push({ id: 'estimate', label: 'Price it' }, { id: 'sizechart', label: 'Size chart' });
  } else if (artifact.kind === 'model3d') {
    common.push({ id: 'techpack', label: 'Tech pack' }, { id: 'photoshoot', label: 'Photoshoot' });
  } else if (artifact.kind === 'vector') {
    common.push({ id: 'apply', label: 'Use on garment' });
  }

  return (
    <div className="artifact-actions">
      {common.map((a) => (
        <button key={a.id} className={`chip ${a.locked ? 'is-locked' : ''}`} type="button"
          onClick={() => onAction?.(a.id)}>{a.label}</button>
      ))}
      {showRefine && (
        <span className="refine-hint mono-xs dim">or type an edit below</span>
      )}
    </div>
  );
}
