# API del motor (`engine.js`)

La página carga `gsap`, `timeline.js` y `engine.js`, y define `window.build(VE)`. El motor espera fuentes e imágenes, llama a `build`, añade subtítulos, viñeta y grano, y expone `window.seek(t)` y `window.READY` para la captura.

## Datos

| Nombre | Qué es |
|---|---|
| `VE.S` | Escenas por nombre: `S.intro.start`, `S.intro.end`, `S.intro.words` (`[{w, t0, t1}]`) |
| `VE.DUR`, `VE.FPS` | Duración total y fotogramas por segundo |
| `VE.wt(escena, palabra, n = 0)` | Segundo en que se pronuncia la palabra (la n-ésima vez). Ignora mayúsculas, tildes y puntuación: `wt("precio", "$8")`, `wt("hook", "lo", 1)`. Lanza error si no existe, para que un cambio de guion no pase inadvertido |
| `VE.tl` | La línea de tiempo de GSAP (en pausa) para lo que no cubran los atajos |

## Atajos de animación

| Función | Uso |
|---|---|
| `sceneCuts([nombres])` | Muestra cada `#sc-<nombre>` solo durante su escena (corte duro). La última queda visible hasta el final |
| `show(sel, a, b)` | Visible entre `a` y `b` (sub-bloques dentro de una escena) |
| `IN(sel, t, desde, dur = 0.6, ease = "expo.out")` | Entrada: de `{y: 50}`, `{x: -40}`, `{scale: 2}`… a su sitio, con aparición |
| `OUT(sel, t, hacia, dur = 0.3)` | Salida con desvanecido |
| `kb(sel, a, b, s0, s1)` | Zoom lento (Ken Burns) de un contenedor `.kb` con el fondo dentro |
| `wipe(c, "v" \| "h")` | Cortina vertical u horizontal que cubre la pantalla en el segundo `c` |
| `bars([[barra, valor, n], …], t, gap)` | Barras `.bar` que crecen con su contador |
| `counter(sel, t0, t1, de, a, decimales)` | Número que cuenta entre dos tiempos |
| `showAt(el, t0, t1)` | Visible sin transición (líneas de terminal, parpadeos) |
| `onFrame(fn)` | `fn(t)` en cada fotograma, para canvas o lógica propia. Debe depender solo de `t` |
| `VE.captions` | `{skip: ["hook"], maxWords: 3, maxChars: 17}`: escenas sin subtítulos y tamaño de los grupos |

## Reglas que evitan fotogramas erróneos

- **Una entrada y una salida por elemento.** Dos animaciones de la misma propiedad sobre el mismo elemento dan estados equivocados cuando el render salta a mitad del video. Si necesitas más, envuelve el elemento en otro y anima cada uno una vez.
- **Sin `transform` en el CSS de lo que animas.** GSAP mezcla mal una rotación o un `translate(-50%)` del CSS con los suyos: pon la rotación fija en un contenedor y anima el hijo; centra con `left/width/text-align`.
- **Nada de relojes ni azar.** Ni `Date.now()`, ni `Math.random()`, ni animaciones CSS, ni `requestAnimationFrame`: todo sale de `t`. Para variación usa `VE.hash(i)`.
- **Clases no se animan** (`className` no funciona en GSAP 3): anima `backgroundColor`, `color`, `borderColor`.
- **Selectores CSS acotados.** Un `.fila span{…}` genérico también pisa los `<span>` de los contadores; usa `.fila > span`.

## HTML de las piezas comunes (estilos en `base.css`)

```html
<section class="scene" id="sc-dato">
  <div class="kb" id="dato-kb"><img class="bg" src="img/fondo.jpg"></div>
  <div class="shade" style="background:linear-gradient(180deg,rgba(20,20,19,0) 40%,rgba(20,20,19,.85) 62%)"></div>
  <div class="bar win" id="b1"><span class="bl">Etiqueta</span>
    <div class="row"><div class="bt" style="width:640px"></div><span class="bv"><span id="v1">0</span><small>%</small></span></div></div>
  <span class="chip">texto corto</span>
</section>
```

Variantes de barra: `.win` (ganador, verde), `.me` (protagonista, acento), `.riv` (rival destacado). El ancho en píxeles de `.bt` es el valor a escala (misma escala en todo el gráfico y eje desde cero, para no exagerar diferencias).
Tipografías: `.serif` (Fraunces), `.mono` (JetBrains Mono, mayúsculas espaciadas), cuerpo en Bricolage Grotesque; `.it` cursiva; colores `.clay`, `.cactus`, `.iris`. La paleta está en `:root` de `base.css`: cámbiala por video.
