# Robot de laberinto – Arduino UNO R3 (ATmega328P)

Firmware en C++ sin librerías de Arduino, para Microchip Studio 7 o `make`. Maneja los periféricos por registros:

| Archivo | Qué hace |
|---|---|
| `config.h` | Pines, laberinto y **todos los valores de calibración** |
| `main.cpp` | Flood-fill, movimiento, conteo de colores, OLED, botón |
| `twi.cpp` | I2C maestro por registros (TWBR, TWCR, TWSR), 400 kHz |
| `tiempo.cpp` | Timer1 en CTC a 1 kHz por interrupción: `ms()` y tick de 10 ms |
| `motores.cpp` | Timer0 Fast PWM en OC0A/OC0B (D6/D5) + dirección del L298N |
| `oled.cpp` | SSD1306 por I2C, texto 5×7 |
| `tcs.cpp` | TCS34725 por registros |
| `VL53L0X.cpp` | Librería de Pololu (MIT) adaptada a `twi.cpp` y `ms()` |

Uso: 13.8 KB de flash (42%) y 1.0 KB de RAM (50%).

## Alimentación

- Batería 2S (7.4 V nominal) → interruptor → **VIN** del UNO R3.
- VIN necesita al menos 7 V: recarga la batería al llegar a **7.2 V**.

## Bus I2C

- El bus va en una mini protoboard con cuatro columnas, contando desde adelante: **1 VCC, 4 GND, 7 SDA, 10 SCL**. Cada columna tiene un puente entre sus dos mitades.
- El jumper VCC del proto shield va en **5V** con el UNO R3.
- **Aviso:** con el UNO Q el jumper debe ir en **3V3**; a 5 V se dañan sus pines I2C.

## Cableado

Diagrama de la versión Nano (los pines son los mismos):

![Diagrama de conexiones](img/conexiones_nano.png)

| Componente | Pin del módulo | UNO R3 |
|---|---|---|
| L298N | ENA / ENB (quitar jumpers) | D5 / D6 |
| L298N | IN1 / IN2 / IN3 / IN4 | D7 / D8 / D9 / D10 |
| L298N | 12V / GND | Batería + (tras el interruptor) / GND |
| VL53L0X izq / frente / der | XSHUT | A0 / A1 / A2 |
| VL53L0X ×3, TCS34725, OLED | SDA / SCL | A4 / A5 (cabecera junto a AREF) |
| VL53L0X ×3 (VCC), TCS34725 (VIN), OLED | VCC / GND | 5V / GND |
| TCS34725 | LED / INT | sin conectar (LED siempre encendido) |
| Botón de arranque | a GND | D2 |
| Batería 2S | + | interruptor → VIN |

## Cambio R3 ↔ UNO Q

1. Desconecta todos los dupont y retira el proto shield.
2. Desatornilla los 4 tornillos M3×8 y cambia la placa.
3. Vuelve a montar el proto shield y reconecta los dupont según la tabla.
4. Mueve el jumper VCC del bus: **5V** para el R3, **3V3** para el UNO Q.

## Programar con Microchip Studio

1. File → New → Project → **GCC C++ Executable Project**, dispositivo **ATmega328P**.
2. Borra el `main.cpp` generado y agrega (Add → Existing Item) todos los `.cpp` y `.h` de `laberinto/`.
3. Configuración **Release** y Build (F7).
4. Carga con avrdude como herramienta externa (Tools → External Tools):

```
-C "<ruta>\etc\avrdude.conf" -p m328p -c arduino -P COM5 -b 115200 -U flash:w:"$(TargetDir)$(TargetName).hex":i
```

Fuera de Windows, desde `laberinto/`:

```
make
make cargar PUERTO=/dev/ttyACM0
```

o directamente: `avrdude -c arduino -p m328p -P /dev/ttyACM0 -b 115200 -U flash:w:laberinto.hex`

Nano con bootloader viejo: usa `-b 57600` (o `make cargar BAUD=57600`).

El paso a paso completo está en `docs/manual_uso.pdf`.

## Funcionamiento

- Mapa en EEPROM: 1 byte por celda (paredes, visitada, color de marca). Sobrevive a apagarlo.
- Sin ruta conocida explora hasta la meta y regresa; con ruta conocida va directo rápido.
- Botón corto: siguiente corrida. Sostenido más de 2 s: borra. Encender con el botón presionado: calibración (corto avanza una celda, largo gira 90°).
- Cada marca se cuenta una sola vez por celda.
