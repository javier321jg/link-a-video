// Fotogramas sueltos para revisar el diseño antes de renderizar todo.
//   node still.mjs 1.5 3.2 8.9            -> stills/t_001.50.jpg ...
//   node still.mjs 1.5 3.2 8.9 --sheet a  -> además stills/sheet_a.jpg (hoja de contacto, 6 por fila)
//   --page otra.html                      -> otra página en vez de video.html
import puppeteer from 'puppeteer-core';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { findChrome, LAUNCH_ARGS } from './chrome.mjs';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const sheetName = opt('sheet', null), pageFile = opt('page', 'video.html');
const times = args.map(Number).filter(n => !Number.isNaN(n));
fs.mkdirSync('stills', { recursive: true });

const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: LAUNCH_ARGS });
const page = await browser.newPage();
page.on('pageerror', e => console.log('ERROR EN LA PÁGINA:', e.message));
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.resolve(pageFile)).href);
const info = await page.evaluate(() => window.READY);
console.log('listo', info);
const files = [];
for (const t of times) {
  await page.evaluate((tt) => window.seek(tt), t);
  const f = `stills/t_${t.toFixed(2).padStart(6, '0')}.jpg`;
  await page.screenshot({ path: f, type: 'jpeg', quality: 88 });
  files.push(f);
}
await browser.close();
if (sheetName && files.length) {
  const cols = Math.min(6, files.length);
  const layout = files.map((_, i) => `${(i % cols) * 360}_${Math.floor(i / cols) * 640}`).join('|');
  const graph = files.map((_, i) => `[${i}]scale=360:640[s${i}]`).join(';') + ';' + files.map((_, i) => `[s${i}]`).join('') +
    (files.length > 1 ? `xstack=inputs=${files.length}:layout=${layout}:fill=black` : 'null');
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...files.flatMap(f => ['-i', f]), '-filter_complex', graph, '-q:v', '3', `stills/sheet_${sheetName}.jpg`], { stdio: 'inherit' });
  console.log('hoja', `stills/sheet_${sheetName}.jpg`, r.status === 0 ? 'ok' : 'falló');
}
