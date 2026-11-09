# Efectos de sonido sintetizados (sin descargar nada), afinados a la tonalidad de la música
# y colocados con las mismas anclas de palabra que usa la animación. Salida: audio/sfx.wav
#   python sfx.py            lee sfx_events.json
#
# sfx_events.json:
#   { "key": "Dm",                         tonalidad (Dm por defecto; pídele la misma a la música)
#     "cuts": ["twins.start", "feats:disene-0.22"],     un whoosh en cada corte de escena
#     "events": [ {"at": "hook:lo:1-0.02", "sfx": "thump", "note": "D2", "gain": 0.5}, ... ] }
#
# "at" acepta: segundos (12.5) · "escena.start+0.1" / "escena.end-0.2" · "escena:palabra[:n][±seg]"
#   (n = cuántas veces ha salido ya esa palabra en la escena, empezando en 0).
# sfx: whoosh(dur,peak) · impact · thump(note,decay) · tick(note,decay) · chime(notes,decay) · riser(dur)
#      ticks(count,span,note)  ráfaga que se va frenando, para contadores
#      sparkle(count,span)     destellos aleatorios de la escala, para enjambres o listas
# Mantén las ganancias bajas (0.05-0.15 los pequeños, 0.4-0.7 los golpes): los efectos van bajo la música.
import json, os, re, subprocess, sys, unicodedata
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
SR = 48000
tl = json.load(open("timeline.json", encoding="utf-8"))
S = {s["scene"]: s for s in tl["scenes"]}
cfg = json.load(open("sfx_events.json", encoding="utf-8"))
rng = np.random.default_rng(52)
bus = np.zeros((int((tl["duration"] + 3) * SR), 2), dtype=np.float64)

SEMI = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def hz(note):
    """'D5' / 'F#4' / 'Bb2' -> Hz"""
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", note)
    semi = SEMI[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)] + 12 * (int(m.group(3)) - 4)
    return 440.0 * 2 ** (semi / 12)


KEY = cfg.get("key", "Dm")
ROOT = re.match(r"[A-G][#b]?", KEY).group(0)
MINOR = KEY.endswith("m")
STEPS = [0, 3, 7, 10, 12, 15, 19] if MINOR else [0, 4, 7, 9, 12, 16, 19]     # arpegio de la tonalidad
SCALE = [hz(ROOT + "5") * 2 ** (s / 12) for s in STEPS]


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\.$", "", re.sub(r"[^a-z0-9$%.×]", "", s))


def when(at):
    if isinstance(at, (int, float)):
        return float(at)
    m = re.fullmatch(r"(\w+)\.(start|end)([+-]\d*\.?\d+)?", at)
    if m:
        return S[m.group(1)][m.group(2)] + float(m.group(3) or 0)
    m = re.fullmatch(r"(\w+):([^:+]+?)(?::(\d+))?([+-]\d*\.?\d+)?", at)
    if not m:
        sys.exit(f"'at' no válido: {at}")
    k = norm(m.group(2))
    ws = [w for w in S[m.group(1)]["words"] if norm(w["w"]) == k] or [w for w in S[m.group(1)]["words"] if norm(w["w"]).startswith(k)]
    try:
        return ws[int(m.group(3) or 0)]["t0"] + float(m.group(4) or 0)
    except IndexError:
        sys.exit(f"palabra no encontrada: {at}")


def put(x, t, gain=1.0, pan=0.0):
    i = int(max(0, t) * SR); n = min(len(x), len(bus) - i)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    bus[i:i + n, 0] += x[:n] * gain * l * 1.414
    bus[i:i + n, 1] += x[:n] * gain * r * 1.414


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d)


def band_noise(n, lo, hi):
    spec = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
    mask = np.exp(-0.5 * ((np.log(np.maximum(f, 1)) - np.log(np.sqrt(lo * hi))) / (np.log(hi / lo) / 2.2)) ** 2)
    y = np.fft.irfft(spec * mask, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def tick(f, d=0.05):
    n = int(SR * 0.25); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(n, 0.003, d)


def chime(freqs, d=0.9):
    n = int(SR * 3.0); t = np.arange(n) / SR; y = np.zeros(n)
    for j, f in enumerate(freqs):
        y += (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.2)
              + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / 0.1)) * env(n, 0.004, d) * (0.85 ** j)
    return y / len(freqs) ** 0.6


