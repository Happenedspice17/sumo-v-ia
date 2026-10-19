# Robot de laberinto – Microcontroladores 2

Robot de 125 × 125 mm que resuelve un laberinto y cuenta marcas de color. Hay dos iteraciones sobre el mismo chasis:

| Carpeta | Iteración | Qué hace |
|---|---|---|
| [`atmega328p/`](atmega328p/) | A · Arduino UNO R3 | Todo en el ATmega328P, sin cámara |
| [`uno_q/`](uno_q/) | B · Arduino UNO Q | STM32 + Linux con cámara |
| [`chasis/`](chasis/) | Ambas | Modelo OpenSCAD y planos en PDF |

Ambas usan 2 N20 sin encoder, L298N, 3 VL53L0X, TCS34725, OLED SSD1306, botón y LiPo 2S.

Planos: [`chasis/chasis.pdf`](chasis/chasis.pdf). Para regenerarlos: `python3 chasis/generar_pdf.py`.
