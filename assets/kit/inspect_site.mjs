// Carga una página como la ve un visitante y guarda su texto, identidad visual y capturas verticales.
//   node inspect_site.mjs https://ejemplo.com/articulo
// Salida: site/page.txt (texto completo, la fuente de verdad para verificar cifras),
//         site/identity.json (colores, fuentes, metadatos) y site/shot_NN.jpg.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import { findChrome } from './chrome.mjs';

const URL = process.argv[2];
if (!URL) { console.error('uso: node inspect_site.mjs <url>'); process.exit(1); }
fs.mkdirSync('site', { recursive: true });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
const resp = await page.goto(URL, { waitUntil: 'networkidle2', timeout: 90000 });
console.log('estado HTTP', resp.status());

// recorrer la página por tramos para que cargue el contenido perezoso
const total = await page.evaluate(() => document.documentElement.scrollHeight);
for (let y = 0; y < total; y += 1400) { await page.evaluate((yy) => window.scrollTo(0, yy), y); await sleep(250); }
await page.evaluate(() => window.scrollTo(0, 0));
await sleep(500);

const info = await page.evaluate(() => {
  const pick = (sel) => { const el = document.querySelector(sel); if (!el) return null; const s = getComputedStyle(el); return { sel, color: s.color, bg: s.backgroundColor, font: s.fontFamily, size: s.fontSize, weight: s.fontWeight }; };
  const vars = {};
  for (const sheet of document.styleSheets) { try { for (const rule of sheet.cssRules) { if (rule.selectorText === ':root' || rule.selectorText === 'html') { for (const p of rule.style) if (p.startsWith('--')) vars[p] = rule.style.getPropertyValue(p).trim(); } } } catch (e) {} }
  const fonts = [...new Set([...document.fonts].map(f => `${f.family} ${f.weight} ${f.style}`))];
  const imgs = [...document.images].map(i => ({ src: i.currentSrc || i.src, w: i.naturalWidth, h: i.naturalHeight, alt: i.alt })).filter(i => i.w > 200);
  const metas = Object.fromEntries([...document.querySelectorAll('meta[property],meta[name]')].map(m => [m.getAttribute('property') || m.getAttribute('name'), m.content]));
  return { title: document.title, metas, styles: ['body', 'h1', 'h2', 'p', 'a', 'button', 'table'].map(pick).filter(Boolean), vars, fonts, imgs, height: document.documentElement.scrollHeight, text: document.body.innerText };
});
fs.writeFileSync('site/page.txt', info.text);
const { text, ...rest } = info;
fs.writeFileSync('site/identity.json', JSON.stringify(rest, null, 2));
console.log(`título: ${info.title} | alto: ${info.height}px | texto: ${info.text.length} caracteres | imágenes: ${info.imgs.length}`);

const shots = Math.min(8, Math.ceil(info.height / 1920));
for (let i = 0; i < shots; i++) {
  await page.evaluate((yy) => window.scrollTo(0, yy), i * 1920);
  await sleep(500);
  await page.screenshot({ path: `site/shot_${String(i).padStart(2, '0')}.jpg`, type: 'jpeg', quality: 80 });
}
await browser.close();
