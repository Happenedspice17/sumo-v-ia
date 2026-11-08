# Manual de uso: robot de laberinto (UNO Q)

## 0. Antes de prender

- Batería cargada: **7.4 V o más** (con menos de 7 V el L298N pierde fuerza).
- Ruedas sin pelusa, nada rozando.
- Robot en la **celda de inicio** (esquina abajo-izquierda), **mirando hacia arriba** del laberinto.

## 1. Prender

1. Prende el switch. **No toques D2.**
2. Espera **~20 s** hasta que la OLED diga `LABERINTO` y el número de `PY` empiece a subir.
3. Si `PY` no sube: Python no arrancó. Conecta a App Lab y dale **Run**.

## 2. El botón D2

| Cómo | Qué hace |
|---|---|
| Presionado **al prender** | Modo calibración |
| Toque corto | **Arranca la corrida** |
| Mantener **más de 2 s** y soltar | Borra el mapa guardado |

## 3. La pantalla

```
LABERINTO  LISTO        <- estado
ROJO    0               <- marcas de color contadas
VERDE   0
AZUL    0
AMAR    0
PY 123 B          T:0   <- Python vivo / última orden / total
```

Estados: `LISTO`, `SIN CAM` (listo, sin cámara), `EXPLORA` (va a la meta), `REGRESO` (vuelve al inicio), `RAPIDO` (corrida con mapa), `META` (llegó), `BORRADO`.

Letras al final de `PY`: `B` toque corto, `L` toque largo, `M` avanzando, `G` girando, `-` nada.

## 4. Jugar (la competencia)

1. **Primera corrida:** toque corto. Explora hasta la meta (`EXPLORA`), regresa al inicio (`REGRESO`) y guarda el mapa.
2. **Siguientes corridas:** regrésalo al inicio, mismo rumbo, toque corto. Con mapa completo va directo y rápido (`RAPIDO` → `META`).
3. **Laberinto nuevo:** mantén D2 más de 2 s → `BORRADO`. Luego toque corto.

El mapa queda guardado aunque apagues.

## 5. Calibrar colores (una vez por pista / luz)

1. Apaga. **Mantén D2 presionado** y prende. Suelta cuando salga `CALIBRACION`.
2. Pon el sensor sobre cada color, quieto, y anota los 4 números:

| Color | r | g | b | c |
|---|---|---|---|---|
| PISO | | | | |
| ROJO | | | | |
| VERDE | | | | |
| AZUL | | | | |
| AMAR | | | | |

3. En `sketch.ino`, cambia la tabla `refs[]` con tus valores (mismo orden: r, g, b, c):

```cpp
  {"PISO",  0.33, 0.33, 0.33, 900},
  {"ROJO",  0.58, 0.22, 0.20, 400},
```

4. Dale **Run** en App Lab. Vuelve a calibración y revisa que el nombre que sale a la derecha de `c` sea el correcto en cada color.

Si un color sale como `PISO`: sus números están lejos de la tabla, vuelve a medirlo. La misma pantalla muestra las 3 distancias (izq, frente, der) en mm: sin nada cerca deben dar más de 120.

## 6. Calibrar movimiento (en `sketch.ino`, sección Calibracion)

Haz cada prueba con la batería cargada. Cambia un número, **Run**, prueba otra vez.

| Problema | Ajusta | Cómo |
|---|---|---|
| Avanza menos/más de una celda (18 cm) | `MS_CELDA` | Sube si se queda corto, baja si se pasa |
| Igual, pero en `RAPIDO` | `MS_RAPIDA` | Igual |
| Gira menos/más de 90° | `MS_90` | Sube si gira poco, baja si gira de más |
| Se desvía a un lado en recto | `AJUSTE_DER` | Se va a la derecha: positivo (ej. 10). A la izquierda: negativo |
| Se para lejos/cerca de la pared de enfrente | `D_FRENTE` | mm entre sensor y pared con el robot centrado |
| Zigzaguea entre paredes | `KC` | Bájalo (ej. 0.5) |
| No se centra | `KC` | Súbelo (ej. 1.2) |
| Ve paredes que no hay / no ve las que sí | `PARED` | mm: menor que esto = pared |
| Muy lento / muy rápido | `VEL_EXPLORA`, `VEL_RAPIDA`, `VEL_GIRO` | 0–255 |

Orden recomendado: `MS_90` → `MS_CELDA` → `AJUSTE_DER` → `D_FRENTE` → `KC`.

## 7. Si algo falla

| Síntoma | Causa | Arreglo |
|---|---|---|
| No se mueve | No le diste el toque a D2 | Toque corto 😉 |
| No se mueve, sale `M` | Batería baja o cables | Mide borne 12V del L298N (> 7 V) |
| `PY` no sube | Python no corre | Run en App Lab; app de arranque: `arduino-app-cli properties set default user:laberinto` |
| OLED dice `SIN VL53L0X` | Un ToF no responde | Revisa sus 4 cables y su XSHUT (A0/A1/A2) |
| OLED dice `SIN SENSOR COLOR` | TCS34725 no responde | Revisa SDA/SCL/VCC/GND |
| Gira al lado contrario | Motores cruzados | Intercambia OUT1-2 con OUT3-4 |
| Un motor va al revés | Cables de ese motor invertidos | Voltea sus 2 cables en el L298N |
| Se queda dando vueltas sin rumbo | Mapa viejo de otro laberinto | Toque largo (borrar) |
| OLED negra al prender por VIN | Tarda en despertar | Espera; si sigue, sube el `delay(500)` del `setup()` a 1500 |

## 8. Laberinto distinto

En `python/main.py`: `N` (celdas por lado), `INICIO`, `RUMBO_INI` (0=arriba 1=derecha 2=abajo 3=izquierda) y `META`.
