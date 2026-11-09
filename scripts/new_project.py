# Crea un proyecto de video con el kit dentro:  python new_project.py <carpeta> [--no-install]
#   <carpeta>/            aquí quedan los entregables (video.mp4, portada, texto para publicar)
#   <carpeta>/work/       kit + todo lo intermedio (audio/, img/, site/, stills/, frames/, brand/)
# No pisa archivos que ya existan: se puede volver a ejecutar para actualizar un proyecto a medias.
import os, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
if len(sys.argv) < 2:
    sys.exit("uso: python new_project.py <carpeta> [--no-install]")
KIT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "kit")
work = os.path.join(os.path.abspath(sys.argv[1]), "work")
for d in ("audio", "img", "brand", "site", "stills", "frames"):
    os.makedirs(os.path.join(work, d), exist_ok=True)
starters = {"script.example.json": "script.json", "music.example.json": "music.json", "sfx_events.example.json": "sfx_events.json"}
for f in sorted(os.listdir(KIT)):
    dst = os.path.join(work, starters.get(f, f))
    if os.path.exists(dst):
        print("  se conserva", os.path.relpath(dst, work))
    else:
        shutil.copy2(os.path.join(KIT, f), dst)
if "--no-install" not in sys.argv:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        sys.exit("No encontré npm: instala Node.js y vuelve a ejecutar.")
    subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=work, check=True)
print(f"\nProyecto listo en {work}\nTrabaja dentro de esa carpeta: todos los scripts del kit leen y escriben ahí.")
