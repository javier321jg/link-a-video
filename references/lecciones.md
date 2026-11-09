# Lecciones ya pagadas

Cosas que fallaron al construir el primer video con este kit y cómo quedaron resueltas. Léelas antes de animar y cuando algo no cuadre.

## Voz
- **La voz dura más de lo que parece.** En español sale a ~2.2–2.6 palabras por segundo aunque pidas velocidad 1.16. Un guion de 250 palabras son ~100 s. Estima, genera, mira `timeline.json` y recorta texto antes de tocar la velocidad.
- **Las frases finales se alargan.** Una frase solemne al final de un segmento puede tardar el doble. Si hay que encajarla en un hueco, ponla en su propio segmento con `"voice": {"speed": 1.2}`.
- **Regrabar sin mover nada.** Para cambiar una frase cuando la música ya existe, fija `"duration"` en `script.json` y `"start_at"` en el segmento que debe seguir en su sitio; `assemble_vo.py` avisa si no cabe.
- **Cifras y nombres.** `eleven_flash_v2_5` no normaliza números: escríbelos en letras con `{30%|treinta por ciento}`. Los nombres en inglés suenan mejor reescritos (`{Claude|Clod}`, `{Gemini|Yéminai}`).
- No se puede escuchar el resultado desde el agente. Una transcripción rápida (Whisper) confirma que los nombres se entienden; el timbre y la música los tiene que oír la persona.

## Música
- **Se apaga antes de tiempo.** Si la última sección es larga y pides "fade out", la música muere 8–10 s antes del final. Parte el cierre en dos secciones y pide a la última que "se sostenga hasta el último segundo"; `music.py` avisa si detecta el problema.
- Las secciones respetan su duración, no siempre su carácter (un "breakdown" puede no bajar). Para un silencio dramático usa `"dips"` en `mix.json`.
- El error 429 `system_busy` es pasajero; el script reintenta solo.
- Pide tonalidad y tempo en los estilos globales y usa la misma tonalidad en `sfx_events.json` (`"key"`), para que efectos y música suenen a una sola pieza.

## Imágenes
- Una a la vez: ZeroGPU no admite paralelo y cada imagen tarda 6–12 s.
- Pide composición pensando en el texto ("sujeto en la mitad superior, mitad inferior oscura y vacía") y termina todos los prompts con el mismo sufijo de estilo.
- Mira cada imagen: aparecen objetos no pedidos (una furgoneta en un túnel de luces). Regenera con "no vehicles, no objects" antes que disimularlo.
- Para superponer interfaz sobre un objeto de la imagen (la pantalla de una laptop), mide su rectángulo con PIL en vez de adivinarlo.

## Animación y render
- **Un Chrome por trabajador.** Varias pestañas en un mismo Chrome se quedan colgadas al capturar en segundo plano. `render.mjs` ya lanza un navegador por tramo y reintenta el arranque.
- ~100 ms por fotograma y navegador; con 6 trabajadores, 97 s a 60 fps tardan unos 5 minutos. Lanza los renders largos en segundo plano.
- **Rehacer solo un tramo.** Renderiza con `--from/--to` a otro archivo y une con `finish.py --parts`. Usa el mismo `render.mjs` para todos los tramos de un video: la unión es sin recodificar y necesita los mismos parámetros.
- **CSS sin cerrar.** Una regla truncada anida todo lo que sigue (Chrome admite anidamiento) y la página sale sin estilos. Si una hoja de contacto aparece "desnuda", busca una llave sin cerrar.
- **El fotograma 0 es la portada.** `--poster` lo sustituye por un fotograma asentado y sin subtítulos; no añade duración.
- El grano de película encarece el bitrate del intermedio (16 Mb/s), pero x264 lento lo deja en ~4.5 Mb/s: 97 s ocupan ~55 MB.

## Proceso
- **Verifica las cifras contra el texto de la página**, no contra un resumen. `site/page.txt` es la referencia.
- **Imágenes pegadas en el chat no son archivos.** Un logo pegado no se puede insertar: pide la ruta y deja el cierre preparado para `brand/logo.png`.
- **Preferencia del autor de esta skill:** videos informativos, sin "cómo se hizo" ni nombres de herramientas en pantalla.
- Guarda las claves en `.env` (ignorado por git) o en `~/.link-a-video.env`; nunca en el guion, el plan ni los comandos que se muestran.
