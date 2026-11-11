---
title: Manual de uso
subtitle: Robot de laberinto · UNO Q
author:
  - Manuel Harari López
  - Víctor Miguel Vázquez
  - Carlos Emiliano Escamilla Garibay
---

::: {.aviso}
**Lo más importante:** el robot **no se mueve solo**. Después de prenderlo, espera a que suba el número de `PY` en la pantalla y **dale un toque corto al botón D2**.
:::

# 1. Revisa antes de prender

- [ ] Batería cargada: **7.8 V o más**
- [ ] Ningún cable suelto
- [ ] Ruedas giran libres
- [ ] Sensores limpios
- [ ] Cámara y hub USB conectados, con el cargador del hub
- [ ] Robot en la esquina de inicio, mirando hacia adelante, y quieto
- [ ] Laberinto nuevo: borra el mapa antes de empezar (paso 3)

::: {.nota}
**¿Qué versión cargar?** Un sketch y un Python. Sketch: `sketch/` si tienes el MPU-6050 (también funciona sin él) o `sketch_sin_mpu/`. Python: `python/` (estable) o `python_experimental/` (la cámara además mide distancias y ve aberturas; para probar).
:::

# 2. Prende

1. Prende el switch **sin tocar el botón**.
2. Espera **20 segundos**. Si el MPU-6050 está conectado, el robot mide su giroscopio al arrancar: no lo muevas.
3. La pantalla muestra el estado y `PY` con un número que sube. **Ya está listo** cuando dice `LISTO`.

| Pantalla | Qué significa |
|---|---|
| Arriba: `LISTO` | Esperando. Lista para correr |
| `EXPLORA` | Corriendo y mapeando (primera vez) |
| `RAPIDO` | Corriendo por la ruta corta conocida |
| `META` | Encontró el amarillo y se detuvo |
| `BORRADO` | Mapa y conteo borrados |
| `SIN CAM` | No hay cámara. El robot sigue funcionando |
| Arriba, después del estado: `SENSA`, `DECIDE`, `GIRA`, `AVANZA`, `ESCANEA` | Fase actual de la corrida |
| Abajo: `PY n` | Si no sube, Python no corre. Si aparece `G`, el MPU-6050 está detectado |

La pantalla se actualiza solo con el robot quieto; durante el movimiento no cambia.

::: {.nota}
Si `PY` no sube: conecta la laptop, abre App Lab y dale **Run**.
:::

# 3. El botón D2

| Haz esto | Pasa esto |
|---|---|
| **Toque corto** | Arranca una corrida. Empieza siempre en la misma celda y viendo al mismo lado |
| **Otro toque corto** (mientras corre) | La detiene |
| **Mantener más de 2 s** y soltar | Borra el mapa y el conteo (laberinto nuevo) |
| **En la web: ▶ Iniciar / ■ Detener / Borrar mapa** | Lo mismo que el toque corto, otro toque y mantener 2 s, desde el celular |
| **Presionado al prender** | Modo prueba de sensores: la pantalla muestra `CALIBRACION` con r, g, b, color y distancias |

::: {.nota}
La primera corrida explora y mapea hasta encontrar el amarillo. Las siguientes van directo por la ruta corta si ya conocen la meta. Borra con D2 antes de cada laberinto nuevo.
:::

# 4. La página web: todo se calibra desde el celular

::: {.nota}
**La herramienta más útil del robot.** Desde la página web se calibran los colores y los sensores de distancia, se ve en vivo lo que mide cada sensor y qué decidiría el robot, se revisa la cámara y se sigue la corrida. Todo sin cables, sin reprogramar y sin copiar números a mano: lo calibrado se guarda en el robot y se carga solo en cada arranque.
:::

1. Prende el robot normal y espera a que suba `PY`.
2. En la laptop o el celular (en el mismo WiFi que la placa), abre **`http://<IP>:7000`**. La IP cambia según la red: App Lab la muestra al darle Run.

