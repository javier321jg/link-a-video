---
name: link-a-video
description: Convierte un link (noticia, lanzamiento, artículo, página de producto) o un guion en un video vertical 1080x1920 listo para TikTok, Reels o Shorts, con guion verificado contra la fuente, voz y música de ElevenLabs, imágenes generadas en un Space de Hugging Face, motion graphics con subtítulos palabra por palabra, portada y texto para publicar. Úsala SIEMPRE que pidan "hazme un video de este link", "video para TikTok / Shorts / Reels sobre X", "explica esto en un video", "video informativo o explicativo con voz y música", "convierte este guion en video" o "motion graphics de esta noticia", aunque lo escriban con errores ("vide", "tok tok", "motion grafhs") o no nombren la skill. No es para editar clips que ya existen (recortes, AMV, subir FPS) ni para grabar demos de una web en uso.
---

# link-a-video

De un link o un guion a un video vertical informativo, hecho entero con código: nada se graba ni se edita a mano.
Cada paso deja archivos en disco, así que se puede rehacer una sola parte (una frase, una escena, la música) sin repetir el resto.

## Qué recibe y qué entrega

| Entrada | Por defecto | Se cambia con |
|---|---|---|
| Link o guion | obligatorio (uno de los dos) | — |
| Duración | 60–100 s | "de 30 segundos", "de 2 minutos" |
| Idioma y voz | español; la voz de `ELEVENLABS_VOICE_ID` | "en inglés", otro id de voz |
| Marca | ninguna | nombre + ruta del logo (`brand/logo.png`) |
| Formato | 1080×1920, 60 fps | — |

Entrega en la carpeta del proyecto: `<nombre>.mp4`, `<nombre>.jpg` (portada), `share-copy.txt` (texto para publicar) y `plan.md` (guion y escenas). Todo lo intermedio queda en `work/`.

## Requisitos

- `ffmpeg`, Node.js 18+, Python 3.10+ con `numpy`, y Chrome o Edge instalado (se usa sin ventana).
- ElevenLabs: `ELEVENLABS_API_KEY` y `ELEVENLABS_VOICE_ID` en el entorno, en `work/.env` o en `~/.link-a-video.env`. Si faltan, pídeselas al usuario y guárdalas ahí; nunca las escribas en el chat, en el plan ni en nada que se entregue.
- Hugging Face: sesión iniciada (`hf auth login`) o `HF_TOKEN`. Las imágenes gastan la cuota ZeroGPU de la cuenta.

Antes de empezar comprueba qué hay y dilo en una línea; si falta algo que no puedes instalar, avisa en vez de improvisar otra herramienta.

## Flujo

Trabaja siempre dentro de `work/`. Los comandos de abajo se ejecutan ahí.

```bash
python <skill>/scripts/new_project.py <carpeta-del-video>     # copia el kit y hace npm install
```

1. **Investigar.** Con link: `node inspect_site.mjs <url>` guarda `site/page.txt` (texto completo), `site/identity.json` (colores y fuentes) y capturas. Lee el texto tú mismo y busca en él cada cifra que vayas a usar: los resúmenes automáticos cambian números y matices. Con guion: el guion del usuario es la fuente; no añadas datos que no estén en él sin decirlo.
2. **Guion.** Escribe `script.json` (formato en `tts.py`) siguiendo las reglas de contenido de abajo, y `plan.md` con ángulo, gancho y tabla de escenas.
3. **Voz.** `python tts.py` y luego `python assemble_vo.py`. El segundo crea `timeline.json`: el reloj único del que salen animación, música, efectos y subtítulos. Mira la duración total; si se pasa, recorta texto y regenera solo esos segmentos (`python tts.py s03 s07`).
4. **Música.** Escribe `music.json` con una sección por bloque narrativo, anclada a escenas, y ejecuta `python music.py`. Lee los niveles que imprime: la última sección debe sostenerse hasta el final.
5. **Imágenes.** `python gen_img.py <nombre> "<prompt en inglés>"`, una por escena que lo pida, de una en una. Usa un sufijo de estilo común para que parezcan del mismo video y deja libre la zona donde irá el texto. Mira cada imagen antes de usarla.
6. **Animación.** Escribe `video.html`: una `<section class="scene" id="sc-<escena>">` por escena y `window.build(VE)` con la coreografía. La API está en `references/engine-api.md`; `examples/fable52/` es un video completo de 11 escenas.
7. **Revisar.** `node still.mjs <tiempos> --sheet a` y mira las hojas de contacto: al menos un fotograma asentado por escena y uno a mitad de cada transición. Corrige desbordes, choques y bajo contraste antes de renderizar.
8. **Sonido.** Escribe `sfx_events.json` con las mismas anclas que la animación, luego `python sfx.py` y `python mix.py`.
9. **Render y entrega.** `node render.mjs --poster <segundo>` (el póster es un fotograma asentado, sin subtítulos) y `python finish.py --name <nombre>`. Extrae fotogramas del `.mp4` final y míralos antes de decir que está listo.

