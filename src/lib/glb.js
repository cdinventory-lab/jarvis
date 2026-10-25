/* ------------------------------------------------------------------
   Real .glb export — glTF 2.0 binary, built without dependencies.

   A garment silhouette is sampled from its SVG path, extruded into a
   thin prism (front face, back face, side wall) and textured with the
   rendered mockup, so the file opens in any glTF viewer and can be
   embedded on a storefront with <model-viewer>.
------------------------------------------------------------------- */

/* ----------------------------- geometry -------------------------- */

/**
 * Sample an SVG path (M / L / C / Z subset, as used by the garment flats)
 * into points evenly spaced by arc length.
 */
export function samplePathPoints(d, count = 160) {
  const tokens = d.match(/[MLCZmlcz]|-?\d*\.?\d+/g) || [];
  let i = 0;
  let x = 0;
  let y = 0;
  let cmd = null;
  const segs = [];
  const num = () => parseFloat(tokens[i++]);

  while (i < tokens.length) {
    if (/[MLCZ]/.test(tokens[i])) cmd = tokens[i++];
    if (cmd === 'M') {
      x = num(); y = num();
      segs.push({ t: 'M', a: [x, y] });
      cmd = 'L';
    } else if (cmd === 'L') {
      const nx = num(); const ny = num();
      segs.push({ t: 'L', a: [x, y], b: [nx, ny] });
      x = nx; y = ny;
    } else if (cmd === 'C') {
      const p1 = [num(), num()];
      const p2 = [num(), num()];
      const b = [num(), num()];
      segs.push({ t: 'C', a: [x, y], p1, p2, b });
      x = b[0]; y = b[1];
    } else break;
  }

  const segLen = (g) => (g.t === 'L'
    ? Math.hypot(g.b[0] - g.a[0], g.b[1] - g.a[1])
    : Math.hypot(g.p1[0] - g.a[0], g.p1[1] - g.a[1])
      + Math.hypot(g.p2[0] - g.p1[0], g.p2[1] - g.p1[1])
      + Math.hypot(g.b[0] - g.p2[0], g.b[1] - g.p2[1]));

  const drawable = segs.filter((g) => g.t !== 'M');
  const total = drawable.reduce((sum, g) => sum + segLen(g), 0);
  if (!total) return [];

  const at = (g, t) => {
    if (g.t === 'L') return [g.a[0] + (g.b[0] - g.a[0]) * t, g.a[1] + (g.b[1] - g.a[1]) * t];
    const mt = 1 - t;
    return [
      mt * mt * mt * g.a[0] + 3 * mt * mt * t * g.p1[0] + 3 * mt * t * t * g.p2[0] + t * t * t * g.b[0],
      mt * mt * mt * g.a[1] + 3 * mt * mt * t * g.p1[1] + 3 * mt * t * t * g.p2[1] + t * t * t * g.b[1],
    ];
  };

  const pts = [];
  for (let k = 0; k < count; k++) {
    let target = (k / count) * total;
    for (const g of drawable) {
      const len = segLen(g);
      if (target <= len) {
        if (g.t === 'L') {
          const t = len ? target / len : 0;
          pts.push(at(g, t));
        } else {
          let prev = at(g, 0);
          let acc = 0;
          let placed = false;
          for (let s = 1; s <= 64; s++) {
            const t = s / 64;
            const pt = at(g, t);
            acc += Math.hypot(pt[0] - prev[0], pt[1] - prev[1]);
            prev = pt;
            if (acc >= target) { pts.push(pt); placed = true; break; }
          }
          if (!placed) pts.push(g.b);
        }
        break;
      }
      target -= len;
    }
  }
  return pts;
}

/** Signed area of a 2D polygon (screen coords: y grows downwards). */
function area(pts) {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    a += x1 * y2 - x2 * y1;
  }
  return a / 2;
}

/** Strictly inside — points exactly on an edge must not block an ear. */
function pointInTriangle(p, a, b, c, eps = 1e-7) {
  const d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1]);
  const d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1]);
  const d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1]);
  const scale = Math.abs(d1) + Math.abs(d2) + Math.abs(d3) + 1;
  const e = eps * scale;
  return d1 > e && d2 > e && d3 > e || d1 < -e && d2 < -e && d3 < -e;
}

