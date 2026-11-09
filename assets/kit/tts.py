# Voz por segmento con ElevenLabs, con marcas de tiempo por carácter -> tiempos de cada palabra.
#   python tts.py            genera los segmentos que falten
#   python tts.py s03 s07    regenera solo esos (borra antes sus archivos si cambiaste el texto)
#
# script.json:
#   { "lang": "es", "voice": {"speed": 1.16, "stability": 0.42, "similarity_boost": 0.8},
#     "segments": [ {"id": "s01", "scene": "hook", "text": "Soy {Claude|Clod} {5.2,|cinco punto dos,} ..."} ] }
#
# Marcado {pantalla|hablado}: a la izquierda lo que se lee en subtítulos, a la derecha lo que pronuncia la voz.
# Úsalo para cifras ("{30%|treinta por ciento}") y nombres en otro idioma ("{Claude|Clod}"): los modelos
# rápidos no normalizan números y leen los nombres extranjeros con fonética del idioma elegido.
import base64, json, os, re, sys, urllib.request, urllib.error
from kit_env import load_env, need

sys.stdout.reconfigure(encoding="utf-8")
env = load_env()
KEY = need(env, "ELEVENLABS_API_KEY", "Ponla en .env o en ~/.link-a-video.env")
VOICE = need(env, "ELEVENLABS_VOICE_ID", "Añade ELEVENLABS_VOICE_ID (id de la voz) al mismo .env")
MODEL = env.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
MARK = re.compile(r"\{([^|{}]+)\|([^|{}]+)\}")


def parse(text):
    """-> (texto hablado, [(palabra en pantalla, char inicial, char final)])"""
    spoken, words, pos, parts = "", [], 0, []
    for m in MARK.finditer(text):
        if m.start() > pos:
            parts.append((text[pos:m.start()], None))
        parts.append((m.group(2), m.group(1)))
        pos = m.end()
    if pos < len(text):
        parts.append((text[pos:], None))
    for chunk, display in parts:
        if display is not None:
            a = len(spoken); spoken += chunk
            words.append((display, a, len(spoken)))
        else:
            for m in re.finditer(r"\S+|\s+", chunk):
                a = len(spoken); spoken += m.group(0)
                if not m.group(0).isspace():
                    words.append((m.group(0), a, len(spoken)))
    return spoken, words


def tts(spoken, prev_text, next_text, seed, lang, vs):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128"
    body = {"text": spoken, "model_id": MODEL, "language_code": lang, "seed": seed,
            "voice_settings": {"stability": vs.get("stability", 0.42), "similarity_boost": vs.get("similarity_boost", 0.8),
                               "use_speaker_boost": True, "speed": vs.get("speed", 1.16)}}
    if prev_text: body["previous_text"] = prev_text      # continuidad de entonación entre segmentos
    if next_text: body["next_text"] = next_text
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"xi-api-key": KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def main():
    only = set(sys.argv[1:])
    data = json.load(open("script.json", encoding="utf-8"))
    segs, lang, vs = data["segments"], data.get("lang", "es"), data.get("voice", {})
    parsed = [parse(s["text"]) for s in segs]
    os.makedirs("audio", exist_ok=True)
    sent = 0
    for i, s in enumerate(segs):
        spoken, words = parsed[i]
        mp3, meta = f"audio/vo_{s['id']}.mp3", f"audio/vo_{s['id']}.json"
        if (only and s["id"] not in only) or (not only and os.path.exists(mp3) and os.path.exists(meta)):
            continue
        res = tts(spoken, parsed[i - 1][0] if i else None, parsed[i + 1][0] if i + 1 < len(segs) else None,
                  s.get("seed", 5200 + i), lang, {**vs, **s.get("voice", {})})   # "voice"/"seed" por segmento: para acelerar o variar una sola frase
        open(mp3, "wb").write(base64.b64decode(res["audio_base64"]))
        al = res["alignment"]
        st, en, n = al["character_start_times_seconds"], al["character_end_times_seconds"], len(al["characters"])
        out = [{"w": d, "t0": round(st[min(a, n - 1)], 3), "t1": round(en[min(b, n) - 1], 3)} for d, a, b in words]
        json.dump({"id": s["id"], "scene": s["scene"], "spoken": spoken, "words": out}, open(meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sent += len(spoken)
        print(f"{s['id']} {s['scene']:8s} {len(spoken):4d} caracteres · {en[-1]:5.2f}s | {spoken[:56]}")
    print("caracteres enviados:", sent)


main()
