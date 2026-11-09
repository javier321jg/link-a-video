/* link-a-video · motor de animación determinista.
   Cada fotograma es una función pura del tiempo: window.seek(t) deja la página exactamente
   como debe verse en el segundo t, sin depender de relojes ni de fotogramas anteriores.
   La página define window.build(VE) con sus escenas; el motor pone subtítulos, cortinas, grano y captura.
   Requiere: gsap (global) y timeline.js (window.TL, generado por assemble_vo.py). */
(function () {
  "use strict";
  const TL = window.TL, FPS = TL.fps, DUR = TL.duration;
  const S = Object.fromEntries(TL.scenes.map(s => [s.scene, s]));
  const $ = (q) => document.querySelector(q);
  const stage = $("#stage");
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const easeOut = (k) => 1 - Math.pow(1 - k, 3);
  const hash = (i) => { const x = Math.sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9$%.×]/g, "").replace(/\.$/, "");

  /* Segundo en que se pronuncia una palabra: wt("precio", "$8"), wt("hook", "lo", 1) = segunda vez.
     Sincronizar con palabras (y no con segundos fijos) mantiene todo alineado si se regenera la voz. */
  function wt(scene, word, nth = 0) {
    const k = norm(word);
    let m = S[scene].words.filter(w => norm(w.w) === k);
    if (!m.length) m = S[scene].words.filter(w => norm(w.w).startsWith(k));
    if (!m[nth]) throw new Error("palabra no encontrada: " + scene + " / " + word + " #" + nth);
    return m[nth].t0;
  }

  /* ---------- registros puros ---------- */
  const counters = [], shows = [], frameFns = [];
  function counter(sel, t0, t1, from, to, dec = 0) { counters.push({ el: typeof sel === "string" ? $(sel) : sel, t0, t1, from, to, dec }); }
  function showAt(el, t0, t1 = Infinity) { el = typeof el === "string" ? $(el) : el; el.style.visibility = "hidden"; shows.push({ el, t0, t1 }); }
  function onFrame(fn) { frameFns.push(fn); }

  /* ---------- línea de tiempo (GSAP en pausa; solo se hace seek) ----------
     Regla: cada elemento recibe como mucho una entrada (IN) y una salida (OUT). Varias animaciones
     de la misma propiedad sobre el mismo elemento dan estados erróneos al saltar en el tiempo. */
  gsap.ticker.lagSmoothing(0);
  const tl = gsap.timeline({ paused: true });
  function show(sel, a, b) { tl.set(sel, { autoAlpha: 1 }, a); if (b != null) tl.set(sel, { autoAlpha: 0 }, b); }
  function IN(sel, t, from = {}, dur = 0.6, ease = "expo.out") {
    const to = { autoAlpha: 1, duration: dur, ease };
    for (const k in from) to[k] = (k === "scale" || k === "scaleX" || k === "scaleY") ? 1 : 0;
    return tl.fromTo(sel, { autoAlpha: 0, ...from }, to, t);
  }
  function OUT(sel, t, to = {}, dur = 0.3, ease = "power2.in") { return tl.to(sel, { autoAlpha: 0, ...to, duration: dur, ease }, t); }
  /* Ken Burns: zoom lento de un fondo durante su escena */
  function kb(sel, a, b, s0, s1, ease = "none") { tl.fromTo(sel, { scale: s0 }, { scale: s1, duration: b - a + 0.6, ease }, a - 0.3); }
  /* Cortina: tapa la pantalla justo en el corte, así el cambio de escena ocurre oculto (sin fundidos turbios) */
  function wipe(c, dir = "v") {
    const el = document.createElement("div");
    el.className = "wipe " + dir;
    stage.appendChild(el);
    const p = dir === "h" ? "xPercent" : "yPercent";
    tl.fromTo(el, { [p]: 101 }, { [p]: 0, duration: 0.22, ease: "power3.in" }, c - 0.22).to(el, { [p]: -101, duration: 0.34, ease: "power3.out" }, c + 0.02);
  }
  /* Barras de un gráfico: [[selectorBarra, selectorValor, valor], ...] */
  function bars(list, t, gap = 0.16) {
    list.forEach(([bar, val, v], i) => {
      const t0 = t + i * gap;
      IN(bar, t0, { x: -30 }, 0.4);
      tl.fromTo(bar + " .bt", { scaleX: 0 }, { scaleX: 1, duration: 0.75, ease: "power3.out" }, t0 + 0.05);
      counter(val, t0 + 0.05, t0 + 0.8, 0, v, Number.isInteger(v) ? 0 : 1);
    });
  }
  /* Visibilidad de escenas por corte duro: sceneCuts(["hook","intro",...]) usa #sc-<nombre> */
  function sceneCuts(names) {
    names.forEach((n, i) => {
      const el = "#sc-" + n;
      if (i === 0) { gsap.set(el, { autoAlpha: 1 }); tl.set(el, { autoAlpha: 0 }, S[n].end); }
      else show(el, S[n].start, i === names.length - 1 ? null : S[n].end);
    });
  }

  /* ---------- subtítulos palabra por palabra ---------- */
  const chunks = [];
  let cap = null, capIdx = -2;
  const capCfg = { skip: [], maxWords: 3, maxChars: 17 };
  function buildCaptions() {
    cap = document.createElement("div"); cap.id = "cap"; stage.appendChild(cap);
    const all = [];
    TL.scenes.forEach(s => { if (capCfg.skip.includes(s.scene)) return; s.words.forEach(w => all.push({ ...w, scene: s.scene })); });
    let cur = [];
    const flush = () => { if (cur.length) { chunks.push({ words: cur, t0: cur[0].t0, t1: cur[cur.length - 1].t1 }); cur = []; } };
    all.forEach((w) => {
      const len = cur.reduce((n, x) => n + x.w.length + 1, 0);
      if (cur.length && (cur[0].scene !== w.scene || cur.length >= capCfg.maxWords || len + w.w.length > capCfg.maxChars)) flush();
      cur.push(w);
      if (/[.,:?!]$/.test(w.w)) flush();
    });
    flush();
    chunks.forEach((c, i) => { const nx = chunks[i + 1]; c.end = Math.min(c.t1 + 0.4, nx ? nx.t0 - 0.03 : c.t1 + 0.4); c.start = c.t0 - 0.05; });
  }
  function drawCaptions(t) {
    let idx = -1;
    for (let i = 0; i < chunks.length; i++) if (t >= chunks[i].start && t < chunks[i].end) { idx = i; break; }
    if (idx !== capIdx) {
      capIdx = idx;
      cap.innerHTML = idx < 0 ? "" : chunks[idx].words.map(w => `<span class="cw">${w.w.replace(/[.,:]+$/, "")}</span>`).join(" ");
    }
    if (idx < 0) return;
    const c = chunks[idx];
    cap.style.transform = `scale(${0.9 + 0.1 * easeOut(clamp((t - c.start) / 0.14))})`;
    cap.style.opacity = clamp((t - c.start) / 0.06);
    c.words.forEach((w, i) => {
      const nextT0 = c.words[i + 1] ? c.words[i + 1].t0 : Infinity;
      const st = t < w.t0 - 0.02 ? "fut" : (t < Math.min(w.t1 + 0.12, nextT0 - 0.02) ? "now" : "");
      const cls = "cw" + (st ? " " + st : "");
      if (cap.children[i].className !== cls) cap.children[i].className = cls;
    });
  }

  /* ---------- grano de película y viñeta ---------- */
  let grain = null;
  function makeOverlays() {
    const vig = document.createElement("div"); vig.id = "vig"; stage.appendChild(vig);
    grain = document.createElement("div"); grain.id = "grain"; stage.appendChild(grain);
    const c = document.createElement("canvas"); c.width = c.height = 256;
    const g = c.getContext("2d"), im = g.createImageData(256, 256);
    let seed = 520;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    for (let i = 0; i < im.data.length; i += 4) { const v = (rnd() * 255) | 0; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    g.putImageData(im, 0, 0);
    grain.style.backgroundImage = `url(${c.toDataURL()})`;
  }

  /* ---------- fotograma ---------- */
  function perFrame(t) {
    for (const c of counters) {
      const v = c.from + (c.to - c.from) * easeOut(clamp((t - c.t0) / (c.t1 - c.t0)));
      const txt = c.dec ? v.toFixed(c.dec) : Math.round(v).toLocaleString("en-US");
      if (c.el.textContent !== txt) c.el.textContent = txt;
    }
    for (const s of shows) { const vis = (t >= s.t0 && t < s.t1) ? "visible" : "hidden"; if (s.el.style.visibility !== vis) s.el.style.visibility = vis; }
    for (const fn of frameFns) fn(t);
    drawCaptions(t);
    const f = Math.round(t * FPS);
    grain.style.backgroundPosition = `${(f * 73) % 256}px ${(f * 151) % 256}px`;
  }
  /* poster=true oculta los subtítulos (para la portada) */
  window.seek = (t, poster = false) => {
    t = clamp(t, 0, DUR - 0.001);
    tl.time(t + 0.0001, false); perFrame(t);
    cap.style.visibility = poster ? "hidden" : "visible";
    return true;
  };

  const VE = window.VE = { TL, S, FPS, DUR, $, clamp, easeOut, hash, norm, wt, tl, show, IN, OUT, kb, wipe, bars, counter, showAt, onFrame, sceneCuts, captions: capCfg };

  /* READY se resuelve cuando fuentes e imágenes están cargadas y la línea de tiempo construida:
     capturar antes da fotogramas con fuentes de reemplazo o fondos vacíos. */
  window.READY = new Promise((resolve, reject) => {
    window.addEventListener("load", async () => {
      try {
        await Promise.all([...document.fonts].map(f => f.load().catch(() => {})));
        await document.fonts.ready;
        await Promise.all([...document.images].map(im => im.decode().catch(() => {})));
        if (typeof window.build !== "function") throw new Error("la página debe definir window.build(VE)");
        await window.build(VE);
        makeOverlays(); buildCaptions();
        tl.to({}, { duration: 0.01 }, DUR);
        window.seek(0);
        resolve({ duration: DUR, fps: FPS });
      } catch (e) { reject(e); }
    });
  });
})();