/** Drop duplicate and collinear points so ear clipping cannot stall. */
export function cleanPolygon(pts, eps = 0.02) {
  const out = [];
  for (const p of pts) {
    const last = out[out.length - 1];
    if (last && Math.hypot(p[0] - last[0], p[1] - last[1]) < eps) continue;
    out.push(p);
  }
  if (out.length > 2) {
    const first = out[0];
    const last = out[out.length - 1];
    if (Math.hypot(first[0] - last[0], first[1] - last[1]) < eps) out.pop();
  }
  let changed = true;
  while (changed && out.length > 3) {
    changed = false;
    for (let i = 0; i < out.length; i++) {
      const a = out[(i - 1 + out.length) % out.length];
      const b = out[i];
      const c = out[(i + 1) % out.length];
      const cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
      const scale = Math.hypot(b[0] - a[0], b[1] - a[1]) * Math.hypot(c[0] - b[0], c[1] - b[1]) + 1e-9;
      if (Math.abs(cross) / scale < 0.004) { out.splice(i, 1); changed = true; break; }
    }
  }
  return out;
}

/** Ear-clipping triangulation for simple polygons (convex or not). */
export function triangulatePolygon(rawPts) {
  const pts = cleanPolygon(rawPts);
  const n = pts.length;
  if (n < 3) return [];
  const ccw = area(pts) > 0;
  const idx = pts.map((_, i) => i);
  const tris = [];
  let guard = 0;

  const isConvex = (a, b, c) => {
    const cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    return ccw ? cross > 0 : cross < 0;
  };

  while (idx.length > 3 && guard++ < n * n) {
    let clipped = false;
    for (let i = 0; i < idx.length; i++) {
      const ia = idx[(i - 1 + idx.length) % idx.length];
      const ib = idx[i];
      const ic = idx[(i + 1) % idx.length];
      const a = pts[ia];
      const b = pts[ib];
      const c = pts[ic];
      if (!isConvex(a, b, c)) continue;
      let contains = false;
      for (const j of idx) {
        if (j === ia || j === ib || j === ic) continue;
        if (pointInTriangle(pts[j], a, b, c)) { contains = true; break; }
      }
      if (contains) continue;
      tris.push([ia, ib, ic]);
      idx.splice(i, 1);
      clipped = true;
      break;
    }
    if (!clipped) break; // degenerate polygon; emit what we have
  }
  if (idx.length === 3) tris.push([idx[0], idx[1], idx[2]]);
  return tris;
}

/**
 * Build a non-indexed triangle soup from a garment silhouette.
 * `pts` are SVG coords on an 800×900 artboard; `artboard` lets callers rescale.
 */
export function buildGarmentMesh(pts, {
  artboard = { w: 800, h: 900 },
  thickness = 0.09,
  divisions = 1,
} = {}) {
  const cx = artboard.w / 2;
  const cy = artboard.h / 2;
  const scale = 1 / 400; // keeps the model roughly 2 units tall

  // SVG → 3D. Flip Y so the model is upright in glTF's Y-up space.
  const to3d = ([x, y], z) => [(x - cx) * scale, (cy - y) * scale, z];

  const outline = cleanPolygon(pts);
  const tris = triangulatePolygon(outline);
  const positions = [];
  const normals = [];
  const uvs = [];
  const half = thickness / 2;

  const pushTri = (a, b, c, normal, uvList) => {
    const P = [a, b, c];
    // ensure winding agrees with the supplied normal
    const e1 = [P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]];
    const e2 = [P[2][0] - P[0][0], P[2][1] - P[0][1], P[2][2] - P[0][2]];
    const cr = [
      e1[1] * e2[2] - e1[2] * e2[1],
      e1[2] * e2[0] - e1[0] * e2[2],
      e1[0] * e2[1] - e1[1] * e2[0],
    ];
    const dot = cr[0] * normal[0] + cr[1] * normal[1] + cr[2] * normal[2];
    const ordered = dot < 0 ? [P[0], P[2], P[1]] : P;
    const uvOrdered = dot < 0 ? [uvList[0], uvList[2], uvList[1]] : uvList;
    ordered.forEach((p, i) => {
      positions.push(p[0], p[1], p[2]);
      normals.push(normal[0], normal[1], normal[2]);
      uvs.push(uvOrdered[i][0], uvOrdered[i][1]);
    });
  };

  const uvFor = ([x, y]) => [x / artboard.w, 1 - y / artboard.h];

  // front (+Z) and back (−Z)
  for (const [z, nz] of [[half, 1], [-half, -1]]) {
    for (const [i, j, k] of tris) {
      const P = [outline[i], outline[j], outline[k]].map((p) => to3d(p, z));
      pushTri(P[0], P[1], P[2], [0, 0, nz], [uvFor(outline[i]), uvFor(outline[j]), uvFor(outline[k])]);
    }
  }

  // side wall
  for (let i = 0; i < outline.length; i++) {
    const a = outline[i];
    const b = outline[(i + 1) % outline.length];
    const af = to3d(a, half);
    const bf = to3d(b, half);
    const ab = to3d(b, -half);
    const aa = to3d(a, -half);
    const mx = (a[0] + b[0]) / 2 - cx;
    const my = (a[1] + b[1]) / 2 - cy;
    const len = Math.hypot(mx, my) || 1;
    const side = [mx / len, -my / len, 0];
    const uvA = uvFor(a);
    const uvB = uvFor(b);
    pushTri(af, bf, ab, side, [uvA, uvB, uvB]);
    pushTri(af, ab, aa, side, [uvA, uvB, uvA]);
  }

  return { points: outline.length, positions, normals, uvs, vertices: positions.length / 3 };
}

