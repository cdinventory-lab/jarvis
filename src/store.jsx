import React, { createContext, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import {
  TOOLS, uid, parseBrief, parseRefine, logoBatch, makeLogo, garmentById, colorwayById,
  MODEL_PHOTOS, priceEstimate, sizeChart, hashString, detectBrand, detectBrandExplicit, slug,
} from './lib/engine.js';

const KEY = 'jarvis.studio.v2';

const initial = {
  plan: 'Creator',
  credits: 225,
  creditsStart: 225,
  brand: '',
  project: 'Untitled drop',
  activeTool: 'mockup',
  messages: [],
  controls: {
    garment: 'hoodie',
    colorway: 'washed-black',
    fit: 'oversized',
    placement: 'chest',
    scale: 'medium',
    wash: 0.2,
    printMethod: 'screen',
    qty: 300,
    region: 'eu',
    unit: 'cm',
    clean: false,
    refImage: null,
  },
  lastArtifactId: null,
  thinking: null,
  activity: [],
};

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return initial;
    const parsed = JSON.parse(raw);
    return { ...initial, ...parsed, controls: { ...initial.controls, ...(parsed.controls || {}), refImage: null } };
  } catch {
    return initial;
  }
}

function reducer(state, action) {
  switch (action.type) {
    case 'controls':
      return { ...state, controls: { ...state.controls, ...action.payload } };
    case 'tool':
      return { ...state, activeTool: action.payload };
    case 'spend':
      return { ...state, credits: Math.max(0, state.credits - action.payload) };
    case 'addCredits':
      return { ...state, credits: state.credits + action.payload, creditsStart: state.creditsStart + action.payload };
    case 'push':
      return {
        ...state,
        messages: [...state.messages, ...action.payload],
        lastArtifactId: action.lastId ?? state.lastArtifactId,
        credits: action.cost ? Math.max(0, state.credits - action.cost) : state.credits,
        activity: [...state.activity, ...(action.activity || [])].slice(-40),
      };
    case 'patchArtifact':
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.artifact && m.artifact.id === action.id
            ? { ...m, artifact: { ...m.artifact, ...action.patch } }
            : m
        ),
        credits: action.cost ? Math.max(0, state.credits - action.cost) : state.credits,
      };
    case 'project':
      return { ...state, project: action.payload, brand: action.brand ?? state.brand };
    case 'plan':
      return { ...state, plan: action.payload, credits: action.credits, creditsStart: action.credits };
    case 'thinking':
      return { ...state, thinking: action.payload };
    case 'reset':
      return { ...initial, controls: state.controls };
    case 'hydrate':
      return { ...state, ...action.payload };
    default:
      return state;
  }
}

const StudioCtx = createContext(null);

