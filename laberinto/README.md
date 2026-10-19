# Robot laberinto – Arduino UNO Q

## Conexiones

| Componente | Pin | UNO Q |
|---|---|---|
| L298N ENA (quitar jumper) | PWM motor izq | D9 |
| L298N IN1 / IN2 | dirección izq | D4 / D5 |
| L298N ENB (quitar jumper) | PWM motor der | D10 |
| L298N IN3 / IN4 | dirección der | D7 / D8 |
| L298N 12V | batería + | LiPo 2S (7.4 V) |
| L298N GND | GND común | GND |
| Encoder izq (canal A) | | D2 |
| Encoder der (canal A) | | D3 |
| Encoders VCC / GND | | 3.3V / GND |
| TCS34725 SDA / SCL | I2C 0x29 | SDA / SCL |
| OLED SSD1306 SDA / SCL | I2C 0x3C | SDA / SCL |
| TCS34725 y OLED VCC | | 3.3V |
| Botón de arranque | a GND | D12 |
| Batería + | | VIN (7–24 V) |
| Cámara USB | hub USB‑C | USB‑C |

```
 LiPo 2S ─┬─► L298N 12V ──► motores N20 (OUT1-2 izq, OUT3-4 der)
          └─► UNO Q VIN
 GND común: batería, L298N, UNO Q, sensores

 UNO Q D9,D4,D5 ─► ENA,IN1,IN2      D2 ◄─ encoder izq
 UNO Q D10,D7,D8 ─► ENB,IN3,IN4     D3 ◄─ encoder der
 UNO Q SDA/SCL ──┬─ TCS34725 (abajo, a 3–5 mm del piso, LED encendido)
                 └─ OLED 128x64
 UNO Q D12 ── botón ── GND
 UNO Q USB‑C ── hub ── cámara (en el mástil, viendo hacia adelante/abajo)
```

No usar el regulador de 5 V del L298N para el UNO Q. Todos los pines del UNO Q son de 3.3 V; el L298N acepta esa lógica.

## Programación (Arduino App Lab)

1. Instala Arduino App Lab, conecta el UNO Q por USB‑C y crea una app nueva llamada `Laberinto`.
2. Copia `sketch/sketch.ino` y `python/main.py` en los archivos de la app y `python/requirements.txt` a la carpeta python.
3. En *Sketch libraries* agrega: `Adafruit SSD1306`, `Adafruit GFX Library`, `Adafruit TCS34725`.
4. Pulsa **Run**: App Lab compila y carga el sketch al MCU y arranca el Python en Linux.
5. Marca la app como predeterminada para que arranque sola al encender (en la competencia no hay PC).

## Calibración (en este orden)

1. **Colores**: enciende con el botón presionado. La OLED y la consola muestran `r g b c`. Pon el sensor sobre el piso y cada marca y copia los valores a `refs[]` en el sketch.
2. **Avance**: manda `mover 1` y ajusta `TICKS_CELDA` hasta que avance 18 cm. Igual con `TICKS_90` para giros. Si los motores no tienen encoder, pon `USE_ENC 0` y ajusta `MS_CELDA` / `MS_90`.
3. **Recto**: si se desvía, ajusta `KP`.
4. **Cámara**: al arrancar se guardan `/app/cal.jpg` y `/app/mask.jpg`. Ajusta `ROI`, `PARED_LO/HI` y `UMBRAL` en `main.py` hasta que los rectángulos salgan rojos donde hay pared.
5. **Laberinto**: ajusta `N`, `INICIO`, `RUMBO_INI` y `META` según las reglas del día.

## Funcionamiento

- Corrida 1: explora con flood‑fill hasta la meta y regresa al inicio explorando más.
- Corridas 2 y 3: va por la ruta más corta conocida, con rectas largas a velocidad alta.
- El mapa y las marcas se guardan en `/app/mapa.json`; sobreviven a apagarlo.
- Botón corto: siguiente corrida (pon el robot en el inicio, viendo en `RUMBO_INI`).
- Botón sostenido más de 2 s: borra mapa y conteo (laberinto nuevo).
- Una marca se cuenta solo si el color se sostiene 3 lecturas seguidas y antes se vio piso. Además, Python guarda la celda donde la vio y no vuelve a contar esa celda en ninguna corrida.
