# Mezcla final: voz + música (que se agacha sola bajo la voz) + efectos, normalizada a -14 LUFS.
#   python mix.py [--music audio/music.mp3]
# Al terminar dice cuántos dB queda la música por debajo de la voz: entre 8 y 11 dB se oye con fuerza
# sin tapar al narrador; más de 13 dB la música casi desaparece; menos de 7 dB compite con la voz.
#
# Opcional mix.json:
#   { "music_under_db": -15,                nivel de la música antes de agacharse (LUFS); súbelo para más presencia
#     "duck": {"threshold": 0.035, "ratio": 2.5, "release": 350},  cuánto se agacha bajo la voz
#     "music_eq": "equalizer=f=2800:t=q:w=1.0:g=-4,bass=g=2.5:f=80",   hueco en medios para la voz + graves con pegada
#     "gains": [[3.7, 10.7, 2.6]],          multiplica la música en un tramo: >1 la sube donde la pista viene floja,
#     "dips": [[58.35, 60.95, 0.38]],       <1 la baja (un silencio dramático)
#     "tail_lift": 0.3,                     sube la música tras la última palabra (para que el cierre no se apague)
#     "sfx_db": -5 }
import json, os, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
music = sys.argv[sys.argv.index("--music") + 1] if "--music" in sys.argv else "audio/music.mp3"
tl = json.load(open("timeline.json", encoding="utf-8"))
cfg = json.load(open("mix.json", encoding="utf-8")) if os.path.exists("mix.json") else {}
DUR = tl["duration"]
last_word = max(s["vo_end"] for s in tl["scenes"])
duck = cfg.get("duck", {})


def lufs(path, a=None, b=None):
    cut = (["-ss", str(a), "-to", str(b)] if a is not None else [])
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *cut, "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(re.findall(r"\bI:\s+(-?[\d.]+) LUFS", out)[-1])


gain = cfg.get("music_under_db", -15) - lufs(music)
vol = [f"volume={gain:.1f}dB"]
for a, b, k in cfg.get("gains", []) + cfg.get("dips", []):
    vol.append(f"volume='1-{1 - k:.2f}*clip((t-{a})/0.25,0,1)*clip(({b}-t)/0.3,0,1)':eval=frame")
lift = cfg.get("tail_lift", 0.3)
if lift:
    vol.append(f"volume='1+{lift}*clip((t-{last_word - 0.25:.2f})/0.6,0,1)':eval=frame")
music_eq = cfg.get("music_eq", "equalizer=f=2800:t=q:w=1.0:g=-4,bass=g=2.5:f=80")
graph = (
    "[0:a]highpass=f=75,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,equalizer=f=3200:t=q:w=1.2:g=2,"
    "pan=stereo|c0=c0|c1=c0,asplit=3[v][vsc][vst];"
    f"[1:a]aresample=48000,{music_eq + ',' if music_eq else ''}{','.join(vol)},afade=t=in:st=0:d=0.25,afade=t=out:st={DUR - 1.4:.2f}:d=1.4[m];"
    f"[m][vsc]sidechaincompress=threshold={duck.get('threshold', 0.035)}:ratio={duck.get('ratio', 2.5)}:attack=15:release={duck.get('release', 350)},asplit=2[md][mst];"
    f"[2:a]volume={cfg.get('sfx_db', -5)}dB,aecho=0.8:0.55:75|140:0.16|0.09[fx];"
    f"[v][md][fx]amix=inputs=3:normalize=0:duration=longest,atrim=0:{DUR},alimiter=limit=0.9:attack=4:release=60[out]"
)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "audio/vo.wav", "-i", music, "-i", "audio/sfx.wav", "-filter_complex", graph,
                "-map", "[out]", "-ar", "48000", "audio/premix.wav", "-map", "[vst]", "-ar", "48000", "audio/stem_voz.wav",
                "-map", "[mst]", "-ar", "48000", "audio/stem_musica.wav"], check=True)
g = -14 - lufs("audio/premix.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "audio/premix.wav", "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:attack=3:release=50:level=disabled",
                "-ar", "48000", "audio/mix.wav"], check=True)

# Balance global en el tramo central con voz, y escena por escena: la pista no suena igual de fuerte en todas
# sus secciones, y donde la música queda a más de 13 dB de la voz el espectador no la oye (súbela con "gains").
a, b = min(DUR * 0.25, 20), max(last_word - 8, DUR * 0.5)
under = lufs("audio/stem_voz.wav", a, b) - lufs("audio/stem_musica.wav", a, b)
print(f"música {gain:+.1f} dB · ganancia final {g:+.2f} dB · audio/mix.wav a {lufs('audio/mix.wav'):.1f} LUFS")
print(f"balance: la música queda {under:.1f} dB por debajo de la voz" + ("  (casi no se oirá: sube music_under_db)" if under > 13 else "  (puede tapar la voz: baja music_under_db)" if under < 7 else ""))
for sc in tl["scenes"]:
    if sc["vo_end"] - sc["vo_start"] < 1.5:
        continue
    try:
        d = lufs("audio/stem_voz.wav", sc["vo_start"], sc["vo_end"]) - lufs("audio/stem_musica.wav", sc["vo_start"], sc["vo_end"])
    except (IndexError, ValueError):
        continue
    print(f"  {sc['scene']:10s} {d:5.1f} dB" + ("  <- música muy baja" if d > 13 else "  <- música muy alta" if d < 6.5 else ""))
