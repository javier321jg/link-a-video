# Une los segmentos de voz en una pista, recorta silencios largos y escribe timeline.json / timeline.js:
# el reloj único del que salen la animación, la música, los efectos y los subtítulos.
#   python assemble_vo.py
#
# Opciones en script.json (todas opcionales):
#   "lead_in": 0.35      silencio antes de la primera palabra
#   "tail": 2.6          cierre después de la última palabra
#   "duration": 97.26    duración total fija (ajusta el cierre; útil si la música ya está generada)
#   "fps": 60
#   por segmento: "gap": 0.5 (pausa después), "start_at": 92.9 (empieza exactamente en ese segundo:
#   sirve para regrabar un tramo sin mover lo que viene después ni desalinear la música)
import json, os, subprocess, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
SR = 48000
MAX_PAUSE = 0.24   # las pausas internas más largas se recortan a esto (ritmo de video corto)
EDGE = 0.04        # silencio que se conserva en los bordes de cada segmento


def decode(path):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()


def silences(x, win=0.01, thr_db=-42.0, min_len=0.12):
    n = int(SR * win); frames = len(x) // n
    rms = np.sqrt(np.mean(x[: frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)
    quiet = 20 * np.log10(rms / np.percentile(rms, 95) + 1e-12) < thr_db
    out, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if (not q or i == frames - 1) and start is not None:
            end = i if not q else i + 1
            if (end - start) * win >= min_len:
                out.append((start * win, end * win))
            start = None
    return out


def tighten(x, words):
    dur, cuts = len(x) / SR, []
    for a, b in silences(x):
        if a <= 0.02:
            if b - EDGE > 0: cuts.append((0.0, max(0.0, b - EDGE)))
        elif b >= dur - 0.02:
            if a + EDGE < dur: cuts.append((a + EDGE, dur))
        elif b - a > MAX_PAUSE:
            extra, mid = (b - a) - MAX_PAUSE, (a + b) / 2
            cuts.append((mid - extra / 2, mid + extra / 2))
    keep, pos = [], 0.0
    for a, b in cuts:
        keep.append((pos, a)); pos = b
    keep.append((pos, dur))
    fade, parts = int(SR * 0.004), []
    for a, b in keep:
        seg = x[int(a * SR): int(b * SR)].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
        parts.append(seg)
    y = np.concatenate(parts) if parts else x

    def remap(t):
        removed = 0.0
        for a, b in cuts:
            removed += (b - a) if t >= b else max(0.0, t - a)
        return max(0.0, t - removed)

    return y, [{"w": w["w"], "t0": remap(w["t0"]), "t1": remap(w["t1"])} for w in words], dur - len(y) / SR


def main():
    script = json.load(open("script.json", encoding="utf-8"))
    segs = script["segments"]
    lead, tail, fps = script.get("lead_in", 0.35), script.get("tail", 2.6), script.get("fps", 60)
    t, track, scenes, saved = lead, [np.zeros(int(lead * SR), dtype=np.float32)], [], 0.0
    for i, seg in enumerate(segs):
        sid = seg["id"]
        meta = json.load(open(f"audio/vo_{sid}.json", encoding="utf-8"))
        y, words, cut = tighten(decode(f"audio/vo_{sid}.mp3"), meta["words"])
        saved += cut
        if "start_at" in seg:
            pad = seg["start_at"] - t
            if pad < -0.01:
                print(f"  aviso: {sid} no puede empezar en {seg['start_at']}s; lo anterior termina en {t:.2f}s")
            pad = max(0.0, pad)
            track.append(np.zeros(int(round(pad * SR)), dtype=np.float32)); t += pad
        d = len(y) / SR
        scenes.append({"id": sid, "scene": seg["scene"], "vo_start": round(t, 3), "vo_end": round(t + d, 3),
                       "words": [{"w": w["w"], "t0": round(t + w["t0"], 3), "t1": round(t + w["t1"], 3)} for w in words]})
        track.append(y)
        last = i == len(segs) - 1
        gap = (max(0.3, script["duration"] - (t + d)) if "duration" in script else tail) if last else seg.get("gap", 0.34)
        track.append(np.zeros(int(round(gap * SR)), dtype=np.float32))
        t += d + gap
    audio = np.concatenate(track)
    if "duration" in script:
        n = int(round(script["duration"] * SR))
        audio = np.pad(audio, (0, max(0, n - len(audio))))[:n]
    total = len(audio) / SR
    for i, s in enumerate(scenes):   # los cortes de escena caen a mitad de la pausa entre segmentos
        s["start"] = 0.0 if i == 0 else round((scenes[i - 1]["vo_end"] + s["vo_start"]) / 2, 3)
    for i, s in enumerate(scenes):
        s["end"] = round(total, 3) if i == len(scenes) - 1 else scenes[i + 1]["start"]
    audio = audio / (np.max(np.abs(audio)) + 1e-9) * 10 ** (-1.5 / 20)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "audio/vo.wav"],
                   input=(audio * 32767).astype(np.int16).tobytes(), check=True)
    tl = {"duration": round(total, 3), "fps": fps, "scenes": scenes}
    json.dump(tl, open("timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open("timeline.js", "w", encoding="utf-8").write("window.TL=" + json.dumps(tl, ensure_ascii=False) + ";")
    print(f"duración total {total:.2f}s (silencio recortado {saved:.2f}s)")
    for s in scenes:
        print(f"  {s['scene']:8s} {s['start']:6.2f} → {s['end']:6.2f} ({s['end'] - s['start']:5.2f}s)  voz {s['vo_start']:.2f}-{s['vo_end']:.2f}")


main()
