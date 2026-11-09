# Mezcla final: voz + música (que se agacha sola bajo la voz) + efectos, normalizada a -14 LUFS.
#   python mix.py [--music audio/music.mp3]
# Opcional mix.json: { "dips": [[58.35, 60.95, 0.38]],   baja la música a ese factor en un tramo (un silencio dramático)
#                      "tail_lift": 0.9,                  sube la música tras la última palabra (para que el cierre no se apague)
#                      "music_under_db": -22.6,           nivel de la música antes del ducking (LUFS)
#                      "sfx_db": -5 }
import json, os, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
music = sys.argv[sys.argv.index("--music") + 1] if "--music" in sys.argv else "audio/music.mp3"
tl = json.load(open("timeline.json", encoding="utf-8"))
cfg = json.load(open("mix.json", encoding="utf-8")) if os.path.exists("mix.json") else {}
DUR = tl["duration"]
last_word = max(s["vo_end"] for s in tl["scenes"])


def lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(re.findall(r"\bI:\s+(-?[\d.]+) LUFS", out)[-1])


gain = cfg.get("music_under_db", -22.6) - lufs(music)
vol = [f"volume={gain:.1f}dB"]
for a, b, k in cfg.get("dips", []):
    vol.append(f"volume='1-{1 - k:.2f}*clip((t-{a})/0.25,0,1)*clip(({b}-t)/0.3,0,1)':eval=frame")
lift = cfg.get("tail_lift", 0.9)
if lift:
    vol.append(f"volume='1+{lift}*clip((t-{last_word - 0.25:.2f})/0.6,0,1)':eval=frame")
graph = (
    "[0:a]highpass=f=75,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
    f"[1:a]aresample=48000,{','.join(vol)},afade=t=in:st=0:d=0.25,afade=t=out:st={DUR - 1.4:.2f}:d=1.4[m];"
    "[m][vsc]sidechaincompress=threshold=0.022:ratio=6:attack=15:release=420[md];"
    f"[2:a]volume={cfg.get('sfx_db', -5)}dB,aecho=0.8:0.55:75|140:0.16|0.09[fx];"
    f"[v][md][fx]amix=inputs=3:normalize=0:duration=longest,atrim=0:{DUR},alimiter=limit=0.9:attack=4:release=60[out]"
)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "audio/vo.wav", "-i", music, "-i", "audio/sfx.wav", "-filter_complex", graph,
                "-map", "[out]", "-ar", "48000", "audio/premix.wav"], check=True)
g = -14 - lufs("audio/premix.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "audio/premix.wav", "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:attack=3:release=50:level=disabled",
                "-ar", "48000", "audio/mix.wav"], check=True)
print(f"música {gain:+.1f} dB · ganancia final {g:+.2f} dB · audio/mix.wav a {lufs('audio/mix.wav'):.1f} LUFS")
