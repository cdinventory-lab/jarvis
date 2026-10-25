import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from '../router.jsx';
import { useStudio } from '../store.jsx';
import {
  TOOLS, TOOL_ORDER, GARMENTS, COLORWAYS, garmentById, colorwayById, sizeChart, priceEstimate,
} from '../lib/engine.js';
import { Icons, TOOL_ICONS } from '../components/Icons.jsx';
import { ArtifactView, ArtifactActions, downloadSvg } from '../components/Artifact.jsx';
import { LogoMark } from '../lib/Garments.jsx';

const TOOL_PROMPTS = {
  mockup: ['Oversized washed black hoodie, big distressed back print', 'Heavyweight ivory tee, small chest mark', 'Grey crewneck for a minimal skate label'],
  logo: ['A dark gothic streetwear label called SAINT', 'Minimal monogram for an atelier named VANTA', 'Brutalist badge for a techno collective'],
  photoshoot: ['Show my design on a model in the studio', 'Editorial three-quarter shot, mid grey backdrop', 'Flat lay product shot for the store'],
  video: ['Make a 5-second loop for Instagram', 'Short vertical clip for the drop'],
  vector: ['One-colour line art of my print for screen printing', 'Embroidery-ready vector of the chest mark'],
  techpack: ['Manufacturer tech pack for the hoodie', 'Spec sheet with BOM and measurements'],
  sizechart: ['Oversized size chart in cm', 'Slim fit chart in inches'],
  estimate: ['What do 300 hoodies cost to produce?', 'Estimate 100 tees in Portugal'],
  model3d: ['Turn the hoodie into a 3D model for my store', 'Spin-ready model of the drop'],
  text2img: ['A bold halftone print about monochrome', 'Big serif type artwork for a back print'],
  img2img: ['Turn my reference into a one-colour print', 'Restyle this image as a screen print'],
};