def thump(f, d=0.22):
    n = int(SR * 0.9); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 1.4 * np.exp(-t / 0.035))) / SR
    return np.sin(ph) * env(n, 0.002, d) + 0.2 * band_noise(n, 800, 4000) * env(n, 0.001, 0.02)


def impact():
    n = int(SR * 2.4); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(hz(ROOT + "1") * (1 + 2.2 * np.exp(-t / 0.08))) / SR
    return np.tanh(1.6 * np.sin(ph)) * env(n, 0.003, 0.7) + band_noise(n, 300, 5000) * env(n, 0.002, 0.28) * 0.35


def whoosh(dur=0.62, peak=0.45):
    n = int(SR * dur); t = np.arange(n) / SR
    lo, hi = band_noise(n, 250, 1100), band_noise(n, 1400, 7000)
    k = np.clip(t / (dur * peak), 0, 1)
    a = np.where(t < dur * peak, k ** 2.2, np.exp(-(t - dur * peak) / (dur * 0.22)))
    return (lo * (1 - 0.7 * k) + hi * (0.25 + 0.75 * k)) * a


def riser(dur=1.0):
    n = int(SR * dur); t = np.arange(n) / SR; k = t / dur
    tone = np.sin(2 * np.pi * np.cumsum(hz(ROOT + "3") * 2 ** (k * 2)) / SR) * 0.35
    return (band_noise(n, 1500, 9000) * 0.8 + tone) * k ** 2.5 * np.minimum(1, (dur - t) / 0.012)


for i, c in enumerate(cfg.get("cuts", [])):
    put(whoosh(), when(c) - 0.30, cfg.get("cut_gain", 0.20), pan=(-0.35 if i % 2 else 0.35))

for e in cfg.get("events", []):
    t, kind, g, pan = when(e["at"]), e["sfx"], e.get("gain"), e.get("pan", 0.0)
    if kind == "whoosh":
        put(whoosh(e.get("dur", 0.62), e.get("peak", 0.45)), t, g or 0.15, pan)
    elif kind == "impact":
        put(impact(), t, g or 0.6, pan)
    elif kind == "thump":
        put(thump(hz(e.get("note", ROOT + "2")), e.get("decay", 0.25)), t, g or 0.4, pan)
    elif kind == "tick":
        put(tick(hz(e.get("note", ROOT + "5")), e.get("decay", 0.05)), t, g or 0.08, pan)
    elif kind == "chime":
        put(chime([hz(n) for n in e.get("notes", [ROOT + "5"])], e.get("decay", 0.9)), t, g or 0.09, pan)
    elif kind == "riser":
        put(riser(e.get("dur", 1.0)), t, g or 0.15, pan)
    elif kind == "ticks":
        n, span, f = e.get("count", 12), e.get("span", 0.85), hz(e.get("note", ROOT + "5"))
        for i in range(n):
            put(tick(f * (1 + i * 0.012), 0.02), t + span * (1 - (1 - i / n) ** 2.2), g or 0.05, pan)
    elif kind == "sparkle":
        for i in range(e.get("count", 40)):
            put(tick(SCALE[int(rng.integers(len(SCALE)))], 0.03), t + rng.random() * e.get("span", 1.3), g or 0.022, rng.uniform(-0.8, 0.8))
    else:
        sys.exit(f"sfx desconocido: {kind}")

peak = float(np.max(np.abs(bus)))
bus = bus / max(peak, 1e-9) * 0.7
os.makedirs("audio", exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", "audio/sfx.wav"],
               input=(np.clip(bus, -1, 1) * 32767).astype(np.int16).tobytes(), check=True)
print(f"audio/sfx.wav · {len(cfg.get('cuts', []))} cortes + {len(cfg.get('events', []))} eventos (pico previo {peak:.2f})")
