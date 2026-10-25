import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, Link } from '../router.jsx';
import { Nav, Footer } from '../components/SiteChrome.jsx';
import { Icons } from '../components/Icons.jsx';
import { LogoMark, GarmentMockup, TechDrawing, VectorArt } from '../lib/Garments.jsx';
import { Artwork } from '../components/Artwork.jsx';
import PricingTable from '../components/PricingTable.jsx';
import { logoBatch, makeLogo, sizeChart, priceEstimate, TOOLS, TOOL_ORDER, GARMENTS } from '../lib/engine.js';

const HERO_PROMPTS = [
  'A washed black oversized hoodie for a gothic label called SAINT.',
  'A minimal ivory tee with a small serif monogram on the chest.',
  'Logo options for a techno collective, brutalist and one colour.',
  'A five-shot lookbook of my drop on a model, studio light.',
];

export default function Landing() {
  const { navigate } = useRouter();
  const marks = useMemo(() => logoBatch({ seed: 4211, brand: 'SAINT', ink: '#111110', count: 6 }), []);
  const [prompt, setPrompt] = useState('');
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % HERO_PROMPTS.length), 3600);
    return () => clearInterval(t);
  }, []);

  const start = (text) => {
    const value = (text ?? prompt).trim();
    if (value) sessionStorage.setItem('jarvis.pending', value);
    navigate('/studio');
  };

  return (
    <div className="site">
      <Nav />
      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><Icons.spark size={14} /> AI · your personal clothing design studio</p>
            <h1 className="display">
              Design your<br />
              <em>clothing brand</em> with AI.
            </h1>
            <p className="hero-lede">
              Create realistic clothing mockups, logos, photoshoots, vectors, tech packs and 3D models
              by describing what you want. One conversation, one colour, print-ready output.
            </p>
            <div className="hero-cta">
              <button className="btn btn-solid lg" onClick={() => navigate('/studio')}>
                Start designing <Icons.arrow />
              </button>
              <a className="btn btn-line lg" href="#how">
                See how it works
              </a>
            </div>
            <dl className="hero-stats">
              <div><dt>12K+</dt><dd>designs created</dd></div>
              <div><dt>2,000+</dt><dd>creators</dd></div>
              <div><dt>&lt;60s</dt><dd>per result</dd></div>
            </dl>
          </div>

          <div className="hero-visual">
            <figure className="hero-shot">
              <img src="/assets/hero-hoodie.jpg" alt="Black oversized hoodie with a screen-printed back graphic" />
              <figcaption>
                <span className="mono-xs dim">SAINT · DROP 01</span>
                <span>Oversized hoodie · back print</span>
              </figcaption>
            </figure>
            <div className="hero-card hero-card-mark">
              <div className="hero-card-head"><span className="mono-xs dim">LOGO · 1 OF 4</span></div>
              <LogoMark mark={marks[0]} size={92} />
              <p className="mono-xs dim">SAINT — wordmark</p>
            </div>
            <div className="hero-chip">
              <span className="hero-chip-dot" />
              <p>“Make the back graphic bigger and more washed-out.”</p>
              <span className="mono-xs dim">updated in 42s</span>
            </div>
            <div className="hero-badge mono-xs">MONOCHROME · PRINT-READY</div>
          </div>
        </section>

        <PromptBar value={prompt} setValue={setPrompt} onSubmit={start} rotating={HERO_PROMPTS[idx]} />

        <div className="ticker" aria-hidden="true">
          <div className="ticker-track">
            {[0, 1].map((k) => (
              <span key={k}>
                MOCKUPS <i /> LOGOS <i /> PHOTOSHOOTS <i /> VECTORS <i /> TECH PACKS <i /> SIZE CHARTS
                <i /> PRICE ESTIMATES <i /> 3D MODELS <i /> IMAGE TO IMAGE <i /> TEXT TO IMAGE <i />
              </span>
            ))}
          </div>
        </div>

        <HowItWorks marks={marks} onStart={start} />

        <Tools marks={marks} />

        <Gallery marks={marks} />

        <section className="section pricing-section" id="pricing">
          <div className="section-head">
            <p className="eyebrow">Pricing</p>
            <h2 className="display">Start your next collection.<br /><em>Pay in credits.</em></h2>
            <p className="section-lede">Every tool draws from one credit balance. No seats, no hidden fees, cancel any time.</p>
          </div>
          <PricingTable />
        </section>

        <section className="section about" id="about">
          <div className="about-grid">
            <div>
              <p className="eyebrow">About JARVIS</p>
              <h2 className="display">Fashion design,<br /><em>made accessible.</em></h2>
            </div>
            <div className="about-copy">
              <p>
                JARVIS began with a simple idea: anyone with a vision for clothing should be able to see it
                before they pay for a sample. No design degree, no agency retainer, no minimum order to get
                started.
              </p>
              <p>
                Describe the garment and the mood. JARVIS writes the brand system, draws the mark, presses it
                onto the garment, shoots it, and hands you the production file — all in one thread you can
                keep editing.
              </p>
              <dl className="about-stats">
                <div><dt>12K+</dt><dd>designs created</dd></div>
                <div><dt>2,000+</dt><dd>creators</dd></div>
                <div><dt>11</dt><dd>AI design tools</dd></div>
                <div><dt>1</dt><dd>colour, print-ready</dd></div>
              </dl>
            </div>
          </div>
        </section>

        <section className="cta">
          <div className="cta-inner">
            <p className="eyebrow">Ready when you are</p>
            <h2 className="display">Your next drop starts<br />with <em>one sentence.</em></h2>
            <p className="section-lede">Type it, and JARVIS takes it from the first mockup to the tech pack.</p>
            <div className="cta-actions">
              <button className="btn btn-solid lg" onClick={() => navigate('/studio')}>Start designing <Icons.arrow /></button>
              <button className="btn btn-line lg" onClick={() => navigate('/pricing')}>See pricing</button>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}