export default function Studio() {
  const { state, dispatch, submit, run } = useStudio();
  const [draft, setDraft] = useState('');
  const [pendingMark, setPendingMark] = useState(null);
  const [panel, setPanel] = useState('inspect');
  const [mobilePanel, setMobilePanel] = useState(false);
  const scroller = useRef(null);
  const fileRef = useRef(null);
  const pendingBrief = useRef(
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('jarvis.pending') : null
  );

  const messages = state.messages;
  const lastArtifact = useMemo(() => {
    const list = messages.filter((m) => m.artifact);
    return list.length ? list[list.length - 1].artifact : null;
  }, [messages]);

  useEffect(() => {
    const el = scroller.current;
    if (el && typeof el.scrollTo === 'function') el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    else if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  // A brief typed on the marketing page continues straight into the studio.
  useEffect(() => {
    const brief = pendingBrief.current;
    if (!brief) return;
    pendingBrief.current = null;
    sessionStorage.removeItem('jarvis.pending');
    const t = setTimeout(() => submit(brief), 260);
    return () => clearTimeout(t);
  }, []);

  const setControl = (patch) => {
    dispatch({ type: 'controls', payload: patch });
    const garmentKinds = ['mockup', 'photoshoot', 'video', 'techpack', 'model3d', 'sizechart', 'estimate'];
    const target = lastArtifact && garmentKinds.includes(lastArtifact.kind)
      ? lastArtifact
      : [...messages].reverse().map((m) => m.artifact).find((a) => a && garmentKinds.includes(a.kind));
    const liveKeys = ['garment', 'colorway', 'placement', 'scale', 'wash', 'invert', 'fit', 'unit', 'qty', 'printMethod', 'region'];
    if (target && liveKeys.some((k) => k in patch)) {
      const nextParams = { ...target.params, ...patch };
      const patchArtifact = { params: nextParams };
      if (target.kind === 'sizechart' && (patch.garment || patch.fit || patch.unit)) {
        patchArtifact.chart = sizeChart(nextParams.garment, nextParams.fit, nextParams.unit);
      }
      if (target.kind === 'estimate' && ('qty' in patch || 'printMethod' in patch || 'region' in patch || 'garment' in patch)) {
        patchArtifact.estimate = priceEstimate({
          garment: nextParams.garment, qty: Number(nextParams.qty),
          print: nextParams.printMethod, country: nextParams.region,
        });
      }
      dispatch({ type: 'patchArtifact', id: target.id, patch: patchArtifact });
    }
    if (lastArtifact?.kind === 'art' && lastArtifact.art?.mode === 'reference' && 'halftone' in patch) {
      dispatch({ type: 'patchArtifact', id: lastArtifact.id, patch: { art: { ...lastArtifact.art, halftone: patch.halftone } } });
    }
    if (lastArtifact?.art?.mode === 'reference' && patch.refImage) {
      dispatch({ type: 'patchArtifact', id: lastArtifact.id, patch: { art: { ...lastArtifact.art, source: patch.refImage } } });
    }
  };

  const handleAction = (artifact, action) => {
    const mark = artifact.marks ? artifact.marks[artifact.selected || 0] : artifact.mark;
    switch (action) {
      case 'use-mark':
        setPendingMark(mark);
        setPanel('inspect');
        dispatch({ type: 'tool', payload: 'mockup' });
        run('mockup', artifact.params.prompt || `${artifact.params.brand} garment`, { mark });
        break;
      case 'variations':
        run(artifact.tool === 'logo' ? 'logo' : artifact.tool, artifact.params.prompt || artifact.params.brand,
          { mark, variant: (artifact.variant || 0) + Math.floor(Math.random() * 90) + 3 });
        break;
      case 'vectorize':
      case 'vector':
        run('vector', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'apply':
        if (artifact.kind === 'art') {
          run('mockup', artifact.params.prompt || artifact.params.brand, { artSpec: artifact.art });
        } else {
          setPendingMark(mark || null);
          run('mockup', artifact.params.prompt || artifact.params.brand, { mark: mark || null });
        }
        break;
      case 'photoshoot':
        run('photoshoot', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'video':
        run('video', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'techpack':
        run('techpack', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'sizechart':
        run('sizechart', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'estimate':
        run('estimate', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'model3d':
        run('model3d', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      case 'logo':
        run('logo', artifact.params.prompt || artifact.params.brand, { mark });
        break;
      default:
        break;
    }
  };

  const onFile = async (file) => {
    if (!file) return;
    const dataUrl = await shrinkImage(file);
    if (!dataUrl) return;
    setControl({ refImage: dataUrl });
    dispatch({ type: 'tool', payload: 'img2img' });
    run('img2img', draft || 'Convert my reference into a one-colour print', { controls: { refImage: dataUrl } });
  };

  const send = (text) => {
    const value = (text ?? draft).trim();
    if (!value) return;
    submit(value);
    setDraft('');
  };

  const onTool = (id) => {
    dispatch({ type: 'tool', payload: id });
    setPanel('inspect');
    if (id === 'img2img' && !state.controls.refImage) fileRef.current?.click();
  };

  const creditsPct = Math.max(0, Math.min(100, (state.credits / Math.max(1, state.creditsStart)) * 100));

  return (
    <div className="studio">
      <header className="studio-top">
        <div className="studio-top-left">
          <Link to="/" className="brand-mark" aria-label="JARVIS home">
            <span className="brand-glyph">J</span>
            <span className="brand-word">JARVIS</span>
          </Link>
          <span className="top-sep" />
          <div className="project-name">
            <span className="mono-xs dim">PROJECT</span>
            <strong>{state.project}</strong>
          </div>
        </div>
        <div className="studio-top-right">
          <Link to="/pricing" className="credit-meter" title={`${state.credits} credits left — view plans`}>
            <span className="credit-bar"><i style={{ width: `${creditsPct}%` }} /></span>
            <span className="mono-xs">{state.credits} cr · {state.plan}</span>
          </Link>
          <button className="mini only-mobile" onClick={() => { setPanel(panel === 'drop' ? 'inspect' : 'drop'); setMobilePanel(true); }}>
            Drop
          </button>
          <button className="mini only-mobile" onClick={() => setMobilePanel(true)}>Inspector</button>
          <Link to="/" className="mini">Exit</Link>
        </div>
      </header>

      <div className="studio-body">
        <aside className="rail">
          <p className="rail-title mono-xs dim">TOOLS</p>
          <nav className="rail-tools">
            {TOOL_ORDER.map((id) => {
              const Icon = TOOL_ICONS[id];
              return (
                <button key={id} type="button" className={`rail-tool ${state.activeTool === id ? 'is-active' : ''}`}
                  onClick={() => onTool(id)}>
                  <Icon />
                  <span>{TOOLS[id].label}</span>
                  <em>{TOOLS[id].cost}</em>
                </button>
              );
            })}
          </nav>
          <div className="rail-foot">
            <p className="mono-xs dim">HOW TO USE</p>
            <p className="rail-note">Type a brief, then refine in plain words. Every design stays editable in the inspector.</p>
          </div>
        </aside>

        <main className="studio-canvas">
          <div className="canvas-scroll" ref={scroller}>
            {pendingMark && (
              <div className="pending-mark">
                <LogoMark mark={pendingMark} size={44} />
                <div>
                  <p className="mono-xs dim">MARK READY</p>
                  <p className="pending-name">{pendingMark.brand} · {pendingMark.style}</p>
                </div>
                <button className="mini" onClick={() => setPendingMark(null)}>Clear</button>
              </div>
            )}

            {state.thinking && (
              <div className="msg msg-ai thinking">
                <AiHead tool={state.thinking.tool} />
                <div className="ai-body">
                  <div className="thinking-line">
                    <span className="thinking-dots"><i /><i /><i /></span>
                    <span>Generating {TOOLS[state.thinking.tool]?.name.toLowerCase()}…</span>
                    <span className="mono-xs dim">{TOOLS[state.thinking.tool]?.cost} credits</span>
                  </div>
                  <div className="skeleton" />
                </div>
              </div>
            )}

            {messages.length === 0 && !state.thinking ? (
              <Welcome onPick={send} tool={state.activeTool} onTool={onTool} />
            ) : (
              messages.map((m) =>
                m.role === 'user' ? (
                  <div className="msg msg-user" key={m.id}>
                    <div className="bubble-user">{m.text}</div>
                  </div>
                ) : m.artifact ? (
                  <div className="msg msg-ai" key={m.id}>
                    <AiHead tool={m.artifact.tool} />
                    <div className="ai-body">
                      <p className="ai-text">{m.text}</p>
                      <div className="artifact-card">
                        <div className="artifact-card-head">
                          <span className="mono-xs dim">{m.artifact.title || TOOLS[m.artifact.tool]?.name || 'Generation'}</span>
                          <span className="mono-xs dim">{m.artifact.params.brand}</span>
                        </div>
                        <ArtifactView artifact={m.artifact}
                          onSelectMark={(i) => dispatch({ type: 'patchArtifact', id: m.artifact.id, patch: { selected: i } })}
                          onAction={(a) => handleAction(m.artifact, a)} />
                        <ArtifactActions artifact={m.artifact} onAction={(a) => handleAction(m.artifact, a)} showRefine />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="msg msg-ai" key={m.id}>
                    <AiHead />
                    <div className="ai-body"><p className="ai-text">{m.text}</p></div>
                  </div>
                )
              )
            )}
          </div>

          <Composer draft={draft} setDraft={setDraft} send={send} tool={state.activeTool} credits={state.credits}
            onFile={onFile} fileRef={fileRef} />
        </main>

        <aside className={`inspector ${mobilePanel ? 'is-open' : ''}`}>
          <div className="inspector-head">
            <div className="inspector-tabs">
              <button className={panel === 'inspect' ? 'is-active' : ''} onClick={() => setPanel('inspect')}>Inspect</button>
              <button className={panel === 'drop' ? 'is-active' : ''} onClick={() => setPanel('drop')}>Drop</button>
            </div>
            <button className="inspector-close mini" onClick={() => setMobilePanel(false)}>Close</button>
          </div>
          <div className="inspector-scroll">
            {panel === 'inspect' ? (
              <Inspector controls={state.controls} setControl={setControl} tool={state.activeTool}
                lastArtifact={lastArtifact} run={run} pendingMark={pendingMark} onFile={onFile} fileRef={fileRef} />
            ) : (
              <DropSummary messages={messages} credits={state.credits} onReset={() => dispatch({ type: 'reset' })} />
            )}
          </div>
        </aside>
      </div>
      {mobilePanel && <div className="scrim" onClick={() => setMobilePanel(false)} />}
    </div>
  );
}

function AiHead({ tool }) {
  return (
    <div className="ai-head">
      <span className="ai-avatar">J</span>
      <span className="mono-xs">{tool ? TOOLS[tool]?.name : 'JARVIS'}</span>
      <span className="ai-live"><i /> engine</span>
    </div>
  );
}

function Welcome({ onPick, tool, onTool }) {
  return (
    <div className="welcome">
      <p className="mono-xs dim">NEW DROP · NOTHING GENERATED YET</p>
      <h1 className="welcome-title">
        What will you <em>create</em> today?
      </h1>
      <p className="welcome-sub">Describe a garment, a brand or a print. JARVIS returns a mockup, a mark, or a full production set — then you refine it in words.</p>
      <div className="welcome-grid">
        {QuickStart.map((q) => (
          <button key={q.tool} className="quick" type="button" onClick={() => { onTool(q.tool); onPick(q.prompt); }}>
            <span className="quick-tool mono-xs">{TOOLS[q.tool].label}</span>
            <span className="quick-prompt">{q.prompt}</span>
            <Icons.arrow />
          </button>
        ))}
      </div>
    </div>
  );
}

const QuickStart = [
  { tool: 'logo', prompt: 'I am starting a gothic streetwear label called SAINT. Give me logo options.' },
  { tool: 'mockup', prompt: 'Put SAINT on an oversized washed black hoodie with a large back print.' },
  { tool: 'photoshoot', prompt: 'Show the hoodie on a model, editorial studio shot.' },
  { tool: 'techpack', prompt: 'Prepare the production tech pack and size chart.' },
];

function Composer({ draft, setDraft, send, tool, credits, onFile, fileRef }) {
  const [attachName, setAttachName] = useState(null);
  const prompts = TOOL_PROMPTS[tool] || TOOL_PROMPTS.mockup;
  return (
    <div className="composer-wrap">
      <div className="composer">
        <div className="composer-tools">
          <span className="composer-tool mono-xs"><Icons.spark size={14} /> {TOOLS[tool].label} · {TOOLS[tool].cost} cr</span>
          <span className="composer-chips">
            {prompts.slice(0, 2).map((p) => (
              <button key={p} type="button" className="chip chip-ghost" onClick={() => setDraft(p)}>{p}</button>
            ))}
          </span>
        </div>
        <div className="composer-row">
          <button className="attach" type="button" onClick={() => fileRef.current?.click()} title="Add a reference image (image to image)">
            <Icons.upload size={16} />
          </button>
          <input ref={fileRef} type="file" accept="image/*" hidden
            onChange={(e) => { const f = e.target.files?.[0]; if (f) { setAttachName(f.name); onFile(f); } e.target.value = ''; }} />
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            placeholder={attachName ? `Reference: ${attachName} — describe the print you want` : 'Describe your garment, brand or print…'}
            rows={1}
          />
          <button className="send" type="button" onClick={() => send()} disabled={!draft.trim() || credits < 1}>
            <Icons.arrow size={18} />
          </button>
        </div>
        <p className="composer-foot mono-xs dim">
          Enter to send · Shift+Enter for a new line · {credits} credits left · output is 1-colour, print-ready
        </p>
        {credits < 5 && (
          <Link to="/pricing" className="topup">
            {credits === 0 ? 'Out of credits — top up to keep designing' : 'Running low on credits — top up'}
          </Link>
        )}
      </div>
    </div>
  );
}

function Field({ label, children, hint }) {
  return (
    <div className="field">
      <div className="field-head"><span className="mono-xs dim">{label}</span>{hint && <span className="mono-xs dim">{hint}</span>}</div>
      {children}
    </div>
  );
}

function Inspector({ controls, setControl, tool, lastArtifact, run, pendingMark, onFile, fileRef }) {
  return (
    <div className="inspector-inner">
      <div className="inspector-block">
        <p className="mono-xs dim">GARMENT</p>
        <div className="garment-grid">
          {GARMENTS.map((g) => (
            <button key={g.id} type="button" className={`garment-btn ${controls.garment === g.id ? 'is-active' : ''}`}
              onClick={() => setControl({ garment: g.id })}>
              <span className="garment-ico">{GARMENT_GLYPH[g.id] || GARMENT_GLYPH.tee}</span>
              <span>{g.short}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="inspector-block">
        <Field label="COLOURWAY">
          <div className="swatches">
            {COLORWAYS.map((c) => (
              <button key={c.id} type="button" aria-label={c.name} title={c.name}
                className={`swatch-btn ${controls.colorway === c.id ? 'is-active' : ''}`}
                style={{ background: c.hex }} onClick={() => setControl({ colorway: c.id })} />
            ))}
          </div>
        </Field>

        <Field label="PRINT PLACEMENT">
          <div className="seg">
            {['chest', 'back', 'sleeve'].map((p) => (
              <button key={p} type="button" className={controls.placement === p ? 'is-active' : ''}
                onClick={() => setControl({ placement: p })}>{p}</button>
            ))}
          </div>
        </Field>

        <Field label="PRINT SCALE">
          <div className="seg">
            {['small', 'medium', 'large'].map((s) => (
              <button key={s} type="button" className={controls.scale === s ? 'is-active' : ''}
                onClick={() => setControl({ scale: s })}>{s}</button>
            ))}
          </div>
        </Field>

        <Field label="WASH / DISTRESS" hint={`${Math.round(controls.wash * 100)}%`}>
          <input type="range" min="0" max="1" step="0.02" value={controls.wash}
            onChange={(e) => setControl({ wash: Number(e.target.value) })} className="range" />
        </Field>

        <Field label="FIT">
          <div className="seg">
            {['regular', 'boxy', 'oversized'].map((f) => (
              <button key={f} type="button" className={controls.fit === f ? 'is-active' : ''}
                onClick={() => setControl({ fit: f })}>{f}</button>
            ))}
          </div>
        </Field>
      </div>

      <div className="inspector-block">
        <Field label="PRINT METHOD">
          <select value={controls.printMethod} onChange={(e) => setControl({ printMethod: e.target.value })}>
            <option value="screen">Screen print · 1 colour</option>
            <option value="puff">Puff print</option>
            <option value="embroidery">Embroidery</option>
            <option value="dtg">DTG</option>
            <option value="none">No print</option>
          </select>
        </Field>
        <Field label="PRODUCTION QTY">
          <div className="qty">
            {[50, 100, 300, 500, 1000].map((q) => (
              <button key={q} type="button" className={Number(controls.qty) === q ? 'is-active' : ''}
                onClick={() => setControl({ qty: q })}>{q}</button>
            ))}
          </div>
        </Field>
        <Field label="UNIT">
          <div className="seg">
            {['cm', 'in'].map((u) => (
              <button key={u} type="button" className={controls.unit === u ? 'is-active' : ''}
                onClick={() => setControl({ unit: u })}>{u}</button>
            ))}
          </div>
        </Field>
        <Field label="REFERENCE (IMAGE → IMAGE)">
          <div className="ref-upload">
            {controls.refImage ? (
              <>
                <img src={controls.refImage} alt="reference" />
                <div className="ref-actions">
                  <button className="mini" onClick={() => fileRef.current?.click()}>Replace</button>
                  <button className="mini" onClick={() => setControl({ refImage: null })}>Remove</button>
                </div>
              </>
            ) : (
              <button className="ref-drop" type="button" onClick={() => fileRef.current?.click()}>
                <Icons.upload size={16} /> Upload a reference image
              </button>
            )}
          </div>
        </Field>
      </div>

      <div className="inspector-block inspector-run">
        <p className="mono-xs dim">GENERATE</p>
        <div className="run-list">
          {['mockup', 'photoshoot', 'vector', 'techpack'].map((t) => (
            <button key={t} className="run-btn" type="button"
              onClick={() => run(t, lastArtifact?.params?.prompt || controls.prompt || 'Continue the drop', { mark: pendingMark || lastArtifact?.mark || null })}>
              <span>{TOOLS[t].label}</span>
              <em>{TOOLS[t].cost} cr</em>
            </button>
          ))}
        </div>
        <p className="inspector-note">Inspector changes apply to the latest design free of charge.</p>
      </div>
    </div>
  );
}

/** Downscale uploads so reference images stay small enough to persist. */
function shrinkImage(file, max = 900) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext('2d');
        if (!ctx) return resolve(String(reader.result));
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.82));
      };
      img.onerror = () => resolve(String(reader.result));
      img.src = String(reader.result);
    };
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}

const GARMENT_GLYPH = {
  hoodie: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M14 8c0 4 2 6 6 6s6-2 6-6l6 3 5 8-4 2v13H7V21l-4-2 5-8z" /><path d="M14 8c-1 4-1 8 6 8s7-4 6-8" /></svg>
  ),
  tee: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M15 8l-9 5 3 7 4-2v15h14V18l4 2 3-7-9-5c-1 3-3 4-5 4s-4-1-5-4z" /></svg>
  ),
  crew: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M15 8l-9 6 3 9 4-2v12h14V21l4 2 3-9-9-6c-1 3-3 4-5 4s-4-1-5-4z" /></svg>
  ),
  bomber: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M15 8l-9 6-2 8 5 1v11h22V23l5-1-2-8-9-6H15z" /><path d="M20 12v22" /></svg>
  ),
  longsleeve: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M15 8l-10 8-2 12h6l3-8v14h16V20l3 8h6l-2-12-10-8c-1 2-3 3-5 3s-4-1-5-3z" /></svg>
  ),
  cargo: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M12 6h16v6l2 22h-8l-2-16-2 16h-8l2-22z" /><path d="M12 12h16" /></svg>
  ),
  shorts: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M12 8h16v6l2 12h-7l-3-9-3 9h-7l2-12z" /></svg>
  ),
  cap: (
    <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M9 26c0-9 5-14 11-14s11 5 11 14z" /><path d="M29 22c4 0 7 2 7 4-3 2-7 1-9-1" /></svg>
  ),
};

