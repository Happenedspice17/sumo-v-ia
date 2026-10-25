# Iteración B – Arduino UNO Q (con cámara)

El STM32 mueve los motores, lee los sensores y maneja la OLED (`sketch/`). Linux corre Python con la cámara y resuelve el laberinto (`python/`). Se comunican por Bridge.

## Conexiones

| Componente | Pin del módulo | UNO Q |
|---|---|---|
| L298N | ENA (quitar jumper) | D9 |
| L298N | IN1 / IN2 | D4 / D5 |
| L298N | ENB (quitar jumper) | D10 |
| L298N | IN3 / IN4 | D7 / D8 |
| L298N | 12V / GND | Batería + / GND |
| VL53L0X izq / frente / der | XSHUT | A0 / A1 / A2 |
| VL53L0X ×3, TCS34725, OLED | SDA / SCL | SDA / SCL |
| VL53L0X ×3 (VCC), TCS34725 (VIN), OLED | VCC / GND | 3.3V / GND |
| TCS34725 (morado) | LED / INT | sin conectar (LED siempre encendido) |
| Botón de arranque | a GND | D12 |
| Batería 2S 18650 (conector T) | + | interruptor → VIN |
| Cámara USB | | hub USB‑C |

5V, GND, SDA y SCL se reparten en la mini protoboard de 170 puntos del piso 3: columnas 1, 4, 7 y 10, cada una con un puente entre sus dos mitades.

GND común entre todo. No alimentes el UNO Q con el regulador de 5 V del L298N. La posición física de cada pieza está en `../chasis/chasis.pdf`.

## Programación (Arduino App Lab)

1. Crea una app nueva llamada `Laberinto`.
2. Copia `sketch/sketch.ino`, `python/main.py` y `python/requirements.txt` a la app.
3. En las librerías del sketch agrega `Adafruit SSD1306`, `Adafruit GFX Library`, `Adafruit TCS34725` y `VL53L0X` (de Pololu).
4. Pulsa **Run**. App Lab carga el sketch al STM32 y arranca el Python.
5. Marca la app para que arranque sola al encender.

## Calibración

1. **Sensores**: enciende con el botón presionado. La OLED muestra `r g b c`, el color detectado y las 3 distancias. Pon el sensor de color sobre el piso y sobre cada marca y copia los valores a `refs[]`. Centra el robot en una celda y anota `D_LADO` y `D_FRENTE`.
2. **Avance**: ajusta `MS_CELDA` hasta que avance 18 cm en un pasillo sin pared enfrente, y `MS_90` para giros de 90°. `MS_RAPIDA` se ajusta igual, en rectas de varias celdas. Calibra con la batería cargada. Si se desvía, ajusta `AJUSTE_DER`.
3. **Cámara**: al arrancar se guardan `/app/cal.jpg` y `/app/mask.jpg`. Ajusta `ROI`, `PARED_LO/HI` y `UMBRAL` en `main.py` hasta que los rectángulos salgan rojos donde hay pared en la celda siguiente.
4. **Laberinto**: ajusta `N`, `INICIO`, `RUMBO_INI` y `META` según las reglas del día.

## Funcionamiento

- Los VL53L0X leen las paredes de la celda actual, mantienen el robot centrado y lo detienen a `D_FRENTE` cuando hay pared enfrente.
- La cámara mira la celda siguiente y adelanta sus paredes al mapa como tentativas, para que el flood‑fill descarte callejones antes de entrar. Si la cámara se equivoca y bloquea todo, el robot ignora esas paredes tentativas. Sin cámara, funciona solo con los VL53L0X (OLED: `SIN CAM`).
- Sin ruta conocida, explora hasta la meta y regresa solo al inicio. No lo recojas hasta que la OLED diga `LISTO`.
- Con ruta conocida, va directo a la meta con rectas largas a velocidad alta.
- Botón corto: siguiente corrida (pon el robot en el inicio, viendo hacia `RUMBO_INI`).
- Botón sostenido más de 2 s: borra mapa y conteo (laberinto nuevo).
- Una marca se cuenta solo si el color se sostiene 3 lecturas y antes se vio piso. Además se guarda la celda y no se vuelve a contar.
