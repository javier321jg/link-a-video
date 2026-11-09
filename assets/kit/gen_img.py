# Imágenes con un Space de Hugging Face (API de Gradio). Por defecto: linoyts/qwen-image-2-1-realtime.
#   python gen_img.py fondo_hook "Dawn over a dark planet seen from orbit ..." [--seed 52] [--aspect 9:16] [--res 1536]
#   python gen_img.py logo_idea "..." --space usuario/otro-space --endpoint generate --extra '{"steps": 4}'
# Salida: img/<nombre>.jpg (y el original). Usa la cuota ZeroGPU de tu cuenta: genera de una en una, nunca en paralelo.
#
# Otro Space: lee primero https://huggingface.co/spaces/<usuario>/<space>/agents.md y
# https://<usuario>-<space>.hf.space/gradio_api/info para conocer el endpoint y sus parámetros, y pásalos con --extra.
import json, os, subprocess, sys, time, urllib.request, urllib.error
from kit_env import load_env, hf_token

sys.stdout.reconfigure(encoding="utf-8")
a = sys.argv[1:]
if len(a) < 2:
    sys.exit('uso: python gen_img.py <nombre> "<prompt en inglés>" [--seed N] [--aspect 9:16] [--res 1536] [--space u/s]')
opt = lambda k, d: a[a.index("--" + k) + 1] if "--" + k in a else d
name, prompt = a[0], a[1]
space = opt("space", "linoyts/qwen-image-2-1-realtime")
endpoint = opt("endpoint", "generate")
BASE = f"https://{space.replace('/', '-').replace('_', '-').replace('.', '-').lower()}.hf.space/gradio_api"
TOKEN = hf_token(load_env())
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
payload = {"prompt": prompt, "input_images": [], "seed": int(opt("seed", 52)), "resolution": int(opt("res", 1536)), "aspect_ratio": opt("aspect", "9:16")}
payload.update(json.loads(opt("extra", "{}")))


def call():
    req = urllib.request.Request(f"{BASE}/call/v2/{endpoint}", data=json.dumps(payload).encode(), headers=H)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            eid = json.load(r)["event_id"]
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
    event = last = None
    with urllib.request.urlopen(urllib.request.Request(f"{BASE}/call/{endpoint}/{eid}", headers=H), timeout=300) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                last = line[5:].strip()
                if event == "error":
                    sys.exit(f"error del Space (¿cuota ZeroGPU agotada?): {last[:400]}")
                if event == "complete":
                    return json.loads(last)
    sys.exit(f"el Space no devolvió resultado: {str(last)[:300]}")


t = time.time()
res = call()
item = res[0] if isinstance(res, list) else res
url = item.get("url") or f"{BASE}/file={item['path']}"
with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"}), timeout=120) as r:
    data = r.read()
os.makedirs("img", exist_ok=True)
ext = ".webp" if data[:4] == b"RIFF" else (".jpg" if data[:2] == b"\xff\xd8" else ".png")
raw = f"img/{name}_orig{ext}"
open(raw, "wb").write(data)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-q:v", "2", f"img/{name}.jpg"], check=True)
print(f"img/{name}.jpg · {len(data) // 1024} KB · {time.time() - t:.1f}s")
