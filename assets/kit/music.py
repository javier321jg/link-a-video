# Música original con ElevenLabs Music, con secciones alineadas a las escenas del video.
#   python music.py [salida.mp3]        (por defecto audio/music.mp3)
#
# music.json:
#   { "global_positive": ["instrumental", "cinematic electronic", "D minor", "100 BPM", ...],
#     "global_negative": ["vocals", "lyrics", ...],
#     "sections": [ {"name": "Hook", "from": 0, "positive": ["near silence", ...], "negative": ["drums"]},
#                   {"name": "Reveal", "from": "intro.start", ...},
#                   {"name": "Finale", "from": "end:sigueme-0.25", "positive": ["sustained chord", "rings out until the very end"]} ] }
# "from" acepta segundos, "escena.start" o "escena:palabra±seg" (igual que sfx_events.json).
# Cada sección dura hasta que empieza la siguiente; la última, hasta el final del video (mínimo 3 s por sección).
#
# Al terminar imprime el nivel de cada sección: revísalo. Si pides "fade out" en una sección larga, el modelo
# apaga la música demasiado pronto y el cierre queda en silencio; pide que el final "se sostenga hasta el último segundo".
import json, os, re, subprocess, sys, time, unicodedata, urllib.request, urllib.error
from kit_env import load_env, need

sys.stdout.reconfigure(encoding="utf-8")
KEY = need(load_env(), "ELEVENLABS_API_KEY", "Ponla en .env o en ~/.link-a-video.env")
tl = json.load(open("timeline.json", encoding="utf-8"))
cfg = json.load(open("music.json", encoding="utf-8"))
S = {s["scene"]: s for s in tl["scenes"]}
out = sys.argv[1] if len(sys.argv) > 1 else "audio/music.mp3"


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
    k = norm(m.group(2))
    ws = [w for w in S[m.group(1)]["words"] if norm(w["w"]) == k] or [w for w in S[m.group(1)]["words"] if norm(w["w"]).startswith(k)]
    return ws[int(m.group(3) or 0)]["t0"] + float(m.group(4) or 0)


starts = [when(s["from"]) for s in cfg["sections"]] + [tl["duration"]]
durs = [int(round((starts[i + 1] - starts[i]) * 1000)) for i in range(len(cfg["sections"]))]
for i in range(len(durs)):          # la API exige 3 s por sección: si una es más corta, le toma el resto a la siguiente
    if durs[i] < 3000 and i + 1 < len(durs):
        durs[i + 1] -= 3000 - durs[i]; durs[i] = 3000
durs = [max(3000, d) for d in durs]
sections = [{"section_name": s["name"], "positive_local_styles": s.get("positive", []), "negative_local_styles": s.get("negative", []),
             "duration_ms": durs[i], "lines": []} for i, s in enumerate(cfg["sections"])]
starts = [sum(durs[:i]) / 1000 for i in range(len(durs))] + [sum(durs) / 1000]
plan = {"positive_global_styles": cfg.get("global_positive", ["instrumental"]), "negative_global_styles": cfg.get("global_negative", ["vocals", "lyrics"]), "sections": sections}
print("secciones:", [(s["section_name"], s["duration_ms"]) for s in sections], "· total", sum(s["duration_ms"] for s in sections), "ms")
req = urllib.request.Request("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128",
                             data=json.dumps({"composition_plan": plan, "model_id": "music_v1", "respect_sections_durations": True}).encode("utf-8"),
                             headers={"xi-api-key": KEY, "Content-Type": "application/json"})
data = None
for attempt in range(4):            # "system_busy" (429) es pasajero: se reintenta con espera
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
        break
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:800]
        if e.code in (429, 500, 502, 503) and attempt < 3:
            print(f"  ElevenLabs ocupado ({e.code}); reintento en {15 * (attempt + 1)}s"); time.sleep(15 * (attempt + 1))
        else:
            sys.exit(f"ElevenLabs Music HTTP {e.code}: {msg}")
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
open(out, "wb").write(data)
print(f"{out} · {len(data) // 1024} KB")


def rms(a, b):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(a), "-to", str(b), "-i", out, "-af",
                          "astats=measure_overall=RMS_level:measure_perchannel=none", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.findall(r"RMS level dB: (-?[\d.]+|-inf)", err)
    return float(m[0]) if m and m[0] != "-inf" else -99.0


levels = [rms(starts[i], starts[i + 1]) for i in range(len(sections))]
for s, lv in zip(sections, levels):
    print(f"  {s['section_name']:12s} {lv:6.1f} dB RMS")
end_lv, body = rms(max(0, tl["duration"] - 5), max(1, tl["duration"] - 1.5)), sorted(levels)[len(levels) // 2]
if end_lv < body - 22:
    print(f"AVISO: la música casi desaparece antes del final ({end_lv:.0f} dB frente a {body:.0f} dB). Regenera pidiendo que la última sección se sostenga.")
