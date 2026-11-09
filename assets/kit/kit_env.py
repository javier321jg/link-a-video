# Carga de claves sin escribirlas nunca en el proyecto ni en la salida.
# Orden de búsqueda: variables de entorno -> ./.env -> archivo indicado en LINK_A_VIDEO_ENV -> ~/.link-a-video.env
import os
import sys


def _parse(path):
    out = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_env():
    env = {}
    for p in (os.path.expanduser("~/.link-a-video.env"), os.environ.get("LINK_A_VIDEO_ENV", ""), ".env"):
        if p:
            env.update(_parse(p))
    env.update({k: v for k, v in os.environ.items() if k.startswith(("ELEVENLABS_", "HF_"))})
    return env


def need(env, key, hint):
    if not env.get(key):
        sys.exit(f"Falta {key}. {hint}")
    return env[key]


def hf_token(env):
    tok = env.get("HF_TOKEN")
    if not tok:
        try:
            tok = open(os.path.expanduser("~/.cache/huggingface/token"), encoding="utf-8").read().strip()
        except OSError:
            tok = ""
    if not tok:
        sys.exit("Falta el token de Hugging Face: ejecuta `hf auth login` o define HF_TOKEN.")
    return tok