/* ------------------------------- GLB ----------------------------- */

function pad4(n) {
  return (4 - (n % 4)) % 4;
}

function alignTo(bufs, byteLength, padByte = 0) {
  const p = pad4(byteLength);
  if (p) bufs.push(new Uint8Array(p).fill(padByte));
  return byteLength + p;
}

/**
 * Serialise a mesh + texture into a valid .glb (glTF 2.0, single BIN chunk).
 * `jpeg` is a Uint8Array of a JPEG image used as the base colour texture.
 */
export function buildGlb(mesh, jpeg, {
  name = 'JARVIS garment',
  baseColor = [0.15, 0.15, 0.14, 1],
  generator = 'JARVIS Studio',
} = {}) {
  const { positions, normals, uvs } = mesh;
  if (!positions?.length || !normals?.length || !uvs?.length) {
    throw new Error('mesh is missing vertex data');
  }

  const posBuf = new Float32Array(positions);
  const nrmBuf = new Float32Array(normals);
  const uvBuf = new Float32Array(uvs);

  // bounds for POSITION accessor (required by spec)
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < positions.length; i += 3) {
    for (let k = 0; k < 3; k++) {
      const v = positions[i + k];
      if (v < min[k]) min[k] = v;
      if (v > max[k]) max[k] = v;
    }
  }

  const chunks = [];
  let offset = 0;
  const views = [];

  const addView = (typed, target) => {
    const bytes = new Uint8Array(typed.buffer, typed.byteOffset, typed.byteLength);
    const view = { buffer: 0, byteOffset: offset, byteLength: typed.byteLength };
    if (target) view.target = target;
    chunks.push(bytes);
    offset = alignTo(chunks, offset + typed.byteLength);
    views.push(view);
    return views.length - 1;
  };

  const posView = addView(posBuf, 34962);
  const nrmView = addView(nrmBuf, 34962);
  const uvView = addView(uvBuf, 34962);

  let imageView = null;
  if (jpeg && jpeg.byteLength) {
    const bytes = jpeg instanceof Uint8Array ? jpeg : new Uint8Array(jpeg);
    imageView = { buffer: 0, byteOffset: offset, byteLength: bytes.byteLength };
    chunks.push(bytes);
    offset = alignTo(chunks, offset + bytes.byteLength);
    views.push(imageView);
    imageView = views.length - 1;
  }

  const count = positions.length / 3;
  const accessors = [
    { bufferView: posView, componentType: 5126, count, type: 'VEC3', min, max },
    { bufferView: nrmView, componentType: 5126, count, type: 'VEC3' },
    { bufferView: uvView, componentType: 5126, count, type: 'VEC2' },
  ];

  const material = {
    name: 'Garment',
    pbrMetallicRoughness: {
      baseColorFactor: baseColor,
      metallicFactor: 0,
      roughnessFactor: 0.92,
    },
    doubleSided: true,
  };
  const primitive = { attributes: { POSITION: 0, NORMAL: 1, TEXCOORD_0: 2 }, material: 0, mode: 4 };

  const json = {
    asset: { version: '2.0', generator },
    scene: 0,
    scenes: [{ name, nodes: [0] }],
    nodes: [{ name, mesh: 0 }],
    meshes: [{ name, primitives: [primitive] }],
    materials: [material],
    accessors,
    bufferViews: views,
    buffers: [{ byteLength: offset }],
  };

  if (imageView !== null) {
    json.textures = [{ sampler: 0, source: 0 }];
    json.samplers = [{ magFilter: 9729, minFilter: 9987, wrapS: 10497, wrapT: 10497 }];
    json.images = [{ bufferView: imageView, mimeType: 'image/jpeg' }];
    material.pbrMetallicRoughness.baseColorTexture = { index: 0, texCoord: 0 };
  }

  // JSON chunk, space-padded per spec
  const jsonText = JSON.stringify(json);
  const jsonBytes = new TextEncoder().encode(jsonText);
  const jsonPad = pad4(jsonBytes.byteLength);
  const jsonChunk = new Uint8Array(jsonBytes.byteLength + jsonPad);
  jsonChunk.set(jsonBytes);
  jsonChunk.fill(0x20, jsonBytes.byteLength);

  const binLength = offset;
  const binPad = pad4(binLength);
  const totalLength = 12 + 8 + jsonChunk.byteLength + 8 + binLength + binPad;

  const out = new Uint8Array(totalLength);
  const dv = new DataView(out.buffer);
  let p = 0;

  // header
  out.set([0x67, 0x6c, 0x54, 0x46], p); p += 4; // 'glTF'
  dv.setUint32(p, 2, true); p += 4;
  dv.setUint32(p, totalLength, true); p += 4;

  // JSON chunk
  dv.setUint32(p, jsonChunk.byteLength, true); p += 4;
  out.set([0x4a, 0x53, 0x4f, 0x4e], p); p += 4; // 'JSON'
  out.set(jsonChunk, p); p += jsonChunk.byteLength;

  // BIN chunk
  dv.setUint32(p, binLength + binPad, true); p += 4;
  out.set([0x42, 0x49, 0x4e, 0x00], p); p += 4; // 'BIN\0'
  for (const chunk of chunks) {
    out.set(chunk, p);
    p += chunk.byteLength;
  }
  // trailing padding stays zero

  return { glb: out, json, bytes: totalLength, vertices: count, triangles: count / 3 };
}

