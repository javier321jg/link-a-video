# Une el video con el audio y deja los entregables en la carpeta del proyecto (un nivel arriba de work/).
#   python finish.py --name mi_video                      usa frames/video_silent.mp4
#   python finish.py --name mi_video --parts frames/a.mp4 frames/b.mp4    une varios tramos en ese orden
# Entrega: ../<name>.mp4 (H.264 + AAC, 1080x1920) y ../<name>.jpg (portada = fotograma 0).
import os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
a = sys.argv[1:]
name = a[a.index("--name") + 1] if "--name" in a else "video"
parts = a[a.index("--parts") + 1:] if "--parts" in a else ["frames/video_silent.mp4"]
parts = [p for p in parts if not p.startswith("--")]
os.makedirs("frames", exist_ok=True)
with open("frames/final_list.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(f"file '{os.path.abspath(p).replace(os.sep, '/')}'" for p in parts))
master, out, poster = "frames/master.mp4", f"../{name}.mp4", f"../{name}.jpg"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "frames/final_list.txt", "-i", "audio/mix.wav",
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", master], check=True)
# x264 lento da archivos pequeños (40-60 MB por 90 s) sin pérdida visible: cómodo para subir desde el teléfono.
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-map", "0:v", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", "-g", "120",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "copy", "-movflags", "+faststart", out], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-frames:v", "1", "-q:v", "2", poster], check=True)
info = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "csv=p=0", out]).decode().strip().split(",")
print(f"{out} · {float(info[0]):.2f}s · {int(info[1]) / 1048576:.1f} MB · portada {poster}")
