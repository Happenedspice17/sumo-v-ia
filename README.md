# Robot de laberinto – Microcontroladores 2

> Guía de programación paso a paso para principiantes: [`docs/GUIA_PROGRAMACION.md`](docs/GUIA_PROGRAMACION.md)

Robot de 120 × 120 mm que resuelve un laberinto y cuenta marcas de color. La versión actual usa Arduino UNO Q (sketch para el STM32 y Python en Linux con cámara USB: mapa por colores y ruta corta). La iteración A anterior usa Arduino Nano / UNO R3 (ATmega328P) con flood-fill.

| Carpeta | Qué hay |
|---|---|
| [`uno_q/`](uno_q/) | Versión actual (iteración B) con Arduino UNO Q: `sketch/` (STM32), `python/` (cámara, mapa, ruta corta) y `assets/` (página web) |
| [`atmega328p/`](atmega328p/) | Iteración A anterior: código en C++ para Microchip Studio con Nano / UNO R3 y diagrama de conexiones |
| [`chasis/`](chasis/) | Modelo OpenSCAD, STL listos para imprimir y planos (`chasis.pdf`) |
| [`docs/`](docs/) | `manual_ensamble.pdf`, `bom.csv`, `uno_q.md` (documento técnico de la versión UNO Q) y `GUIA_PROGRAMACION.md` |
| `docs/pdf/` | `manual_tecnico.pdf` y `manual_uso.pdf`, generados desde `docs/manual_tecnico.md` y `docs/manual_uso.md` |
| `docs/historial_cambios.md` | Bitácora de cambios, problemas y soluciones desde la V1 |

Regenerar documentos: `python3 chasis/generar_pdf.py`, `python3 docs/generar_manuales.py` y `sh docs/md_pdf.sh` (PDF de los manuales en `docs/pdf/`).