| En la página | Para qué |
|---|---|
| Corrida (arriba) | Iniciar, detener y borrar el mapa sin tocar el robot |
| Asistente de colores | Calibrar los 5 colores del piso (4.1) |
| Ver sensores ToF → Calibrar distancia | Calibrar los 3 sensores de distancia con el vernier (4.2) |
| Cámara → Calibrar cámara | Exposición, rumbo derecho, escala y (experimental) distancia (4.3) |
| Ver sensores ToF (dibujo) | Ver en vivo lo que mide cada sensor y qué haría el robot, sin moverlo |
| Cámara | Ver si el camino sale blanco (pared) o negro (sección 5) |
| Dónde está | Fase, celda, celdas mapeadas, meta y último avance durante la corrida |

## 4.1 Colores (una vez por pista)

1. Sigue el asistente: pon el robot **en el piso de la pista**, quieto, encima del color que te pide, y aprieta **Guardar**. Son 5: piso, rojo, verde, azul y amarillo. Cada botón promedia 5 lecturas.
4. Al final sale **¡Listo!**. Pasa el sensor por cada color y revisa que arriba diga el nombre correcto. Si uno falla, dale **◀ Atrás** y repítelo.

::: {.nota}
Se guarda solo y se queda aunque apagues. Recalibra solo si cambias de pista o de lugar (otra luz).
:::

## 4.2 Sensores de distancia (una vez, o si mueves un sensor)

1. Abre **Ver sensores ToF** y baja a **Calibrar distancia**. El robot quieto.
2. Pon algo plano y blanco (un trozo de pared) frente al sensor, a **100 mm** medidos con el vernier desde la cara del sensor.
3. Aprieta **Izq a 100 mm**, **Frente a 100 mm** o **Der a 100 mm**. Promedia 10 lecturas y corrige el desfase de ese sensor.
4. Abajo sale cada sensor: "a 100 mm leía X mm → corrige ±Y mm". El dibujo de arriba ya muestra la distancia corregida y, debajo, la lectura sin calibrar.

- [ ] Izquierdo a 100 mm
- [ ] Frontal a 100 mm
- [ ] Derecho a 100 mm

::: {.nota}
Si salió mal, solo repítelo: reemplaza la calibración anterior de ese sensor. **Borrar** la quita. Después de calibrar, revisa en el dibujo qué lee el robot centrado en una celda: los umbrales (`PARED`, `D_FRENTE`, `FRENTE_LIBRE`) se ajustaron con lecturas sin calibrar.
:::

## 4.3 Cámara (una vez, o si mueves la cámara)

1. Abre **Calibrar cámara**, abajo de la imagen.
2. **Exposición:** escribe un número y aprieta **Aplicar** hasta que el piso salga negro y las paredes blancas, sin manchas. Empieza en 100 (10 ms). 0 la deja automática.
3. **Derecho:** pon el robot derecho y centrado en un pasillo largo y aprieta **Está derecho**.
4. **Escala:** gíralo a mano **15° a la derecha** (con transportador) y aprieta **Fijar escala**. Al regresarlo derecho, abajo de la imagen debe decir "Rumbo: derecho" o 1-2°.
5. **Solo experimental:** pon el robot frente a una pared a 100, 200, 300, 400 y 600 mm y aprieta **Agregar punto** en cada una. El ToF frontal hace de regla, así que calíbralo antes (4.2).

- [ ] Exposición
- [ ] Derecho
- [ ] Escala (15°)
- [ ] Distancia (solo experimental)

::: {.nota}
La inclinación de la cámara no hay que medirla: estos pasos miden todo con el robot armado. Si mueves la cámara, repítelos.
:::

# 5. Revisa la cámara

En la página se ve lo que ve la cámara, con estas marcas:

- Camino **rojo**: ve blanco (pared) en el piso por donde va a pasar. El robot va lento.
- Camino **verde**: ve negro (piso libre). El robot va normal.
- Líneas **azules**: las bases de las 2 paredes y su punto de fuga. Si el punto queda a un lado de la línea blanca, el robot va chueco y lo corrige antes de avanzar.
- Puntos **amarillos** (solo experimental): dónde empieza la pared en 5 columnas; abajo dice a cuántos mm y si ve una abertura en la celda siguiente.

Con el robot en un pasillo libre, el camino tiene que salir **verde**. Si sale rojo, revisa primero la exposición (4.3); si sigue, ajusta `ZONA_PASO` (la parte del piso que mira) o sube `BLANCO_MAX` (cuánto blanco tolera antes de ir lento), en `python/main.py`.