/* --------------------------- validation -------------------------- */

/** Parse a GLB back and assert the container + accessors are consistent. */
export function validateGlb(glb) {
  const dv = new DataView(glb.buffer, glb.byteOffset, glb.byteLength);
  const magic = String.fromCharCode(...glb.slice(0, 4));
  const version = dv.getUint32(4, true);
  const length = dv.getUint32(8, true);
  const problems = [];
  if (magic !== 'glTF') problems.push(`bad magic: ${magic}`);
  if (version !== 2) problems.push(`bad version: ${version}`);
  if (length !== glb.byteLength) problems.push(`length ${length} != ${glb.byteLength}`);

  const jsonLen = dv.getUint32(12, true);
  const jsonType = String.fromCharCode(...glb.slice(16, 20));
  if (jsonType !== 'JSON') problems.push(`chunk 0 type: ${jsonType}`);
  if (jsonLen % 4 !== 0) problems.push(`json chunk not 4-byte aligned: ${jsonLen}`);
  const json = JSON.parse(new TextDecoder().decode(glb.slice(20, 20 + jsonLen)));

  const binHeader = 20 + jsonLen;
  const binLen = dv.getUint32(binHeader, true);
  const binType = String.fromCharCode(...glb.slice(binHeader + 4, binHeader + 8));
  if (binType !== 'BIN\0') problems.push(`chunk 1 type: ${JSON.stringify(binType)}`);
  if ((binLen & 3) !== 0) problems.push(`bin chunk not 4-byte aligned: ${binLen}`);
  if (binHeader + 8 + binLen !== glb.byteLength) problems.push('bin chunk does not reach end of file');

  const declared = json.buffers?.[0]?.byteLength ?? 0;
  for (const [i, v] of (json.bufferViews || []).entries()) {
    if (v.byteOffset + v.byteLength > declared) problems.push(`bufferView ${i} overruns buffer`);
  }
  for (const [i, a] of (json.accessors || []).entries()) {
    const v = json.bufferViews[a.bufferView];
    if (!v) { problems.push(`accessor ${i} has no bufferView`); continue; }
    const comps = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[a.type] || 1;
    const size = a.componentType === 5126 ? 4 : 2;
    if (a.byteOffset || v.byteOffset % 4 === 0) {
      if (a.count * comps * size > v.byteLength) problems.push(`accessor ${i} overruns its view`);
    }
  }
  const prim = json.meshes?.[0]?.primitives?.[0];
  if (!prim) problems.push('no primitive');
  if (prim && json.accessors?.[prim.attributes.POSITION]?.count === 0) problems.push('empty POSITION accessor');

  return { ok: problems.length === 0, problems, json, triangles: (json.accessors?.[0]?.count || 0) / 3 };
}

