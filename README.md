# JARVIS — AI clothing & logo studio

A complete, working AI design studio for clothing brands: **text to image**, **image to image**, garment
mockups, logo generation, photoshoots, photoshoot video, vectors, tech packs, size charts, price estimates
and 3D models — all in one dark, monochrome workspace.

Everything is rendered live as vector art, so every artefact can be downloaded as **SVG** (print-ready,
one colour) or **PNG**, and nothing depends on external image services.

```bash
npm install
npm run dev      # http://localhost:5173  (marketing site + /studio + /pricing)
npm run build && npm start   # production build on :5173
```

---

## What's inside

### Marketing site (`/`)
- Editorial monochrome landing page: hero with live campaign imagery, prompt bar, marquee, stats.
- **How it works** — an interactive 5-step walkthrough (idea → mockup → refine → photoshoot → production)
  that renders real generated artwork at each stage.
- **Tools** — filterable grid of all 11 generators, each preview rendered by the same engine as the studio.
- **Gallery** — mix of photography and generated garment mockups.
- **Pricing** — three plans, monthly/annual toggle (20% off), credit cost table, FAQ page at `/pricing`.

### Studio (`/studio`)
Three-column dark workspace:

| Column | What it does |
| --- | --- |
| **Rail** | Pick one of 11 tools; each shows its credit cost. |
| **Canvas** | Conversational thread. Briefs become artefacts, and later sentences refine them. |
| **Inspector** | Live, free editing of the latest design + a "Drop" panel listing every generated asset. |

**Generation flow**
1. Type a brief ("A gothic label called SAINT, oversized washed black hoodie with a big back print").
2. The engine parses brand, garment, style, colourway, placement and scale.
3. A tool runs with a short "generating" state and returns an artefact card with contextual next actions.
4. Follow-ups are understood as edits (`bigger`, `more washed-out`, `invert`, `move to the chest`,
   `cleaner`, `smaller`). Edits target the newest *garment* artefact, not just the last message.

**Tools**

| Tool | Cost | Output |
| --- | --- | --- |
| Text → Image | 2 | One-colour print artwork in 8 styles (halftone, type stack, stripes, arches, checker, brutalist, orbit, gradient) with live density / ink / word controls |
| Image → Image | 4 | Upload a photo; it is **vectorised** into one-colour dots (tones, contrast, dot size/shape, invert) and can be pressed onto any garment |
| Mockup | 2 | Technical garment flat: 8 garments × 6 colourways, front/back/sleeve placement |
| Logo | 3 | 4 marks per run across 8 styles (wordmark, monogram, badge, seal, gothic, emblem, minimal, brutal) |
| Photoshoot | 3 | Print composited onto model photography in the correct tonal blend |
| Photoshoot video | 25 | Animated 9:16 loop with live progress UI |
| Vector | 3 | Screen-print / embroidery line art, SVG export |
| Tech pack | 3 | A4 spec sheet: BOM, construction notes, fabric, GSM, measurement chart |
| Size chart | 1 | XS–XXL in cm or inches, fit-aware, CSV export |
| Price estimate | 1 | Unit cost + order total + cost breakdown, recalculated live by quantity |
| 3D model | 20 | Drag-to-spin turntable with wireframe toggle, `.glb` framing |

### Image → image, honestly vectorised
Uploads are sampled into an 84 × 84 luminance grid in the browser, then re-drawn as
one-colour dots (circle or square, 2–8 tone separations). The result is real vector geometry:
it scales, exports as SVG, presses onto light or dark garments, and never depends on the
uploaded bitmap loading at render time.

### Design system
Strictly black and white: ink `#0b0b0a`, paper `#f4f3ef`, plus a monochrome studio palette.
Type pairing is **Instrument Serif** (display, italic accents) and **Space Grotesk** (UI, mono-ish caps).
No colour anywhere in the product — artwork is generated one colour so it survives screen printing.

---

## Architecture

```
src/
  App.jsx                 route switch (/, /pricing, /studio)
  router.jsx              tiny history router (<Link>, useRouter)
  store.jsx               studio state, credits, brief parsing, generation jobs (useReducer + context)
  styles.css              marketing design system
  studio.css              workspace + artefact views
  lib/
    engine.js             brief parsing, logo/mark specs, price + size math, tool catalogue
    Garments.jsx          SVG logo marks, garment flats, mockup compositor, tech drawings
  components/
    Artwork.jsx           procedural print artwork + reference conversion
    Artifact.jsx          artefact views, SVG/PNG/CSV exporters, photoshoot, turntable, tech pack
    Icons.jsx, SiteChrome.jsx, PricingTable.jsx
  pages/
    Landing.jsx, Pricing.jsx, Studio.jsx
server/index.js           Express: Vite middleware in dev, static build in production
```

Generation is deterministic: a brief + seed produces the same mark, garment and spec every time, which is
what makes "refine this" feel stable. Marks are pure SVG geometry (no bitmaps), so the same object is used
for the logo card, the garment print, the vector file and the tech-pack drawing.

### Plugging in a hosted diffusion model
The engine is deliberately isolated behind two seams:

- `buildArtifact(tool, prompt, controls, prevMark, seed)` in `src/store.jsx` — returns the artefact object.
- `<Artwork spec>` in `src/components/Artwork.jsx` — renders a print from a spec.

Swap `makeArtworkSpec` for an API call that returns an image URL, store it on `artifact.art.source`, and
render an `<image>` in `Artwork`; the mockup compositor, photoshoot overlay, vectoriser and tech pack all
keep working unchanged because they consume the same spec objects.

---

## Notes
- Credits are simulated client-side (225 on the Creator plan); generation never calls a paid service.
- Studio state persists to `localStorage` (uploaded references are downscaled to keep it small).
- Exports run entirely in the browser: SVG is serialised from the live DOM, PNG via canvas.
- Responsive: side-by-side workspace on desktop, scrollable tool rail + bottom-sheet inspector on mobile.