function PromptBar({ value, setValue, onSubmit, rotating }) {
  const inputRef = useRef(null);
  return (
    <div className="promptbar-wrap">
      <form className="promptbar" onSubmit={(e) => { e.preventDefault(); onSubmit(value); }}>
        <span className="promptbar-icon"><Icons.spark size={16} /></span>
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={rotating}
          aria-label="Describe the clothing design you want"
        />
        <span className="promptbar-tool mono-xs hide-sm">{TOOLS.mockup.label}</span>
        <button className="btn btn-solid" type="submit">
          Generate <Icons.arrow size={15} />
        </button>
      </form>
      <div className="promptbar-chips">
        {['Oversized hoodie', 'Logo options', 'On a model', 'Tech pack', '3D model'].map((c) => (
          <button key={c} className="chip" type="button" onClick={() => { setValue(c); inputRef.current?.focus(); }}>{c}</button>
        ))}
      </div>
    </div>
  );
}

function SectionHead({ eyebrow, title, lede }) {
  return (
    <div className="section-head">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="display">{title}</h2>
      {lede && <p className="section-lede">{lede}</p>}
    </div>
  );
}

function HowItWorks({ marks, onStart }) {
  const [step, setStep] = useState(0);
  const steps = [
    { n: '01', key: 'idea', title: 'Idea', body: 'Describe a brand, a mood, a garment. JARVIS reads the brief and writes the system: name, typography, mark direction.' },
    { n: '02', key: 'mockup', title: 'Mockup', body: 'A photoreal-style technical flat of the exact garment, colourway and print placement you asked for.' },
    { n: '03', key: 'refine', title: 'Refine', body: 'Type a change in plain words — bigger, washed-out, inverted, moved to the chest. The design updates in place.' },
    { n: '04', key: 'shoot', title: 'Photoshoot', body: 'Press the same print onto a model, in the studio, then animate it into a five-second vertical loop.' },
    { n: '05', key: 'production', title: 'Production', body: 'Vector line art, an A4 tech pack, a size chart, a cost estimate and a 3D model for your store page.' },
  ];
  const active = steps[step];

  return (
    <section className="section how" id="how">
      <SectionHead
        eyebrow="How it works"
        title={<>Watch an idea become<br /><em>a clothing project.</em></>}
        lede="One conversation takes a label from a first sentence to a production-ready drop. Follow along."
      />
      <div className="how-grid">
        <ol className="how-steps">
          {steps.map((s, i) => (
            <li key={s.key}>
              <button className={i === step ? 'is-active' : ''} onClick={() => setStep(i)}>
                <span className="step-n mono-xs">{s.n}</span>
                <span className="step-copy">
                  <strong>{s.title}</strong>
                  <span>{s.body}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
        <div className="how-stage">
          <div className="how-stage-head">
            <span className="mono-xs dim">SAINT · DROP 01</span>
            <span className="mono-xs dim">{TOOL_LABEL[active.key]}</span>
          </div>
          <div className="how-stage-body" key={active.key}>{renderStage(active.key, marks)}</div>
          <div className="how-stage-foot">
            <span className="mono-xs dim">{STAGE_NOTE[active.key]}</span>
            <button className="btn btn-solid sm" onClick={() => onStart(STAGE_PROMPT[active.key])}>
              Try this <Icons.arrow size={14} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

const TOOL_LABEL = {
  idea: 'LOGO & GRAPHICS',
  mockup: 'TECHNICAL MOCKUP',
  refine: 'REFINE',
  shoot: 'PHOTOSHOOT · VIDEO',
  production: 'TECH PACK · SIZE CHART · ESTIMATE',
};
const STAGE_NOTE = {
  idea: 'four marks · one colour · vector',
  mockup: '450 gsm fleece · washed black · large back print',
  refine: 'same mark, same palette, new pieces',
  shoot: 'studio light · 1080p · ready for Reels',
  production: 'A4 · gsm, BOM, measurements, unit cost',
};
const STAGE_PROMPT = {
  idea: 'A dark gothic streetwear label called SAINT. Start with the logo.',
  mockup: 'Put SAINT on an oversized washed black hoodie with a big back graphic.',
  refine: 'Make the back graphic bigger and more washed-out.',
  shoot: 'Show the drop on a model and make a short video for Instagram.',
  production: 'Prepare the vector, tech pack, size chart and price estimate.',
};

function renderStage(key, marks) {
  if (key === 'idea') {
    return (
      <div className="stage-marks">
        {marks.slice(0, 4).map((m, i) => (
          <div key={m.id} className={`stage-mark ${i === 1 ? 'on-ink' : ''}`}>
            <LogoMark mark={m} size={150} wash={0.06} />
            <span className="mono-xs dim">{m.style}</span>
          </div>
        ))}
      </div>
    );
  }
  if (key === 'mockup') {
    return (
      <div className="stage-mockup">
        <GarmentMockup garment="hoodie" colorway="washed-black" mark={{ ...marks[0], style: 'wordmark' }}
          placement="back" scale="large" wash={0.24} />
      </div>
    );
  }
  if (key === 'refine') {
    return (
      <div className="stage-pair">
        <div>
          <GarmentMockup garment="tee" colorway="ivory" mark={marks[2]} placement="chest" scale="medium" wash={0.1} />
          <span className="mono-xs dim">Tee · chest</span>
        </div>
        <div>
          <GarmentMockup garment="crew" colorway="grey" mark={marks[2]} placement="chest" scale="large" wash={0.2} />
          <span className="mono-xs dim">Crewneck · large</span>
        </div>
      </div>
    );
  }
  if (key === 'shoot') {
    return (
      <div className="stage-shoot">
        <div className="stage-photo">
          <img src="/assets/model-2.jpg" alt="Model wearing the generated print" />
          <div className="stage-print" style={{ left: '30%', top: '43%', width: '19%', mixBlendMode: 'screen' }}>
            <LogoMark mark={{ ...marks[0], ink: '#f4f4ef' }} size={200} wash={0.15} />
          </div>
          <span className="hud-pill">Editorial · mid grey</span>
        </div>
        <div className="stage-photo small">
          <img src="/assets/model-1.jpg" alt="Second pose" />
          <div className="stage-print" style={{ left: '40%', top: '28%', width: '20%', mixBlendMode: 'multiply' }}>
            <LogoMark mark={{ ...marks[0], ink: '#141412' }} size={160} wash={0.12} />
          </div>
          <span className="hud-pill">Studio · front</span>
        </div>
      </div>
    );
  }
  const chart = sizeChart('hoodie', 'oversized', 'cm');
  const est = priceEstimate({ garment: 'hoodie', qty: 300, print: 'screen' });
  return (
    <div className="stage-production">
      <div className="stage-tech">
        <TechDrawing garment="hoodie" printMark={marks[0]} showNotes={false} />
        <span className="mono-xs dim">A4 tech pack · front</span>
      </div>
      <div className="stage-side">
        <div className="mini-chart">
          <table>
            <thead><tr><th>cm</th><th>S</th><th>M</th><th>L</th><th>XL</th></tr></thead>
            <tbody>
              {['chest', 'length', 'sleeve'].map((k) => (
                <tr key={k}>
                  <td className="cap">{k}</td>
                  {chart.slice(1, 5).map((c) => <td key={c.size}>{c[k]}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mini-estimate">
          <p className="mono-xs dim">300 HOODIES</p>
          <p className="mini-price">${est.perLow}–${est.perHigh}<span>/pc</span></p>
          <div className="bars">
            {est.breakdown.map((b) => (
              <div className="bar-row" key={b.label}>
                <span className="mono-xs">{b.label}</span>
                <span className="bar"><i style={{ width: `${(b.value / 5) * 100}%` }} /></span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Tools({ marks }) {
  const [tab, setTab] = useState('all');
  const items = [
    { id: 'mockup', title: 'AI mockups', body: 'Any garment, flat or worn, from a sentence or a reference photo.', art: <GarmentMockup garment="crew" colorway="washed-black" mark={marks[3]} placement="chest" scale="large" wash={0.2} /> },
    { id: 'logo', title: 'Logo design', body: 'Wordmarks, monograms, badges and seals — one colour, vector.', art: <LogoMark mark={marks[1]} size={220} wash={0.08} /> },
    { id: 'photoshoot', title: 'Photoshoots', body: 'Your print on a model, studio-lit, then animated into a loop.', art: <img src="/assets/model-1.jpg" alt="Model in a generated tee" /> },
    { id: 'vector', title: 'Vector graphics', body: 'Clean line art for embroidery and screen printing.', art: <VectorArt mark={marks[4]} size={220} /> },
    { id: 'techpack', title: 'Tech packs', body: 'Manufacturer-ready spec sheets with BOM and measurements.', art: <TechDrawing garment="hoodie" showNotes printMark={marks[0]} /> },
    { id: 'model3d', title: '3D generation', body: 'Spin-ready models you can embed on your store page.', art: <div className="spin3d"><GarmentMockup garment="hoodie" colorway="ink" mark={marks[2]} placement="chest" scale="medium" /></div> },
    { id: 'estimate', title: 'Price estimates', body: 'Know your unit cost before you call a factory.', art: <div className="tool-mini-est"><span>$/pc</span><strong>$14–19</strong><span className="mono-xs dim">300 pcs · EU</span></div> },
    { id: 'sizechart', title: 'Size charts', body: 'Professional charts in cm or inches, any fit.', art: <MiniChart /> },
    { id: 'img2img', title: 'Image to image', body: 'Upload a photo or screenshot — JARVIS vectorises it into one-colour dots you can print.', art: <Artwork spec={{ mode: 'procedural', motif: 'halftone', seed: 991, density: 13, invert: false, word: 'MONO', rotation: 0 }} /> },
    { id: 'text2img', title: 'Text to image', body: 'Eight print styles — halftone, brutalist type, arches, orbits — from one sentence.', art: <Artwork spec={{ mode: 'procedural', motif: 'brutal', seed: 88, density: 8, invert: true, word: 'SAINT', rotation: 0 }} /> },
  ];
  const filtered = tab === 'all' ? items : items.filter((i) => i.id === tab);

  return (
    <section className="section tools" id="tools">
      <SectionHead
        eyebrow="The engine"
        title={<>Every tool your brand needs.<br /><em>In one thread.</em></>}
        lede="Eleven generators, one credit balance. Nothing to install, nothing to export between apps."
      />
      <div className="tools-tabs">
        {['all', 'mockup', 'logo', 'photoshoot', 'vector', 'techpack'].map((t) => (
          <button key={t} className={tab === t ? 'is-active' : ''} onClick={() => setTab(t)}>
            {t === 'all' ? 'Everything' : TOOLS[t].label}
          </button>
        ))}
      </div>
      <div className={`tools-grid ${filtered.length === 1 ? 'is-single' : ''}`}>
        {filtered.map((item) => (
          <article key={item.id} className="tool-card">
            <div className="tool-art">{item.art}</div>
            <div className="tool-copy">
              <h3>{item.title}</h3>
              <p>{item.body}</p>
              <span className="mono-xs dim">{TOOLS[item.id].cost} credits · {TOOLS[item.id].blurb}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MiniChart() {
  const chart = sizeChart('tee', 'boxy', 'cm');
  return (
    <div className="mini-chart big">
      <table>
        <thead><tr><th>cm</th>{chart.slice(1, 5).map((c) => <th key={c.size}>{c.size}</th>)}</tr></thead>
        <tbody>
          {['chest', 'length', 'sleeve'].map((k) => (
            <tr key={k}><td className="cap">{k}</td>{chart.slice(1, 5).map((c) => <td key={c.size}>{c[k]}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Gallery({ marks }) {
  const items = [
    { src: '/assets/gallery-jacket.jpg', label: 'Varsity bomber', kind: 'Mockup' },
    { node: <GarmentMockup garment="hoodie" colorway="washed-black" mark={{ ...marks[0], style: 'badge' }} placement="back" scale="large" wash={0.3} />, label: 'SAINT hoodie', kind: 'Mockup' },
    { src: '/assets/gallery-knit.jpg', label: 'Cable-knit sweater', kind: 'Still life' },
    { node: <GarmentMockup garment="tee" colorway="ivory" mark={{ ...marks[1], style: 'minimal' }} placement="chest" scale="small" />, label: 'Bone tee', kind: 'Mockup' },
    { src: '/assets/model-2.jpg', label: 'Editorial shoot', kind: 'Photoshoot' },
    { node: <GarmentMockup garment="crew" colorway="charcoal" mark={{ ...marks[2], style: 'gothic' }} placement="chest" scale="medium" wash={0.18} />, label: 'Charcoal crew', kind: 'Mockup' },
    { src: '/assets/gallery-tee.jpg', label: 'Washed tee', kind: 'Product' },
    { node: <GarmentMockup garment="cargo" colorway="ink" mark={{ ...marks[3], style: 'wordmark' }} placement="chest" scale="small" />, label: 'Cargo pants', kind: 'Technical mockup' },
  ];
  return (
    <section className="section gallery" id="gallery">
      <SectionHead
        eyebrow="Gallery"
        title={<>What the engine<br /><em>actually makes.</em></>}
        lede="A few results generated in the studio. No Photoshop, no design skills, one colour throughout."
      />
      <div className="gallery-grid">
        {items.map((item, i) => (
          <figure key={i} className={`gallery-item ${item.node ? 'is-generated' : ''} ${i % 5 === 0 ? 'tall' : ''}`}>
            <div className="gallery-media">
              {item.node || <img src={item.src} alt={item.label} />}
            </div>
            <figcaption>
              <span>{item.label}</span>
              <span className="mono-xs dim">{item.kind}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