export function StudioProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, undefined, load);
  const timers = useRef([]);
  const seedTick = useRef(0);

  useEffect(() => {
    try {
      const { ...persist } = state;
      localStorage.setItem(KEY, JSON.stringify(persist));
    } catch {}
  }, [state]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const api = useMemo(() => {
    const pushAssistant = (text, artifact, cost = 0, extra = {}) => {
      const id = uid();
      dispatch({
        type: 'push',
        payload: [{ id, role: 'assistant', text, artifact: artifact ? { ...artifact, id: artifact.id || id } : null, time: Date.now(), ...extra }],
        lastId: artifact?.id || id,
        cost,
        activity: [{ id, label: artifact ? TOOLS[artifact.tool]?.name || 'Generation' : 'Message', at: Date.now() }],
      });
      return id;
    };

    const buildArtifact = (tool, prompt, controls, prevMark, overrideSeed, artSpec) => {
      const brief = parseBrief(prompt || '');
      const brand = detectBrandExplicit(prompt || '') || state.brand || brief.brand || 'JARVIS';
      const p = {
        seed: overrideSeed ?? brief.seed,
        brand,
        garment: brief.garment,
        colorway: controls.colorway,
        placement: brief.placement,
        scale: brief.scale,
        wash: fine(controls.wash),
        invert: false,
        fit: controls.fit,
        printMethod: controls.printMethod,
        qty: controls.qty,
        region: controls.region,
        unit: controls.unit,
        prompt,
        style: brief.style,
      };
      const ink = colorwayById(p.colorway).ink === 'light' ? '#f4f4ef' : '#111110';

      switch (tool) {
        case 'logo': {
          const marks = logoBatch({ seed: p.seed, brand, ink, count: 4 });
          return {
            kind: 'logo', tool, title: `${brand} — logo options`,
            params: p, marks, selected: 0, ink,
          };
        }
        case 'text2img': {
          return {
            kind: 'art', tool, title: 'Print artwork',
            params: p,
            art: makeArtworkSpec(prompt || brand, p.seed),
            ink,
          };
        }
        case 'img2img': {
          return {
            kind: 'art', tool, title: 'Reference → print',
            params: p,
            art: { mode: 'reference', source: controls.refImage, threshold: 0.5, halftone: 0.4 },
            appliedTo: null,
            ink,
          };
        }
        case 'photoshoot':
        case 'video': {
          const mark = prevMark || makeLogo({ seed: p.seed, brand, ink, style: 'wordmark' });
          const photo = MODEL_PHOTOS[(p.seed + (tool === 'video' ? 1 : 0)) % MODEL_PHOTOS.length];
          return {
            kind: tool, tool, title: tool === 'video' ? 'Photoshoot video' : 'Photoshoot',
            params: { ...p, photoId: photo.id }, mark, ink,
            duration: tool === 'video' ? 5 : null,
          };
        }
        case 'vector': {
          const mark = prevMark || makeLogo({ seed: p.seed, brand, ink: '#111110', style: 'badge' });
          return { kind: 'vector', tool, title: 'Vector artwork', params: p, mark, ink: '#111110' };
        }
        case 'techpack': {
          const mark = prevMark || makeLogo({ seed: p.seed, brand, ink, style: 'monogram' });
          return { kind: 'techpack', tool, title: 'Tech pack', params: p, mark, ink };
        }
        case 'sizechart':
          return { kind: 'sizechart', tool, title: 'Size chart', params: p, chart: sizeChart(p.garment, p.fit, p.unit) };
        case 'estimate':
          return {
            kind: 'estimate', tool, title: 'Production estimate', params: p,
            estimate: priceEstimate({ garment: p.garment, qty: Number(controls.qty), print: controls.printMethod, country: controls.region }),
          };
        case 'model3d': {
          const mark = prevMark || makeLogo({ seed: p.seed, brand, ink, style: 'minimal' });
          return { kind: 'model3d', tool, title: '3D model', params: p, mark, ink };
        }
        case 'mockup':
        default: {
          const mark = artSpec ? null : prevMark || makeLogo({ seed: p.seed, brand, ink, style: 'wordmark' });
          return {
            kind: 'mockup', tool: 'mockup',
            title: artSpec ? 'Print on garment' : 'Technical mockup',
            params: p, mark, ink, art: artSpec || null,
          };
        }
      }
    };

    const run = (tool, prompt, opts = {}) => {
      const t = TOOLS[tool];
      if (state.credits < t.cost) {
        pushAssistant(
          `You need ${t.cost} credits for that and you have ${state.credits} left. Top up in Plans and I will pick this straight back up.`,
          null, 0
        );
        return;
      }
      const controls = { ...state.controls, ...(opts.controls || {}) };
      const prevMark = opts.mark || null;
      const variant = opts.variant ?? seedTick.current++;
      const seed = opts.seed ?? ((parseBrief(prompt || '').seed + variant * 7919) >>> 0);

      dispatch({ type: 'thinking', payload: { tool, prompt } });
      const delay = opts.instant ? 0 : t.cost >= 20 ? 2100 : 900 + Math.min(900, t.cost * 60);
      const id = setTimeout(() => {
        const artifact = buildArtifact(tool, prompt, controls, prevMark, seed, opts.artSpec || null);
        const text = assistantCopy(tool, artifact, prompt);
        dispatch({ type: 'thinking', payload: null });
        pushAssistant(text, artifact, t.cost);
        if (artifact.params.brand && artifact.params.brand !== state.brand) {
          dispatch({ type: 'project', payload: `${artifact.params.brand} · Drop 01`, brand: artifact.params.brand });
        }
      }, delay);
      timers.current.push(id);
    };

    const submit = (raw) => {
      const text = (raw || '').trim();
      if (!text) return;
      dispatch({ type: 'push', payload: [{ id: uid(), role: 'user', text, time: Date.now() }] });

      const all = state.messages.filter((m) => m.artifact).map((m) => m.artifact);
      const garmentKinds = ['mockup', 'photoshoot', 'video', 'techpack', 'model3d'];
      const latest = all[all.length - 1];
      const latestGarment = [...all].reverse().find((a) => garmentKinds.includes(a.kind));
      const wantsGarmentEdit = /bigger|smaller|washed|cleaner|invert|chest|back|sleeve|black|white|grey/i.test(text);
      const last = wantsGarmentEdit && latestGarment ? latestGarment : latest;
      const intent = detectIntent(text);
      const tool = intent.tool || state.activeTool;

      // Refinement of an existing artifact
      if (intent.refine && last && !intent.tool) {
        const { next, changed } = parseRefine(text, last);
        if (changed) {
          const t = TOOLS[last.tool] || TOOLS.mockup;
          const newMark = last.marks
            ? { ...last.marks[last.selected || 0] }
            : last.mark
            ? { ...last.mark, seed: (last.mark.seed || 1) + 7 }
            : makeLogo({ seed: Date.now() % 9999, brand: last.params.brand, ink: last.ink });
          const patched = {
            ...last.params,
            ...next,
          };
          dispatch({
            type: 'patchArtifact',
            id: last.id,
            patch: { params: patched, mark: newMark, revision: (last.revision || 1) + 1 },
            cost: Math.max(1, Math.round(t.cost / 2)),
          });
          pushAssistant(
            `Updated — ${describeChange(next, last.params)}. Credited ${Math.max(1, Math.round(t.cost / 2))} for the revision.`,
            null,
            0
          );
          return;
        }
      }

      if (intent.credits) {
        pushAssistant(
          `You have ${state.credits} credits left on the ${state.plan} plan. A mockup is ${TOOLS.mockup.cost}, a logo ${TOOLS.logo.cost}, a 3D model ${TOOLS.model3d.cost}.`,
          null, 0
        );
        return;
      }

      run(tool, text);
    };

    return { state, dispatch, submit, run, pushAssistant, buildArtifact };
  }, [state]);

  return <StudioCtx.Provider value={api}>{children}</StudioCtx.Provider>;
}