function DropSummary({ messages, credits, onReset }) {
  const artifacts = messages.filter((m) => m.artifact).map((m) => m.artifact);
  const kinds = artifacts.reduce((acc, a) => ({ ...acc, [a.tool]: (acc[a.tool] || 0) + 1 }), {});
  const brand = artifacts[0]?.params?.brand || '—';
  return (
    <div className="inspector-inner">
      <div className="drop-head">
        <p className="mono-xs dim">DROP SUMMARY</p>
        <h3>{brand}</h3>
        <p className="mono-xs dim">{artifacts.length} assets · {credits} credits left</p>
      </div>
      <div className="drop-kinds">
        {Object.entries(kinds).length === 0 && <p className="inspector-note">Nothing generated yet.</p>}
        {Object.entries(kinds).map(([k, n]) => (
          <div key={k} className="drop-kind">
            <span>{TOOLS[k]?.name || k}</span>
            <em>{n}</em>
          </div>
        ))}
      </div>
      {artifacts.length > 0 && (
        <div className="drop-list">
          <p className="mono-xs dim">ASSETS</p>
          {artifacts.slice().reverse().map((a) => (
            <div key={a.id} className="drop-asset">
              <span className="drop-thumb">{a.kind === 'logo' ? 'Aa' : a.kind === 'mockup' ? '⌂' : '◻'}</span>
              <span>{a.title}</span>
              <em>{TOOLS[a.tool]?.cost} cr</em>
            </div>
          ))}
        </div>
      )}
      <button className="mini wide" onClick={onReset}>Start a new drop</button>
    </div>
  );
}
