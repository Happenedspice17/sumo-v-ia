# Manual paso a paso: robot de laberinto (UNO Q)

Orden: **Paso 0** cada vez que lo prendas · **Pasos 1–3** días antes (y repetir 1 y 2 en la pista real el día de la competencia, si dejan) · **Paso 4** en la competencia.

---

## Paso 0. Chequeo de sanidad (2 min, siempre)

**Apagado:**

- [ ] Batería **cargada**: mide en sus bornes **7.8 V o más** (llena = 8.4 V; con menos de 7 V no la uses).
- [ ] Cables del motor bien apretados en OUT1–OUT4, ningún hilo suelto tocando otro.
- [ ] Dupont firmes: D5, D6, D7–D10 (L298N), D2 (botón), A0/A1/A2 (XSHUT), bus SDA/SCL/VCC/GND.
- [ ] Puente del bus en **3V3**.
- [ ] Jumpers de **ENA/ENB del L298N quitados**; jumper de 5V del L298N **puesto**.
- [ ] Ruedas giran libres con la mano, sin pelusa; patín sin basura.
- [ ] Sensores ToF y de color limpios (sin polvo ni huellas).

**Prendido (sin tocar D2):**

- [ ] A los ~20 s la OLED dice `LABERINTO`.
- [ ] El número de `PY` sube solo → Python corre.
- [ ] No aparece `SIN VL53L0X` ni `SIN SENSOR COLOR`.
- [ ] Nada huele a quemado ni se calienta el L298N en reposo.