Para corregir algo después: cambia el archivo, vuelve a ejecutar solo los pasos que dependen de él y, si es un tramo corto, renderízalo con `--from/--to` a otro archivo y une las partes con `finish.py --parts`. `"start_at"` y `"duration"` en `script.json` permiten regrabar una frase sin mover lo demás ni desalinear la música.

## Reglas de contenido

El video es **informativo sobre el tema**, no sobre sí mismo.

- **No expliques cómo se hizo el video.** Nada de créditos de herramientas, listas de "guion / voz / música", ni menciones a esta skill, a modelos de voz o de imagen. Si viene al caso, basta una línea que indique que fue creado con IA (por ejemplo "Este video fue creado con …" cuando el tema es justo ese modelo) y el aviso pequeño del cierre.
- **Solo lo que dice la fuente.** Cada cifra y afirmación debe poder señalarse en `site/page.txt` o en el guion del usuario. Si la fuente dice "hasta 30 %", el video dice "hasta". No redondees a favor ni inventes comparaciones.
- **Di también lo que no favorece.** Si la fuente muestra dónde pierde el producto, un beat honesto ("¿Gano en todo? No.") da más credibilidad que otro elogio. Cuando los datos son del propio fabricante, ponlo en pantalla ("cifras publicadas por …").
- **Gancho en los dos primeros segundos**, con texto grande en pantalla desde el primer fotograma. Planifícalo antes que nada.
- **Una idea por escena**, frases cortas, cifras concretas. Cuenta ~2.3 palabras por segundo de voz para estimar la duración.
- **Cierre:** resumen de dos o tres ideas, llamada a seguir la cuenta y marca del usuario. Añade siempre en pequeño la fuente y "Video hecho con IA"; si el tema es una empresa o producto ajeno, también "no es contenido oficial de …".
- **No suplantes a la fuente.** Usa su paleta si ayuda a reconocer el tema, pero no su logotipo como firma ni sus tipografías propietarias; el video lo firma la marca del usuario.
- **Pronunciación.** Escribe cifras y nombres extranjeros con el marcado `{pantalla|hablado}`: `{30%|treinta por ciento}`, `{Claude|Clod}`.

## Animación en pocas líneas

```js
window.build = function (VE) {
  const { S, wt, IN, OUT, kb, wipe, bars, counter, sceneCuts } = VE;
  sceneCuts(["hook", "dato", "cierre"]);            // cortes duros entre escenas
  wipe(S.dato.start);                               // cortina que tapa cada corte
  kb("#dato-kb", S.dato.start, S.dato.end, 1.1, 1); // zoom lento del fondo
  IN("#titulo", wt("dato", "rendimiento") - 0.08, { y: 50 });   // entra cuando se dice la palabra
  counter("#num", wt("dato", "64%") - 0.1, wt("dato", "64%") + 0.6, 0, 64);
};
```

Ancla todo a palabras con `wt(escena, palabra)`, no a segundos escritos a mano: si se regenera la voz, la animación sigue sincronizada. Mantén el contenido en las zonas seguras (comentadas en `video.html`). Los subtítulos, las cortinas, el grano y la captura los pone el motor.

## Al entregar

- Di dónde están el video y el texto, la duración y el tamaño, y resume el ángulo en una frase.
- Recuerda activar la etiqueta de contenido generado con IA al publicar.
- Informa de lo gastado (créditos de ElevenLabs antes y después, imágenes generadas) y de cualquier cosa que no se pudo verificar; el audio no se puede escuchar desde aquí, así que di que conviene oírlo una vez.
- Si el usuario pegó un logo en el chat en vez de dar un archivo, no se puede insertar: pide la ruta y mientras tanto cierra con el nombre de la marca en texto.

Lee `references/lecciones.md` antes de la primera animación y cuando algo falle: recoge los tropiezos ya resueltos (GSAP al saltar en el tiempo, render en paralelo, música que se apaga antes del final, tamaños de archivo).