export const useStudio = () => {
  const ctx = useContext(StudioCtx);
  if (!ctx) throw new Error('useStudio outside provider');
  return ctx;
};

/* ------------------------------ helpers -------------------------- */

const fine = (n) => Math.round(n * 100) / 100;

function detectIntent(text = '') {
  const p = text.toLowerCase();
  const out = {};
  if (/^\s*(hi|hello|hey)\b/.test(p)) return { small: true };
  if (/credit|how much|balance/.test(p)) out.credits = true;
  if (/bigger|smaller|washed|cleaner|invert|move (it )?to|back graphic|chest|sleeve|bolder|thinner|tagline/.test(p)) out.refine = true;
  const map = [
    [/tech ?pack|spec sheet|bom/, 'techpack'],
    [/size chart|sizing|measurements/, 'sizechart'],
    [/price|cost|estimate|budget|quote/, 'estimate'],
    [/3d|rotate|glb/, 'model3d'],
    [/vector|svg|line art|embroidery file/, 'vector'],
    [/video|reel|tiktok|loop|animate/, 'video'],
    [/photoshoot|on a model|model|lookbook|campaign/, 'photoshoot'],
    [/image to image|img2img|reference|upload|my photo|this photo/, 'img2img'],
    [/logo|mark|monogram|wordmark|badge|brand identity/, 'logo'],
    [/text to image|text2img|artwork|graphic|print design|pattern/, 'text2img'],
    [/mockup|hoodie|tee|t-shirt|crewneck|bomber|cargo|shorts|cap|garment/, 'mockup'],
  ];
  map.forEach(([re, tool]) => {
    if (re.test(p) && !out.tool) out.tool = tool;
  });
  return out;
}