Si algo falla → [Anexo C](#anexo-c-si-algo-falla).

---

## Paso 1. Calibrar colores (en la pista o con las mismas hojas/cintas de color)

1. Apaga. **Mantén D2 presionado** y prende. Suelta cuando salga `CALIBRACION`.
2. Pon el robot con el sensor sobre cada color, quieto, con la luz del lugar. Anota:

| Color | r | g | b | c |
|---|---|---|---|---|
| PISO | | | | |
| ROJO | | | | |
| VERDE | | | | |
| AZUL | | | | |
| AMAR | | | | |

3. Mientras estás ahí, revisa las 3 distancias de abajo (izq, frente, der, en mm):
   - Sin nada cerca: más de 120.
   - Con pared pegada al centrar el robot en una celda: anota frente = ____ y lado = ____ (sirven en el paso 2).
4. Abre App Lab, `sketch.ino`, tabla `refs[]` y pon tus números (orden r, g, b, c):

```cpp
  {"PISO",  0.33, 0.33, 0.33, 900},
  {"ROJO",  0.58, 0.22, 0.20, 400},
  ...
```

5. **Run**. Vuelve a entrar a calibración y pasa por cada color: el nombre al lado de `c` debe ser el correcto. Si uno sale `PISO`, vuelve a medir ese color.

---

## Paso 2. Calibrar movimiento

Todo en `sketch.ino`, sección `Calibracion`. **Un número a la vez → Run → probar.** Batería cargada.

Para probar: robot en una celda, toque corto a D2 y mira el primer movimiento. Después de cada prueba haz toque largo (borra el mapa) para empezar limpio.

| # | Qué revisar | Variable | Cómo ajustar |
|---|---|---|---|
| 1 | Giro de exactamente 90° | `MS_90` | Gira poco → sube. Gira de más → baja (de 10 en 10) |
| 2 | Avanza exactamente 1 celda (18 cm) | `MS_CELDA` | Se queda corto → sube. Se pasa → baja (de 25 en 25) |
| 3 | Va recto | `AJUSTE_DER` | Se va a la derecha → positivo (5, 10...). A la izquierda → negativo |
| 4 | Se para centrado frente a una pared | `D_FRENTE` | Pon el valor "frente" que anotaste en el paso 1 |
| 5 | Se centra entre paredes | `D_LADO` | Pon el valor "lado" que anotaste en el paso 1 |
| 6 | Centrado suave | `KC` | Zigzaguea → baja (0.5). No corrige → sube (1.2) |
| 7 | Detecta paredes bien | `PARED` | Ve paredes fantasma → baja. No ve paredes reales → sube |
| 8 | Corrida rápida exacta | `MS_RAPIDA` | Igual que `MS_CELDA`, pero se prueba en el paso 3 |

Velocidades (0–255): `VEL_EXPLORA`, `VEL_RAPIDA`, `VEL_GIRO`. Si patina o se pasa, bájalas.

Anota los valores finales aquí: `MS_90` = ___ `MS_CELDA` = ___ `MS_RAPIDA` = ___ `AJUSTE_DER` = ___ `D_FRENTE` = ___ `D_LADO` = ___ `KC` = ___ `PARED` = ___

---

## Paso 3. Ensayo completo

1. Si el laberinto no es 16×16 con meta al centro e inicio abajo-izquierda mirando arriba, cambia en `python/main.py`: `N`, `INICIO`, `RUMBO_INI` (0=arriba 1=derecha 2=abajo 3=izquierda), `META`. **Run**.
2. Toque largo → `BORRADO`.
3. Robot en el inicio, toque corto → `EXPLORA` hasta la meta, `REGRESO` al inicio, guarda el mapa.
4. Regrésalo al inicio, toque corto → `RAPIDO` → `META`. Ajusta `MS_RAPIDA` y `VEL_RAPIDA` si se pasa o choca.
5. Revisa que los conteos de colores en la OLED sean los reales.

---

## Paso 4. Día de la competencia

1. **Paso 0** completo. Batería recién cargada (lleva la de repuesto cargada).
2. Si dejan probar en la pista: **Paso 1** (la luz cambia los colores) y revisa `MS_90` / `MS_CELDA` con un par de movimientos.
3. **Toque largo** → `BORRADO` (borra el mapa de tus pruebas).
4. Robot en el inicio, bien centrado y derecho, mirando hacia donde dice `RUMBO_INI`.
5. Prende, espera a que suba `PY`, **toque corto**. No lo toques hasta que diga `META` o regrese.
6. Siguiente intento: regrésalo al inicio en la misma posición, **toque corto** (ya usa el mapa: `RAPIDO`). **No borres** entre intentos del mismo laberinto.

---

## Anexo A. Botón D2

| Cómo | Qué hace |
|---|---|
| Presionado **al prender** | Modo calibración |
| Toque corto | Arranca la corrida |
| Mantener **más de 2 s** y soltar | Borra el mapa |

## Anexo B. Pantalla

```
LABERINTO  LISTO        <- estado
ROJO    0               <- marcas de color
VERDE   0
AZUL    0
AMAR    0
PY 123 B          T:0   <- Python vivo / última orden / total
```

Estados: `LISTO` / `SIN CAM` (listo), `EXPLORA`, `REGRESO`, `RAPIDO`, `META`, `BORRADO`.
Letras: `B` toque corto, `L` toque largo, `M` avanzando, `G` girando, `-` nada.

## Anexo C. Si algo falla

| Síntoma | Causa | Arreglo |
|---|---|---|
| No se mueve | No le diste el toque a D2 | Toque corto 😉 |
| No se mueve, sale `M` | Batería baja o cables | Mide borne 12V del L298N (> 7 V) |
| `PY` no sube | Python no corre | Run en App Lab; app de arranque: `arduino-app-cli properties set default user:laberinto` |
| `SIN VL53L0X` | Un ToF no responde | Revisa sus 4 cables y su XSHUT (A0/A1/A2) |
| `SIN SENSOR COLOR` | TCS34725 no responde | Revisa SDA/SCL/VCC/GND |
| Gira al lado contrario | Motores cruzados | Intercambia OUT1-2 con OUT3-4 |
| Un motor va al revés | Cables de ese motor invertidos | Voltea sus 2 cables en el L298N |
| Da vueltas sin rumbo | Mapa de otro laberinto | Toque largo (borrar) |
| OLED negra al prender por VIN | Tarda en despertar | Espera; si sigue, sube el `delay(500)` del `setup()` a 1500 |