Durante una corrida la página no consulta al robot: muestra la última lectura que tomó y su última foto.

# 6. Ajusta el movimiento

Calibra con la batería cargada. Cambia **un número a la vez** en `sketch/sketch.ino` (o en `python/main.py` si es de cámara), dale **Run** y prueba. Después de cada prueba, mantén D2 por 2 s para borrar.

Para ver por qué gira o avanza, usa **Ver sensores ToF** en la página: dibuja en vivo lo que mide cada sensor y qué haría el robot.

| Si el robot... | Cambia | Así |
|---|---|---|
| No llega a la siguiente celda (sin pared enfrente) | `MS_CELDA` | Súbelo 25 |
| Se pasa de la celda (sin pared enfrente) | `MS_CELDA` | Bájalo 25 |
| Gira poco (sin MPU-6050) | `MS_90` | Súbelo 10 |
| Gira de más (sin MPU-6050) | `MS_90` | Bájalo 10 |
| Gira de más o de menos (con MPU-6050) | `ADELANTO` | Si se pasa del giro, súbelo; si le falta, bájalo |
| Se queda antes del centro de la celda al abrirse un lado | `TRAS_SALTO` | Súbelo 5 |
| Se pasa del centro de la celda al abrirse un lado | `TRAS_SALTO` | Bájalo 5 |
| Se va a la derecha (sin MPU-6050) | `AJUSTE_DER` | Ponle 10 |
| Se va a la izquierda (sin MPU-6050) | `AJUSTE_DER` | Ponle -10 |
| Zigzaguea entre paredes | `KC` | Bájalo, por ejemplo a 0.5 |

::: {.nota}
Con MPU-6050 el robot sostiene el rumbo solo en recta, así que `AJUSTE_DER` casi no hace falta. Si se desvía, revisa primero `ADELANTO`.
:::

# 7. A jugar

1. **Mantén D2 por 2 s** y suelta (borra las pruebas).
2. Pon el robot en la **esquina de inicio**, mirando hacia adelante.
3. **Toque corto.** Explora hasta el amarillo y se detiene solo en `META`.
4. Regrésalo al inicio, en la misma posición, y dale **toque corto** otra vez: ahora va directo por la ruta corta (`RAPIDO`).

::: {.nota}
Entre intentos del mismo laberinto **no borres**: así recuerda el camino. Borra solo cuando cambies de laberinto.
:::

# 8. Si algo falla

| Pasa esto | Haz esto |
|---|---|
| No se mueve | ¿Le diste el toque corto a D2? La pantalla debe decir `LISTO` |
| Se pasa de la meta | Revisa la calibración del amarillo (paso 4). Si va por tiempo, baja `MS_CELDA` |
| Gira de más o de menos | Con MPU: `ADELANTO`. Sin MPU: `MS_90` (paso 6) |
| Gira al revés | Cambia OUT1-2 por OUT3-4 en el puente H |
| Un motor va al revés | Voltea sus 2 cables en el puente H |
| Siempre va lento | La cámara ve blanco en el camino. Revisa en la página si el camino sale rojo sobre piso negro; ajusta la exposición (4.3), `ZONA_PASO` o `BLANCO_MAX` |
| Antes de avanzar gira un poquito al lado equivocado | Repite "Está derecho" y "Fijar escala" (4.3) girándolo a la **derecha** |
| No para en el amarillo | Lo detecta el sensor de color, no la cámara. Recalibra el amarillo en la página (paso 4) |
| Un color sale mal | Repítelo en la página con **◀ Atrás** |
| `PY` no sube | App Lab → **Run** |
| `SIN VL53L0X` | Revisa los cables de los sensores de distancia |
| `SIN SENSOR COLOR` | Revisa los cables del sensor de color |
| `SIN CAM` en la pantalla | Revisa que el cargador del hub esté conectado y que la cámara esté en el hub. El robot funciona sin cámara, pero no revisa el piso |
| La cámara sale negra | Conecta cámara y hub **antes** de darle Run; el hub con su cargador |
| La página no abre | Mismo WiFi que la placa; usa la IP que muestra App Lab con `:7000` |
| Se pierde o el mapa está mal | Mantén D2 por 2 s para borrar y empieza de nuevo |
| Pantalla negra | Espera; si sigue, revisa la batería |