function describeChange(next, prev) {
  if (next.scale && next.scale !== prev.scale) return `print size set to ${next.scale}`;
  if (next.wash !== undefined && next.wash !== prev.wash) return next.wash > (prev.wash || 0) ? 'more wash and distress applied' : 'print cleaned up';
  if (next.placement && next.placement !== prev.placement) return `graphic moved to the ${next.placement}`;
  if (next.invert !== undefined && next.invert !== prev.invert) return 'print inverted';
  if (next.colorway && next.colorway !== prev.colorway) return `colourway switched to ${colorwayById(next.colorway).name.toLowerCase()}`;
  return 'design refined';
}

function assistantCopy(tool, artifact, prompt) {
  const brand = artifact.params.brand;
  const g = garmentById(artifact.params.garment);
  const cw = colorwayById(artifact.params.colorway).name.toLowerCase();
  const brief = prompt ? `Based on “${prompt.length > 78 ? prompt.slice(0, 78) + '…' : prompt}”. ` : '';
  switch (tool) {
    case 'logo':
      return `${brief}Four directions for ${brand}: wordmark, monogram, badge and a distressed seal. They are one colour, so any of them drops straight onto a garment. Pick one and I will mock it up.`;
    case 'mockup':
      return `${brief}Here is the ${g.name.toLowerCase()} in ${cw} with a ${artifact.params.scale} ${artifact.params.placement} print. Which piece is next for the drop?`;
    case 'photoshoot':
      return `${brief}Your print on a model, studio-lit and ready for the lookbook. Say “make a video” for the 5-second loop.`;
    case 'video':
      return `${brief}A 5-second vertical loop, 9:16 · 1080p. Ready for Reels and TikTok — the print and the colourway match the drop.`;
    case 'vector':
      return `${brief}Clean one-colour line art for screen printing and embroidery. SVG and PNG export included.`;
    case 'techpack':
      return `${brief}Manufacturer-ready spec sheet with fabric, weight, BOM, construction notes and the measurement chart.`;
    case 'sizechart':
      return `${brief}Here is the ${artifact.params.fit} fit size chart in ${artifact.params.unit}. Switch the unit or fit in the inspector.`;
    case 'estimate':
      return `${brief}Production estimate for ${artifact.estimate.qty} pieces: $${artifact.estimate.perLow}–$${artifact.estimate.perHigh} per piece. Change quantity in the inspector.`;
    case 'model3d':
      return `${brief}A turntable model for your store page, exported as .glb. Drag it to rotate.`;
    case 'text2img':
      return `${brief}Print artwork generated one colour, so it survives screen printing. Send it to a mockup when you are happy.`;
    case 'img2img':
      return `${brief}Your reference was converted into a one-colour print, then pressed onto the garment. Adjust the threshold in the inspector.`;
    default:
      return brief || 'Done.';
  }
}

/* ---------------- procedural print artwork (text → image) -------- */

const MOTIFS = ['halftone', 'stripes', 'arch', 'checker', 'brutal', 'orbit', 'type', 'gradient'];

export function makeArtworkSpec(prompt = '', seed = 1) {
  const h = hashString(prompt.toLowerCase() + seed);
  const r = (n) => (h % n);
  const motif = MOTIFS[(h >>> 3) % MOTIFS.length];
  return {
    mode: 'procedural',
    motif,
    seed: h,
    rotation: r(30) - 15,
    density: 6 + (r(9)),
    invert: (h >>> 5) % 2 === 0,
    word: (prompt.match(/\b([A-Za-z]{3,10})\b/g) || ['JARVIS'])[r(3)]?.toUpperCase() || 'JARVIS',
  };
}

export function addCredits(n) {
  return { type: 'addCredits', payload: n };
}