/* ------------------------------ PDF ------------------------------ */

/** Read the component count out of a JPEG's SOF marker. */
export function jpegComponents(bytes) {
  for (let i = 2; i < bytes.length - 9; i++) {
    if (bytes[i] !== 0xff) continue;
    const marker = bytes[i + 1];
    const isSof = marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;
    if (isSof) return bytes[i + 9];
    const len = (bytes[i + 2] << 8) | bytes[i + 3];
    if (len > 0) i += len + 1;
  }
  return 3;
}

/**
 * Minimal single-page PDF wrapping a JPEG image (DCTDecode — no re-encoding).
 * Page is A4 at 72 dpi if `a4`, otherwise sized to the image.
 */
export function buildPdf(jpeg, { width, height, a4 = true, title = 'JARVIS' } = {}) {
  const bytes = jpeg instanceof Uint8Array ? jpeg : new Uint8Array(jpeg);
  const comps = jpegComponents(bytes);
  const aspect = width / height;
  let pw = width;
  let ph = height;
  if (a4) {
    const A4 = [595.28, 841.89];
    if (aspect >= A4[0] / A4[1]) { pw = A4[0]; ph = A4[0] / aspect; } else { ph = A4[1]; pw = A4[1] * aspect; }
  }

  const enc = (s) => new TextEncoder().encode(s);
  const parts = [];
  let length = 0;
  const push = (data) => {
    const b = typeof data === 'string' ? enc(data) : data;
    parts.push(b);
    length += b.byteLength;
  };
  const offsets = {};
  const startObj = (n) => { offsets[n] = length; push(`${n} 0 obj\n`); };

  push('%PDF-1.4\n%\u00e2\u00e3\u00cf\u00d3\n');

  startObj(1);
  push('<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');

  startObj(2);
  push('<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n');

  startObj(3);
  push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pw.toFixed(2)} ${ph.toFixed(2)}] ` +
    `/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>\nendobj\n`);

  const content = `q\n${pw.toFixed(2)} 0 0 ${ph.toFixed(2)} 0 0 cm\n/Im0 Do\nQ\n`;
  startObj(4);
  push(`<< /Length ${content.length} >>\nstream\n${content}endstream\nendobj\n`);

  startObj(5);
  push(`<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} ` +
    `/ColorSpace ${comps === 1 ? '/DeviceGray' : '/DeviceRGB'} /BitsPerComponent 8 ` +
    `/Filter /DCTDecode /Length ${bytes.byteLength} >>\nstream\n`);
  push(bytes);
  push('\nendstream\nendobj\n');

  startObj(6);
  push(`<< /Title (${title.replace(/[()\\]/g, '')}) /Producer (JARVIS Studio) >>\nendobj\n`);

  const xrefStart = length;
  const total = 7;
  let xref = `xref\n0 ${total}\n0000000000 65535 f \n`;
  for (let i = 1; i < total; i++) {
    xref += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  push(xref);
  push(`trailer\n<< /Size ${total} /Root 1 0 R /Info 6 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`);

  const out = new Uint8Array(length);
  let p = 0;
  for (const part of parts) { out.set(part, p); p += part.byteLength; }
  return out;
}

/** Structural check used by tests. */
export function validatePdf(pdf) {
  const text = new TextDecoder('latin1').decode(pdf);
  const problems = [];
  if (!text.startsWith('%PDF-1.')) problems.push('missing %PDF header');
  if (!text.trimEnd().endsWith('%%EOF')) problems.push('missing %%EOF');
  const startxref = Number(text.match(/startxref\n(\d+)/)?.[1]);
  if (!Number.isFinite(startxref)) problems.push('missing startxref');
  else {
    const at = text.slice(startxref, startxref + 4);
    if (at !== 'xref') problems.push(`startxref does not point at xref (found ${JSON.stringify(at)})`);
  }
  for (const m of text.matchAll(/(\d+) 0 obj/g)) {
    if (!new RegExp(`${m[1]} 0 obj[\\s\\S]*?endobj`).test(text)) problems.push(`object ${m[1]} unterminated`);
  }
  const declared = Number(text.match(/\/Length (\d+) >>\nstream\n/)?.[1]);
  if (!Number.isFinite(declared)) problems.push('image stream has no /Length');
  if (!/\/DCTDecode/.test(text)) problems.push('image is not DCTDecode');
  return { ok: problems.length === 0, problems, pages: (text.match(/\/Type \/Page[^s]/g) || []).length };
}
