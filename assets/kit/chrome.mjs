// Localiza un Chrome/Chromium para puppeteer-core (no descarga nada).
// Orden: variable CHROME_PATH, caché de puppeteer, Chrome/Edge instalados.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

export function findChrome() {
  const c = [];
  if (process.env.CHROME_PATH) c.push(process.env.CHROME_PATH);
  const cache = path.join(os.homedir(), '.cache', 'puppeteer', 'chrome');
  if (fs.existsSync(cache)) {
    for (const v of fs.readdirSync(cache).sort().reverse()) {
      c.push(path.join(cache, v, 'chrome-win64', 'chrome.exe'), path.join(cache, v, 'chrome-linux64', 'chrome'),
        path.join(cache, v, 'chrome-mac-arm64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing'),
        path.join(cache, v, 'chrome-mac-x64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing'));
    }
  }
  c.push('C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser');
  const hit = c.find(p => p && fs.existsSync(p));
  if (!hit) throw new Error('No encontré Chrome. Instala Chrome o define CHROME_PATH con la ruta del ejecutable.');
  return hit;
}

export const LAUNCH_ARGS = ['--allow-file-access-from-files', '--force-color-profile=srgb', '--hide-scrollbars'];
