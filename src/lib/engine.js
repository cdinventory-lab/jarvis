/* ------------------------------------------------------------------
   JARVIS — design engine
   Deterministic, client-side generation: briefs become brand systems,
   marks, garment mockups, vectors, tech packs and production estimates.
   Swap `composeBrief` for a hosted image model when you want it.
------------------------------------------------------------------- */

/* ----------------------------- utilities ------------------------- */

export function hashString(s = '') {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function mulberry32(a) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function rngFrom(seed) {
  const r = mulberry32(typeof seed === 'number' ? seed : hashString(String(seed)));
  return {
    next: r,
    int: (min, max) => Math.floor(r() * (max - min + 1)) + min,
    pick: (arr) => arr[Math.floor(r() * arr.length)],
    chance: (p) => r() < p,
    range: (min, max) => min + r() * (max - min),
  };
}

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

export const slug = (s = '') =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'jarvis';

/* ------------------------------ catalogue ------------------------ */

export const GARMENTS = [
  { id: 'hoodie', name: 'Oversized hoodie', short: 'Hoodie', category: 'Top', zone: { x: 0.375, y: 0.30, w: 0.25, h: 0.22 } },
  { id: 'tee', name: 'Heavyweight tee', short: 'Tee', category: 'Top', zone: { x: 0.365, y: 0.30, w: 0.27, h: 0.22 } },
  { id: 'crew', name: 'Crewneck sweatshirt', short: 'Crewneck', category: 'Top', zone: { x: 0.365, y: 0.29, w: 0.27, h: 0.22 } },
  { id: 'bomber', name: 'Varsity bomber', short: 'Bomber', category: 'Outerwear', zone: { x: 0.36, y: 0.30, w: 0.28, h: 0.20 } },
  { id: 'longsleeve', name: 'Long sleeve', short: 'Long sleeve', category: 'Top', zone: { x: 0.37, y: 0.30, w: 0.26, h: 0.22 } },
  { id: 'cargo', name: 'Cargo pants', short: 'Cargo', category: 'Bottom', zone: { x: 0.42, y: 0.44, w: 0.16, h: 0.20 } },
  { id: 'shorts', name: 'Raw-hem shorts', short: 'Shorts', category: 'Bottom', zone: { x: 0.42, y: 0.42, w: 0.16, h: 0.18 } },
  { id: 'cap', name: 'Six-panel cap', short: 'Cap', category: 'Accessory', zone: { x: 0.40, y: 0.36, w: 0.20, h: 0.16 } },
];

export const garmentById = (id) => GARMENTS.find((g) => g.id === id) || GARMENTS[0];

export const COLORWAYS = [
  { id: 'washed-black', name: 'Washed black', hex: '#232322', print: '#f2f2ee', ink: 'light' },
  { id: 'ink', name: 'Ink', hex: '#0b0b0b', print: '#fafaf7', ink: 'light' },
  { id: 'charcoal', name: 'Charcoal', hex: '#4a4a48', print: '#f4f4f0', ink: 'light' },
  { id: 'grey', name: 'Heather grey', hex: '#a9a9a4', print: '#111110', ink: 'dark' },
  { id: 'bone', name: 'Bone', hex: '#dcd8ce', print: '#141412', ink: 'dark' },
  { id: 'ivory', name: 'Ivory', hex: '#f0efea', print: '#141412', ink: 'dark' },
];

export const colorwayById = (id) => COLORWAYS.find((c) => c.id === id) || COLORWAYS[0];

export const MODEL_PHOTOS = [
  { id: 'm1', src: '/assets/model-1.jpg', label: 'Studio · front', gender: 'Unisex', backdrop: 'Seamless white', zone: { left: 0.400, top: 0.280, w: 0.200, tilt: -0.6 }, blend: 'dark' },
  { id: 'm2', src: '/assets/model-2.jpg', label: 'Editorial · three-quarter', gender: 'Woman', backdrop: 'Mid grey', zone: { left: 0.300, top: 0.430, w: 0.190, tilt: -1.4 }, blend: 'light' },
  { id: 'flat', src: '/assets/gallery-tee.jpg', label: 'Flat lay · detail', gender: 'Unisex', backdrop: 'Pale grey', zone: { left: 0.415, top: 0.395, w: 0.150, tilt: 0.8 }, blend: 'dark' },
];

export const TOOLS = {
  text2img: { id: 'text2img', name: 'Text to image', cost: 2, label: 'Text → Image', blurb: 'Eight print styles from one sentence.' },
  img2img: { id: 'img2img', name: 'Image to image', cost: 4, label: 'Image → Image', blurb: 'Vectorise any photo into a one-colour print.' },
  mockup: { id: 'mockup', name: 'Technical mockup', cost: 2, label: 'Mockup', blurb: 'Garment mockups, flat or worn.' },
  logo: { id: 'logo', name: 'Logo & graphics', cost: 3, label: 'Logo', blurb: 'Marks, badges and wordmarks.' },
  photoshoot: { id: 'photoshoot', name: 'Photoshoot', cost: 3, label: 'Photoshoot', blurb: 'Your print on a model.' },
  video: { id: 'video', name: 'Photoshoot video', cost: 25, label: 'Video', blurb: '5-second 9:16 loop for Reels.', proOnly: true },
  vector: { id: 'vector', name: 'Vector generator', cost: 3, label: 'Vector', blurb: 'Screen-print ready line art.' },
  techpack: { id: 'techpack', name: 'Tech pack', cost: 3, label: 'Tech pack', blurb: 'Manufacturer-ready spec sheet.' },
  sizechart: { id: 'sizechart', name: 'Size chart', cost: 1, label: 'Size chart', blurb: 'Measurements in cm or inches.' },
  estimate: { id: 'estimate', name: 'Price estimate', cost: 1, label: 'Estimate', blurb: 'Know your unit cost first.' },
  model3d: { id: 'model3d', name: '3D generator', cost: 20, label: '3D model', blurb: 'Spin your garment on the store.' },
};

export const TOOL_ORDER = ['mockup', 'logo', 'photoshoot', 'img2img', 'text2img', 'vector', 'techpack', 'sizechart', 'estimate', 'model3d', 'video'];

/* --------------------------- brief parsing ----------------------- */

const GARMENT_WORDS = [
  [/hoodie|hooded|sweatshirt with hood/, 'hoodie'],
  [/crewneck|crew neck|sweatshirt|jumper|pullover/, 'crew'],
  [/bomber|varsity|jacket|outerwear|coach/, 'bomber'],
  [/long ?sleeve|longsleeve/, 'longsleeve'],
  [/cargo|pants|trousers|sweatpants|joggers/, 'cargo'],
  [/shorts|boardshort/, 'shorts'],
  [/cap|hat|beanie|headwear/, 'cap'],
  [/t-?shirt|tee|top|shirt/, 'tee'],
];

const STYLES = [
  [/gothic|occult|dark|cathedral|medieval/, 'gothic'],
  [/street|urban|skate|hip.?hop/, 'streetwear'],
  [/minimal|clean|quiet|scandi|essential/, 'minimal'],
  [/luxury|premium|atelier|couture|elegant/, 'luxury'],
  [/vintage|retro|washed|90s|distressed|worn/, 'vintage'],
  [/sport|athletic|track|training|gym/, 'sport'],
  [/y2k|cyber|futur|technical|techwear/, 'y2k'],
  [/romantic|soft|poetic|organic|botanic/, 'organic'],
];

const FALLBACK_BRANDS = [
  'SAINT', 'ATELIER', 'NORTHBOUND', 'MONO', 'HALO', 'VANTA', 'ORISON', 'NOCTURNE',
  'ASHFALL', 'SABLE', 'MERIDIAN', 'COLDFRONT', 'OBSCURA', 'SERAPH', 'KILN', 'LOWLAND',
];

const SYLL = ['sa', 'in', 'tar', 'vel', 'no', 'ri', 'ash', 'mon', 'ar', 'cade', 'sel', 'kai', 'or', 'ven', 'ly', 'nox'];

/** Brand name the user actually wrote, or '' if they did not name one. */
export function detectBrandExplicit(prompt = '') {
  const quoted = prompt.match(/["'“”]([A-Za-z0-9&.\- ]{2,18})["'“”]/);
  if (quoted) return quoted[1].trim().toUpperCase();

  const STOP = /^(called|named|brand|label|is|the|for|a|an|my|our|new|dark|black|white)$/i;
  const grab = (re) => {
    const m = prompt.match(re);
    const word = m?.[1]?.replace(/[.,]$/, '');
    return word && !STOP.test(word) ? word.toUpperCase() : '';
  };
  const named = grab(/(?:called|named)\s+["']?([A-Za-z0-9&.\-]{2,18})/i);
  if (named) return named;
  const labelled = grab(/(?:brand|label)\s+(?:is\s+|called\s+|named\s+)?["']?([A-Za-z0-9&.\-]{2,18})/i);
  if (labelled) return labelled;

  const caps = prompt.match(/\b([A-Z]{3,12})\b/);
  if (caps && !STOP.test(caps[1])) return caps[1];
  return '';
}

export function detectBrand(prompt = '') {
  const explicit = detectBrandExplicit(prompt);
  if (explicit) return explicit;
  const r = rngFrom(prompt + 'brand');
  if (prompt.trim().length > 12) {
    let word = '';
    const n = r.int(2, 3);
    for (let i = 0; i < n; i++) word += r.pick(SYLL);
    return word.toUpperCase();
  }
  return FALLBACK_BRANDS[hashString(prompt) % FALLBACK_BRANDS.length];
}

export function parseBrief(prompt = '') {
  const p = prompt.toLowerCase();
  const garment = (GARMENT_WORDS.find(([re]) => re.test(p)) || [, 'tee'])[1];
  const styles = STYLES.filter(([re]) => re.test(p)).map(([, s]) => s);
  const style = styles[0] || 'streetwear';
  let colorway = 'washed-black';
  if (/white|ivory|off.?white|cream|bone|ecru/.test(p)) colorway = 'ivory';
  else if (/grey|gray|heather|marle/.test(p)) colorway = 'grey';
  else if (/charcoal/.test(p)) colorway = 'charcoal';
  else if (/black|dark|noir/.test(p)) colorway = 'washed-black';
  const placement = /back/.test(p) ? 'back' : /sleeve/.test(p) ? 'sleeve' : 'chest';
  const scale = /big|large|huge|oversized graphic|full.?back/.test(p) ? 'large' : /small|tiny|minimal/.test(p) ? 'small' : 'medium';
  const brand = detectBrand(prompt);
  const seed = hashString(prompt.trim().toLowerCase() + '|' + garment + '|' + style);
  return { prompt, garment, style, styles, colorway, placement, scale, brand, seed };
}

export const REFINE_HINTS = [
  'bigger back graphic',
  'more washed-out',
  'tighter tracking',
  'invert the print',
  'move to the chest',
  'add a tagline',
];

/** Interpret a follow-up sentence against the last artifact. */
export function parseRefine(text = '', artifact) {
  const p = text.toLowerCase();
  const next = { ...(artifact?.params || {}) };
  let changed = false;
  if (/bigger|larger|huge|scale up/.test(p)) { next.scale = next.scale === 'large' ? 'large' : next.scale === 'small' ? 'medium' : 'large'; changed = true; }
  if (/smaller|tinier|scale down/.test(p)) { next.scale = next.scale === 'large' ? 'medium' : 'small'; changed = true; }
  if (/washed|faded|distress|vintage/.test(p)) { next.wash = Math.min(1, (next.wash ?? 0.25) + 0.25); changed = true; }
  if (/cleaner|crisp|sharp|solid/.test(p)) { next.wash = 0; changed = true; }
  if (/invert|negative|white on black|swap/.test(p)) { next.invert = !next.invert; changed = true; }
  if (/back/.test(p) && !/background/.test(p)) { next.placement = 'back'; changed = true; }
  if (/chest|front/.test(p)) { next.placement = 'chest'; changed = true; }
  if (/sleeve/.test(p)) { next.placement = 'sleeve'; changed = true; }
  if (/bold|heavier weight|thicker/.test(p)) { next.weight = Math.min(1, (next.weight ?? 0.4) + 0.2); changed = true; }
  if (/thin|hairline|light(er)? weight/.test(p)) { next.weight = Math.max(0.1, (next.weight ?? 0.4) - 0.15); changed = true; }
  if (/black/.test(p)) { next.colorway = 'washed-black'; changed = true; }
  if (/white|ivory|bone/.test(p)) { next.colorway = 'ivory'; changed = true; }
  if (/grey|gray/.test(p)) { next.colorway = 'grey'; changed = true; }
  if (/tagline|slogan|words|text/.test(p)) { next.tagline = true; changed = true; }
  return { next, changed };
}

/* --------------------------- logo generation --------------------- */

const LOGO_STYLES = ['badge', 'monogram', 'wordmark', 'emblem', 'gothic', 'minimal', 'brutal', 'seal'];

/**
 * Build a deterministic mark spec. Everything the renderer needs to draw
 * a print-ready vector logo lives here.
 */
export function makeLogo({ seed = 1, brand = 'JARVIS', style = 'badge', ink = '#111110', invert = false } = {}) {
  const r = rngFrom(typeof seed === 'string' ? hashString(seed) : seed);
  const chosen = style && LOGO_STYLES.includes(style) ? style : r.pick(LOGO_STYLES);
  const fold = r.pick([3, 4, 5, 6, 8, 12]);
  const motif = r.pick(['blades', 'orbits', 'chevrons', 'spikes', 'grid', 'lattice', 'petals', 'arrows']);
  const glyph = {
    motif,
    fold,
    radius: r.range(0.26, 0.36),
    spin: r.range(0, 360),
    weight: r.range(0.012, 0.03),
    density: r.int(2, 4),
    gap: r.range(0.12, 0.3),
    solid: r.chance(0.35),
  };
  const initials = brand.replace(/[^A-Z0-9]/gi, '').slice(0, 2).toUpperCase() || 'J';
  const type = {
    family: chosen === 'gothic' ? 'serif' : chosen === 'brutal' ? 'grotesk' : r.pick(['serif', 'grotesk']),
    tracking: chosen === 'wordmark' ? 0.26 : r.range(0.08, 0.24),
    size: chosen === 'wordmark' ? 0.2 : chosen === 'monogram' ? 0.34 : 0.11,
    weight: chosen === 'brutal' ? 700 : 500,
    caps: r.chance(0.7),
    initials: chosen === 'monogram',
    split: chosen === 'badge' || chosen === 'seal',
  };
  const frame = chosen === 'badge' ? r.pick(['circle', 'double-circle', 'rounded'])
    : chosen === 'seal' ? 'double-circle'
    : chosen === 'emblem' ? r.pick(['shield', 'hex'])
    : null;
  return {
    id: uid(),
    brand: brand.toUpperCase(),
    style: chosen,
    ink,
    invert,
    glyph,
    type,
    frame,
    tagline: r.pick(['STUDIO', 'ATELIER', 'DROP 01', 'EST. 2024', 'MONOCHROME', 'ORIGINAL', '']),
    seed: typeof seed === 'number' ? seed : hashString(String(seed)),
  };
}

export function logoBatch({ seed, brand, ink, count = 4, styles = [] }) {
  const base = typeof seed === 'number' ? seed : hashString(String(seed));
  const pool = styles.length ? styles : ['wordmark', 'monogram', 'badge', 'gothic', 'minimal', 'emblem', 'seal', 'brutal'];
  const r = rngFrom(base);
  const shuffled = [...pool].sort(() => r.next() - 0.5);
  return Array.from({ length: count }, (_, i) =>
    makeLogo({
      seed: base + i * 7919,
      brand,
      ink,
      style: shuffled[i % shuffled.length],
    })
  );
}

/* --------------------------- production data --------------------- */

export const SIZE_BASE = {
  tee: { chest: 112, length: 70, sleeve: 22, shoulder: 50 },
  hoodie: { chest: 118, length: 68, sleeve: 58, shoulder: 52 },
  crew: { chest: 114, length: 66, sleeve: 57, shoulder: 51 },
  bomber: { chest: 116, length: 64, sleeve: 60, shoulder: 50 },
  longsleeve: { chest: 110, length: 71, sleeve: 62, shoulder: 48 },
  cargo: { waist: 78, inseam: 76, hem: 24, rise: 31 },
  shorts: { waist: 78, inseam: 22, hem: 27, rise: 29 },
  cap: { circumference: 58, brim: 7, crown: 12 },
};

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

export function sizeChart(garment = 'tee', fit = 'oversized', unit = 'cm') {
  const base = SIZE_BASE[garment] || SIZE_BASE.tee;
  const fitScale = fit === 'oversized' ? 1.09 : fit === 'boxy' ? 1.05 : fit === 'slim' ? 0.95 : 1;
  const fitLen = fit === 'oversized' ? 1.03 : fit === 'boxy' ? 0.98 : 1;
  return SIZES.map((size, i) => {
    const step = i === 0 ? -6 : i === 1 ? -3 : i >= 4 ? (i - 2) * 6 : 0;
    const row = { size };
    Object.entries(base).forEach(([k, v]) => {
      const scaled = k === 'length' || k === 'inseam' || k === 'sleeve' ? v * fitLen + step * 0.8 : v * fitScale + step;
      const value = Math.round(scaled * 10) / 10;
      row[k] = unit === 'in' ? Math.round((value / 2.54) * 10) / 10 : value;
    });
    return row;
  });
}

export const FABRICS = {
  tee: { name: '240 GSM compact jersey', price: 3.1, unit: 'kg' },
  hoodie: { name: '450 GSM brushed fleece', price: 4.6, unit: 'kg' },
  crew: { name: '380 GSM loopback fleece', price: 4.1, unit: 'kg' },
  bomber: { name: 'Recycled nylon shell', price: 6.2, unit: 'kg' },
  longsleeve: { name: '220 GSM interlock', price: 3.4, unit: 'kg' },
  cargo: { name: '310 GSM cotton twill', price: 4.9, unit: 'kg' },
  shorts: { name: '310 GSM cotton twill', price: 4.2, unit: 'kg' },
  cap: { name: 'Cotton twill · 6 panel', price: 2.4, unit: 'kg' },
};

export const PRINTS = {
  none: { name: 'No print', cost: 0 },
  screen: { name: 'Screen print · 1 colour', cost: 1.4 },
  puff: { name: 'Puff print', cost: 2.1 },
  embroidery: { name: 'Embroidery', cost: 3.2 },
  dtg: { name: 'DTG', cost: 2.6 },
};

export function priceEstimate({ garment = 'hoodie', qty = 300, print = 'screen', trim = 'standard', country = 'eu' } = {}) {
  const fab = FABRICS[garment] || FABRICS.hoodie;
  const pr = PRINTS[print] || PRINTS.screen;
  const qtyFactor = qty <= 50 ? 1.65 : qty <= 100 ? 1.4 : qty <= 300 ? 1.12 : qty <= 500 ? 1 : qty <= 1000 ? 0.92 : 0.86;
  const trimCost = { minimal: 0.6, standard: 1.2, premium: 2.6 }[trim] ?? 1.2;
  const region = { eu: 1, pt: 0.82, tr: 0.74, asia: 0.68, us: 1.18 }[country] ?? 1;
  const labour = 2.9 * region;
  const fabric = fab.price * (garment === 'cargo' || garment === 'shorts' ? 2.1 : garment === 'cap' ? 0.6 : 1.5);
  const printCost = pr.cost + (trimCost * 0.4);
  const unit = (fabric + labour + printCost + trimCost) * qtyFactor;
  const tooling = 85 + (print === 'embroidery' ? 120 : 0);
  const perLow = Math.round(unit * 0.92 * 10) / 10;
  const perHigh = Math.round(unit * 1.14 * 10) / 10;
  return {
    perLow,
    perHigh,
    totalLow: Math.round(perLow * qty),
    totalHigh: Math.round(perHigh * qty),
    tooling,
    qty,
    currency: 'USD',
    breakdown: [
      { label: 'Fabric', value: Math.round(fabric * qtyFactor * 100) / 100 },
      { label: 'Labour', value: Math.round(labour * qtyFactor * 100) / 100 },
      { label: 'Print', value: Math.round(printCost * qtyFactor * 100) / 100 },
      { label: 'Trims', value: Math.round(trimCost * qtyFactor * 100) / 100 },
    ],
    fabricName: fab.name,
    printName: pr.name,
  };
}

export function techPackSpec(artifact) {
  const garment = artifact?.params?.garment || 'hoodie';
  const g = garmentById(garment);
  const color = colorwayById(artifact?.params?.colorway);
  const fab = FABRICS[garment] || FABRICS.hoodie;
  const chart = sizeChart(garment, artifact?.params?.fit || 'oversized');
  return {
    title: `${artifact?.params?.brand || 'JARVIS'} ${g.name}`,
    code: `JV-${garment.slice(0, 3).toUpperCase()}-${String(artifact?.params?.seed || 1).slice(-4)}`,
    garment: g,
    color,
    fabric: fab.name,
    weight: fab.name.match(/(\d{3})/)?.[1] || '380',
    print: artifact?.params?.printMethod || 'Screen print · 1 colour',
    placement: artifact?.params?.placement || 'chest',
    chart,
    bom: [
      ['Shell fabric', fab.name, '1.4 m'],
      ['Ribbing', '2×2 cotton rib', '0.25 m'],
      ['Print', 'Water-based ink, 1 colour', '1 pass'],
      ['Labels', 'Woven main + care', '2 pcs'],
      ['Thread', 'Poly-cotton, matched', '1 cone'],
    ],
    construction: [
      'Coverstitched hem and cuffs, 6 mm',
      'Twin-needle shoulder seams with tape',
      'Bartack at pocket and sleeve openings',
      'Screen print cured at 160 °C',
    ],
  };
}
