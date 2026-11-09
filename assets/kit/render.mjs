// Render completo: varios Chrome capturan tramos en paralelo y cada uno alimenta su propio ffmpeg.
//   node render.mjs [--workers 6] [--from 0] [--to DUR] [--poster 10.2] [--out frames/video_silent.mp4]
// --poster T pone el fotograma del segundo T (sin subtítulos) como fotograma 0: es la miniatura
// que muestran TikTok/YouTube. Sustituye al fotograma 0, no añade ninguno: el audio no se desplaza.
// Para rehacer solo un tramo, renderízalo con --from/--to a otro --out y vuelve a unir con finish.py.
import puppeteer from 'puppeteer-core';
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { findChrome, LAUNCH_ARGS } from './chrome.mjs';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const TL = JSON.parse(fs.readFileSync('timeline.json', 'utf8'));
const FPS = TL.fps;
const WORKERS = +arg('workers', Math.max(2, Math.min(6, Math.floor(os.cpus().length / 2))));
const F0 = Math.round(+arg('from', 0) * FPS), F1 = Math.round(+arg('to', TL.duration) * FPS);
const POSTER = arg('poster', null);
const OUT = arg('out', 'frames/video_silent.mp4');
const PAGE = arg('page', 'video.html');
const total = F1 - F0, per = Math.ceil(total / WORKERS);
const CHROME = findChrome();
fs.mkdirSync(path.dirname(OUT), { recursive: true });

// NVENC si hay GPU NVIDIA que lo acepte; si no, x264 por CPU (más lento, misma calidad).
const nvenc = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=s=256x256:d=0.1', '-c:v', 'h264_nvenc', '-f', 'null', '-']).status === 0;
const ENC = nvenc
  ? ['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', '0', '-maxrate', '20M', '-bufsize', '40M']
  : ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14'];
console.log(`${total} fotogramas · ${WORKERS} trabajadores · ${nvenc ? 'NVENC' : 'x264'}`);

let done = 0;
const t0 = Date.now();
const timer = setInterval(() => {
  const el = (Date.now() - t0) / 1000;
  console.log(`  ${done}/${total} · ${(done / el).toFixed(1)} fps · faltan ~${Math.round((total - done) / Math.max(done / el, 0.01))}s`);
}, 15000);

// Un navegador por trabajador: varias pestañas en un mismo Chrome se bloquean al capturar en segundo plano.
async function worker(w) {
  const a = F0 + w * per, b = Math.min(F1, a + per);
  if (a >= b) return null;
  const seg = path.join(path.dirname(OUT), `${path.basename(OUT, '.mp4')}_seg${String(w).padStart(2, '0')}.mp4`);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-', '-vf', 'format=yuv420p', ...ENC,
    '-g', String(FPS), '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  let browser, page;
  for (let attempt = 1; ; attempt++) {           // arrancar varios Chrome a la vez falla de vez en cuando: se reintenta
    try {
      browser = await puppeteer.launch({ executablePath: CHROME, headless: true, protocolTimeout: 0, args: LAUNCH_ARGS });
      page = await browser.newPage();
      page.on('pageerror', e => console.log('ERROR EN LA PÁGINA:', e.message));
      await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
      await page.goto(pathToFileURL(path.resolve(PAGE)).href);
      await page.evaluate(() => window.READY);
      break;
    } catch (e) {
      if (browser) await browser.close().catch(() => {});
      if (attempt >= 3) throw e;
      await new Promise(r => setTimeout(r, 1500 * attempt));
    }
  }
  for (let f = a; f < b; f++) {
    const isPoster = f === 0 && POSTER != null;
    await page.evaluate((tt, pp) => window.seek(tt, pp), isPoster ? +POSTER : f / FPS, isPoster);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95, optimizeForSpeed: true });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    done++;
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg terminó con código ' + c))));
  await browser.close();
  return seg;
}

const segs = (await Promise.all(Array.from({ length: WORKERS }, (_, w) => worker(w)))).filter(Boolean);
clearInterval(timer);
const list = OUT.replace(/\.mp4$/, '_list.txt');
fs.writeFileSync(list, segs.map(s => `file '${path.resolve(s).replace(/\\/g, '/')}'`).join('\n'));
const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', OUT], { stdio: 'inherit' });
console.log(`listo: ${OUT} · ${total} fotogramas en ${((Date.now() - t0) / 1000).toFixed(0)}s${r.status ? ' (falló la unión)' : ''}`);
process.exit(r.status || 0);
