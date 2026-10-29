# Robot de laberinto: Arduino UNO Q

Documento técnico del plan para la competencia (en 15 días desde 2026-10-29). Lo marcado en **Pendientes** se resuelve antes de cablear.

## 1. Plan

| Rol | Placa | Estado |
|---|---|---|
| Principal (experimental) | Arduino UNO Q | Se prueba primero |
| Respaldo oficial | Arduino UNO R3 (ATmega328P) | Firmware bare-metal ya en `atmega328p/` |

Mismo chasis, mismas piezas impresas y misma huella. El Q solo agrega:

- Mástil (PTR de 10 o 15 mm, tamaño pendiente).
- Cabeza con cámara USB.
- Repisa y hub USB.
- OLED movida a la parte trasera del mástil.

## 2. Hardware

### UNO Q

- **MPU:** Qualcomm QRB2210, corre Debian Linux.
- **MCU:** STM32U585, corre sketches de Arduino.
- Ambos se comunican por un enlace interno que administra el servicio `arduino-router` en Linux, con MessagePack RPC.

### R3 frente a Q

| Aspecto | UNO R3 | UNO Q |
|---|---|---|
| Procesador | ATmega328P | QRB2210 (Linux) + STM32U585 (sketches) |
| Lógica I/O | 5 V | 3.3 V |
| Reguladores | Lineales (VIN → 5 V → 3.3 V) | Conmutados |
| Visión | No | Cámara USB + OpenCV en Linux |

### Programación (Arduino App Lab)

Una **App** tiene:

1. Sketch `.ino` para el MCU (librería `Arduino_RouterBridge`).
2. Programa Python en Linux.
3. **Bricks** (opcional).

## 3. Comunicación MCU ↔ Linux (Bridge)

| Función | Uso |
|---|---|
| `Bridge.provide("nombre", fn)` | Expone una función para que la otra parte la llame |
| `Bridge.call("nombre", args)` | Llama a una función y recibe un valor |
| `Bridge.notify(...)` | Aviso sin respuesta (en ambos sentidos) |

Reparto propuesto:

| Lado | Responsabilidad |
|---|---|
| MCU (sketch) | Motores (L298N), 3× VL53L0X, TCS34725, OLED, botón. Expone `avanza(n)`, `gira(dir)`, `lee_sensores()`. Notifica `color` y `pared`. |
| Linux (Python) | Cámara USB, OpenCV, mapa, ruta más corta, guarda el mapa entre corridas. |

## 4. Estrategia de corridas

| Corrida | Qué hace |
|---|---|
| 1 | Explora y arma el mapa: paredes por celda + color. |
| 2 | Calcula la ruta más corta (flood fill o BFS) y corre rápido. |

Funciona sin cámara: el R3 puede hacerlo solo. Un mapa de 16×16 ocupa ~512 bytes de los 2 KB de RAM.

## 5. Cámara

- Cámara USB UVC de 32×32 mm, lente gran angular M12, agujeros M2 a 28 mm.
- No es MIPI-CSI porque el Q necesita la Media Carrier board (más grande, 1.8 V) para usar CSI.

Qué aporta:

- No ve el laberinto completo de antemano: las paredes bloquean la vista.
- Ve 2–3 celdas adelante. Acelera la exploración y anticipa colores.
- La cámara anticipa; el TCS34725 confirma.

Geometría actual:

| Parámetro | Valor |
|---|---|
| Altura del lente | 150 mm |
| Inclinación | 25° hacia abajo |
| Campo de visión | ~100° × 75° |
| Ve el piso desde | ~3 cm adelante |

Pendiente: altura de la pared. Decide la altura de la cámara.

## 6. Sensor de color (TCS34725)

Sigue siendo necesario: lee el color exacto bajo el robot con su propio LED. La cámara no lo reemplaza.

### Calibración

Geometría fija dentro de la capucha, LED encendido.

1. **Blanco:** sin saturación (ATIME 24 ms, cuenta máxima 10240).
2. **Oscuridad:** offset con negro mate.
3. **Balance de blancos:** ganancias para que el blanco dé R = G = B.
4. **Colores:** enseñar cada loseta real con ~30 lecturas promediadas y guardar en EEPROM.
5. **En la sede:** recalibrar con el modo calibración (encender con el botón presionado).

Clasificación: referencia más cercana en RGB normalizado + brillo. Ya está en el firmware. Los valores de `config.h` son placeholders.

## 7. Energía

- **Batería:** 2S, 6.0–8.4 V. Referencia de recarga: 7.2 V.
- **Q:** VIN acepta 7–24 V. USB-C: 5 V / 3 A.
- **Consumo:** Q + cámara + hub ≈ 10 W en el peor caso ≈ 1.5 A desde la batería.
- Con la batería por debajo de 7 V, VIN queda fuera de rango. Por eso la ruta recomendada usa un módulo PD (entrada desde 6 V).

### Problema del USB-C con VIN

Al alimentar por VIN, el puerto USB-C puede arrancar en modo dispositivo y no ver la cámara. Arduino lo marca como no soportado.

- **Workaround comunitario:** forzar modo host por debugfs: https://github.com/Psalmustrack/arduino-uno-q-usb-fix
- **Método oficial:** hub con entrada PD que alimenta el Q.

### Ruta PD en el robot

