# Robot de laberinto – Microcontroladores 2

Robot de 120 × 120 mm con Arduino Nano (ATmega328P) que resuelve un laberinto con flood-fill y cuenta marcas de color.

| Carpeta | Qué hay |
|---|---|
| [`atmega328p/`](atmega328p/) | Código en C++ para Microchip Studio y diagrama de conexiones |
| [`chasis/`](chasis/) | Modelo OpenSCAD, STL listos para imprimir y planos (`chasis.pdf`) |
| [`docs/`](docs/) | `manual_ensamble.pdf`, `manual_uso.pdf` y `bom.csv` |
| [`uno_q/`](uno_q/) | Versión anterior con Arduino UNO Q (descartada, sin mantenimiento) |

Regenerar documentos: `python3 chasis/generar_pdf.py` y `python3 docs/generar_manuales.py`.
