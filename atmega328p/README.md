# Robot de laberinto – Arduino Nano (ATmega328P)

Firmware en C++ sin librerías de Arduino, para Microchip Studio 7. Maneja los periféricos por registros:

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

## Conexiones

![Diagrama de conexiones](img/conexiones_nano.png)

| Componente | Pin del módulo | Nano |
|---|---|---|
| L298N | ENA / ENB (quitar jumpers) | D5 / D6 |
| L298N | IN1 / IN2 / IN3 / IN4 | D7 / D8 / D9 / D10 |
| L298N | 12V / GND | Batería + (tras el interruptor) / GND |
| VL53L0X izq / frente / der | XSHUT | A0 / A1 / A2 |
| VL53L0X ×3, TCS34725, OLED | SDA / SCL | A4 / A5 |
| VL53L0X ×3 (VCC), TCS34725 (VIN), OLED | VCC / GND | 5V / GND |
| TCS34725 | LED / INT | sin conectar (LED siempre encendido) |
| Botón de arranque | a GND | D2 |
| Batería 2S | + | interruptor → VIN |

El Nano va en una mini protoboard; la otra es el bus I2C: columnas 1 (5V), 4 (GND), 7 (SDA) y 10 (SCL), cada una con un puente entre sus dos mitades.

## Programar con Microchip Studio

1. File → New → Project → **GCC C++ Executable Project**, dispositivo **ATmega328P**.
2. Borra el `main.cpp` generado y agrega (Add → Existing Item) todos los `.cpp` y `.h` de `laberinto/`.
3. Configuración **Release** y Build (F7).
4. Carga con avrdude como herramienta externa (Tools → External Tools):

```
-C "<ruta>\etc\avrdude.conf" -p atmega328p -c arduino -P COM5 -b 115200 -U flash:w:"$(TargetDir)$(TargetName).hex":i
```

Con bootloader viejo usa `-b 57600`. Fuera de Windows: `make` y `make cargar PUERTO=/dev/ttyUSB0`.

El paso a paso completo está en `docs/manual_uso.pdf`.

## Funcionamiento

- Mapa en EEPROM: 1 byte por celda (paredes, visitada, color de marca). Sobrevive a apagarlo.
- Sin ruta conocida explora hasta la meta y regresa; con ruta conocida va directo rápido.
- Botón corto: siguiente corrida. Sostenido más de 2 s: borra. Encender con el botón presionado: calibración (corto avanza una celda, largo gira 90°).
- Cada marca se cuenta una sola vez por celda.