Batería → interruptor → fusible de 3 A → módulo DC-DC con salida USB-C PD SOURCE (entrada desde 6 V o menos, salida 5 V / 3 A) → Q.

| Módulo | Entrada | Enlace |
|---|---|---|
| JUZITAO 60 W 6–35 V a USB-C PD 3.0 (Amazon MX) | 6–35 V | https://www.amazon.com.mx/JUZITAO-unidades-alimentaci%C3%B3n-reductor-adaptador/dp/B0CDPR4MKZ |
| Módulo de carga rápida tipo C 20 W PPS 3.0 (Mercado Libre) | 6–32 V | https://www.mercadolibre.com.mx/modulo-de-carga-rapida-tipo-c-20w-pps-30-board-dc/p/MLM2001545654 |
| Placas SW3518 | 6–32 V | — |

**No comprar:**

- Módulos "trigger", "decoy" o "señuelo": son sumideros (consumen), no fuentes.
- Módulos que requieren 8 V o más de entrada (ej. PD65W 8–30 V).

## 8. Voltajes y bus I2C

| Placa | VCC del bus | Motivo |
|---|---|---|
| UNO Q | 3V3 | Sus pines son de 3.3 V. Algunos módulos suben SDA/SCL a su VCC: con 5 V dañarían los pines del Q. |
| UNO R3 | 5V | Lógica de 5 V. |

- Diferencia de energía: ~100 mA de sensores = 0.33 W a 3.3 V frente a 0.5 W a 5 V. Despreciable.
- El L298N acepta 3.3 V como nivel alto.
- Bus en la mini protoboard: columnas VCC, GND, SDA, SCL.

## 9. Mapa de pines (idéntico en ambas placas)

| Señal | Pin |
|---|---|
| ENA | D5 |
| ENB | D6 |
| IN1–IN4 | D7–D10 |
| Botón | D2 |
| XSHUT izq / frente / der | A0 / A1 / A2 |
| I2C | SDA / SCL (header junto a AREF) |
| Alimentación | VIN, GND |

## 10. Cambio de placa R3 ↔ Q

1. Retirar el Proto Shield con todos los dupont.
2. Quitar los 4 tornillos M3×8.
3. Cambiar la placa.
4. Volver a colocar el shield.
5. Mover el puente de VCC: **3V3** para Q, **5V** para R3.
6. En Q: montar mástil, repisa y hub.

## 11. Ruedas

Parámetros CAD actuales: `D_RUEDA` = 34 mm, `A_RUEDA` = 20 mm.

- Diámetro mayor de 38 mm: requiere un pozo de rueda más grande.
- El ancho cuenta para el límite de 120 mm.
- Al cambiar la rueda: recalibrar `T_CELDA` y `T_90`.

## 12. Pruebas de alimentación

### Test 1: sin PD (en casa, hub UGREEN)

1. Q alimentado por VIN desde la batería. Hub sin alimentar. Cámara conectada al hub.
2. Ejecutar `lsusb` y `v4l2-ctl --list-devices`.
3. Si la cámara no aparece: probar el workaround de modo host.
4. Si el hub tiene entrada PD: probar con su cargador.

| Paso | Resultado |
|---|---|
| 1–2 | Pendiente |
| 3 | Pendiente |
| 4 | Pendiente |

## 13. Pendientes

| # | Pendiente | Qué decide | Estado |
|---|---|---|---|
| 1 | Tamaño del PTR (10 o 15 mm) | Mástil | Pendiente |
| 2 | Altura de la pared | Altura de la cámara (lente hoy a 150 mm) | Pendiente |
| 3 | Rueda real: diámetro y ancho | `D_RUEDA`, `A_RUEDA`, pozo, límite de 120 mm, `T_CELDA`, `T_90` | Pendiente |
| 4 | Referencia y dimensiones del hub | Repisa y espacio. Candidato: Arduino USB-C Hub 8-in-1 (https://www.robotshop.com/products/arduino-usb-c-hub-8in-1-for-uno-q) | Pendiente |
| 5 | Resultado del test sin PD | Si se compra el módulo PD | Pendiente |
| 6 | Posición exacta del USB-C del UNO Q | Repisa, mástil y cable | Medir |
| 7 | Alinear `uno_q/README.md` con el mapa de pines de la sección 9 | Su tabla (ENA D9, ENB D10, IN D4/D5/D7/D8, botón D12) no coincide. Evita errores al cablear. | Pendiente |

## 14. Fuentes

- Datasheet ABX00162 / ABX00173: https://694757fbdf180503949db099--docs-content.netlify.app/resources/datasheets/ABX00162-ABX00173-datasheet.pdf
- Foro: USB desactivado con VIN: https://forum.arduino.cc/t/usb-power-disabled-if-using-vin-power-pin/1411831
- Foro: cámara USB en UNO Q: https://forum.arduino.cc/t/connecting-usb-camera-to-uno-q/1412062
- arduino-router: https://github.com/arduino/arduino-router
- Foro: transferencia bidireccional MCU–MPU vía Router Bridge: https://forum.arduino.cc/t/uno-q-overview-of-bidirectional-data-transfer-between-mcu-and-mpu-via-router-bridge/1446178
- Hub: https://www.robotshop.com/products/arduino-usb-c-hub-8in-1-for-uno-q
- Workaround de modo host: https://github.com/Psalmustrack/arduino-uno-q-usb-fix
