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
| **Presionado al prender** | Modo calibración |

# 4. Calibra los colores (una vez por pista)

1. Apaga. **Mantén presionado D2 y prende.** Sale `CALIBRACION`.
2. Pon el robot encima de cada color y apunta los números:

| Color | r | g | b | c |
|---|---|---|---|---|
| Piso | | | | |
| Rojo | | | | |
| Verde | | | | |
| Azul | | | | |
| Amarillo | | | | |

3. En App Lab, abre `sketch.ino`, busca `refs[]` y escribe tus números en el mismo orden.
4. Dale **Run**. Vuelve a calibración y revisa que diga el color correcto.

# 5. Ajusta el movimiento

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

# 6. A jugar

1. **Mantén D2 por 2 s** (borra las pruebas).
2. Pon el robot en la **esquina de inicio**, mirando hacia adelante.
3. **Toque corto.** Va a la meta y regresa solo.
4. Regrésalo al inicio y **toque corto** otra vez: ahora va directo y más rápido.

::: {.nota}
Entre intentos del mismo laberinto **no borres**: así recuerda el camino.
:::

# 7. Si algo falla

| Pasa esto | Haz esto |
|---|---|
| No se mueve | ¿Le diste el toque a D2? |
| `PY` no sube | App Lab → **Run** |
| `SIN VL53L0X` | Revisa los cables de los sensores de distancia |
| `SIN SENSOR COLOR` | Revisa los cables del sensor de color |
| Gira al revés | Cambia OUT1-2 por OUT3-4 en el puente H |
| Un motor va al revés | Voltea sus 2 cables en el puente H |
| Se pierde | Mantén D2 por 2 s para borrar |
| Pantalla negra | Espera; si sigue, revisa la batería |
