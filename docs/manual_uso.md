---
title: Manual de uso
subtitle: Robot de laberinto · UNO Q
---

::: {.aviso}
**Lo más importante:** el robot **no se mueve solo**. Después de prenderlo, espera a que suba el número de `PY` en la pantalla y **dale un toque al botón D2**.
:::

# 1. Revisa antes de prender

- [ ] Batería cargada: **7.8 V o más**
- [ ] Ningún cable suelto
- [ ] Ruedas giran libres
- [ ] Sensores limpios

# 2. Prende

1. Prende el switch **sin tocar el botón**.
2. Espera **20 segundos**.
3. La pantalla dice `LABERINTO` y el número de `PY` sube. **Ya está listo.**

::: {.nota}
Si `PY` no sube: conecta la laptop, abre App Lab y dale **Run**.
:::

# 3. El botón D2

| Haz esto | Pasa esto |
|---|---|
| **Toque corto** | Arranca |
| **Mantener 2 s** y soltar | Borra lo que aprendió |
| **Presionado al prender** | Modo prueba de sensores |

# 4. Calibra los colores (una vez por pista)

1. Prende el robot normal y espera a que suba `PY`.
2. En la laptop o el celular (en el mismo WiFi), abre **http://192.168.3.66:7000**. Si la IP cambia, App Lab la muestra al darle Run.
3. Sigue el asistente: pon el robot **en el piso de la pista**, quieto, encima del color que te pide, y aprieta **Guardar**. Son 5: piso, rojo, verde, azul y amarillo.
4. Al final sale **¡Listo!**. Pasa el sensor por cada color y revisa que arriba diga el nombre correcto. Si uno falla, dale **◀ Atrás** y repítelo.

::: {.nota}
Se guarda solo y se queda aunque apagues. Recalibra solo si cambias de pista o de lugar (otra luz).
:::

# 5. Revisa la cámara

En la misma página sale lo que ve la cámara. Con el robot en una celda, los cuadros salen **rojos** donde hay pared en la celda de adelante y **verdes** donde no. Si no coinciden, avísale a quien programa para ajustar `ROI`.

# 6. Ajusta el movimiento

Cambia **un número a la vez** en `sketch.ino`, dale **Run** y prueba.

| Si el robot... | Cambia | Así |
|---|---|---|
| Gira poco | `MS_90` | Súbelo 10 |
| Gira de más | `MS_90` | Bájalo 10 |
| No llega a la siguiente celda | `MS_CELDA` | Súbelo 25 |
| Se pasa de la celda | `MS_CELDA` | Bájalo 25 |
| Se va a la derecha | `AJUSTE_DER` | Ponle 10 |
| Se va a la izquierda | `AJUSTE_DER` | Ponle -10 |
| Zigzaguea | `KC` | Ponle 0.5 |

Después de cada prueba: **mantén D2 por 2 s** para borrar.

# 7. A jugar

1. En la página, elige el modo: **Mapa** (normal) o **Tonto** (sigue la pared derecha; si se atora, cambia solo a Mapa).
2. **Mantén D2 por 2 s** (borra las pruebas).
3. Pon el robot en la **esquina de inicio**, mirando hacia adelante.
4. **Toque corto.** Va a la meta y regresa solo.
5. Regrésalo al inicio y **toque corto** otra vez: ahora va directo y más rápido.

::: {.nota}
Entre intentos del mismo laberinto **no borres**: así recuerda el camino.
:::

# 8. Si algo falla

| Pasa esto | Haz esto |
|---|---|
| No se mueve | ¿Le diste el toque a D2? |
| `PY` no sube | App Lab → **Run** |
| `SIN VL53L0X` | Revisa los cables de los sensores de distancia |
| `SIN SENSOR COLOR` | Revisa los cables del sensor de color |
| La página no abre | Mismo WiFi que la Q; usa la IP que muestra App Lab con `:7000` |
| La cámara sale negra | Conecta cámara y hub **antes** de darle Run; el hub con su cargador |
| Un color sale mal | Repítelo en la página con **◀ Atrás** |
| Gira al revés | Cambia OUT1-2 por OUT3-4 en el puente H |
| Un motor va al revés | Voltea sus 2 cables en el puente H |
| Se pierde | Mantén D2 por 2 s para borrar |
| Pantalla negra | Espera; si sigue, revisa la batería |
