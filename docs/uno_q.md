# Robot de laberinto: Arduino UNO Q

Documento técnico del plan para la competencia (en 15 días desde 2026-10-29). Lo marcado en **Pendientes** se resuelve antes de cablear.

## 1. Plan

| Rol | Placa | Estado |
|---|---|---|
| Principal (experimental) | Arduino UNO Q | Se prueba primero |
| Respaldo oficial | Arduino UNO R3 (ATmega328P) | Firmware bare-metal ya en `atmega328p/` |

Mismo chasis, mismas piezas impresas y misma huella. El Q solo agrega:

- Pedestal impreso de 20 × 20 × 75 mm (inserto M4 abajo, M4 desde el piso 2).
- Cabeza impresa: cámara al frente, OLED atrás en rieles.
- Repisa y hub USB-C con entrada de alimentación.
- Panel web de calibración en el puerto 7000.

## 2. Hardware

### UNO Q

- **MPU:** Qualcomm QRB2210, corre Debian Linux.
- **MCU:** STM32U585, corre sketches de Arduino.
- Ambos se comunican por un enlace interno que administra el servicio `arduino-router` en Linux, con MessagePack RPC.
- Montaje: la placa va vertical, sujeta con cinchos al chasis, para conservar los 12 cm y que el adaptador OTG quede dentro del contorno del robot.

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
| MCU (sketch) | Motores (L298N), 3× VL53L0X, TCS34725, OLED, botón, MPU-6050 opcional. Expone `mover(mm, lento)`, `odo(i)` y `set_ref`; Python los llama con `Bridge.call`. |
| Linux (Python) | Cámara USB, OpenCV, mapa, ruta más corta, guarda el mapa entre corridas. |

## 4. Estrategia de corridas

| Corrida | Qué hace |
|---|---|
| 1 | Explora y arma el mapa: paredes por celda y colores. Se guarda en `/app/datos/mapa.json`. |
| 2 y siguientes | Si ya conoce la meta (amarillo), va por el camino más corto conocido (BFS, OLED `RAPIDO`). Si algo no cuadra, sigue explorando desde ahí. |

Funciona sin cámara: el R3 puede hacerlo solo. Un mapa de 16×16 ocupa ~512 bytes de los 2 KB de RAM.

## 5. Cámara

- Cámara innomaker U20CAM-9281M (OV9281, 1 MP monocromática, obturador global, hasta 720p a 120 fps, lente M12 gran angular). Es UVC: Linux la ve sin driver. Las medidas de la placa están por confirmar (el CAD aún usa 32×32 mm, agujeros M2 a 28 mm).
- No es MIPI-CSI porque el Q necesita la Media Carrier board (más grande, 1.8 V) para usar CSI.

Qué hace hoy (no calcula paredes por cámara):

- Es monocromática: no busca el amarillo (lo detecta el TCS34725). Solo mide cuánto blanco (pared) hay en el piso por donde va a pasar.
- Revisa el piso del camino (`ZONA_PASO`): blanco (gris ≥ `BLANCO_MIN`) = pared, negro = libre. Con blanco el robot va lento y el frontal hace el doble check.
- No ve el laberinto completo de antemano: las paredes bloquean la vista.
- Geometría actual:

| Parámetro | Valor |
|---|---|
| Altura del lente | 162 mm (placa 12 mm arriba de la manga para dejar libre la parte de atrás) |
| Inclinación | 40° hacia abajo |
| Campo de visión | ~100° × 75° |
| Ve el piso desde | ~3 cm adelante |

Montaje: marco de 33 × 33 mm, 4 M2 a 28 mm con ±1 mm de juego y tuerca atrás, hueco para el conector USB arriba a la izquierda (visto por atrás) y paso de cables de alimentación abajo al centro.

La Q busca la cámara de `/dev/video0` a `video11`; `video0` y `video1` son internos de la placa. `ZONA_PASO`, `BLANCO_MIN` y `BLANCO_MAX` se ajustan viendo la imagen en el panel web.

## 6. Sensor de color (TCS34725)

Sigue siendo necesario: lee el color exacto bajo el robot con su propio LED. La cámara no lo reemplaza.

### Calibración

Geometría fija dentro de la capucha, LED encendido.

1. **Blanco:** sin saturación (ATIME 24 ms, cuenta máxima 10240).
2. **Oscuridad:** offset con negro mate.
3. **Balance de blancos:** ganancias para que el blanco dé R = G = B.
4. **Colores:** en el panel web (`http://<ip>:7000`), un asistente pide cada color; promedia 5 lecturas y guarda en `/app/datos/colores.json`. Python lo manda al MCU en cada arranque.
5. **En la sede:** repetir el asistente sobre la pista real.

Clasificación: referencia más cercana en RGB normalizado + brillo. `refs[]` del sketch solo son los valores por defecto.

## 7. Energía

- **Batería:** 2S, 6.0–8.4 V. Referencia de recarga: 7.2 V.
- **Q:** VIN acepta 7–24 V. USB-C: 5 V / 3 A.
- **Consumo:** Q + cámara + hub ≈ 10 W en el peor caso ≈ 1.5 A desde la batería.
- Con la batería por debajo de 7 V, VIN queda fuera de rango. Por eso la ruta recomendada usa un módulo PD (entrada desde 6 V).

### Problema del USB-C con VIN

Al alimentar por VIN, el puerto USB-C puede arrancar en modo dispositivo y no ver la cámara. Arduino lo marca como no soportado.

- **Workaround comunitario:** forzar modo host por debugfs: https://github.com/Psalmustrack/arduino-uno-q-usb-fix
- **Método oficial:** hub con entrada PD que alimenta el Q.

Con la Q alimentada por VIN, su USB-C no da 5 V al hub: el hub debe recibir energía por su puerto PD (cargador PD; 5 V ≥ 3 A del regulador del robot a un cable USB-C cortado conectado al puerto PD del hub; o módulo DC-DC con salida USB-C PD desde la batería). Alimentar solo la cámara con 5 V externos no basta.

En la práctica (pruebas en pista del equipo) el UNO Q no siempre reconocía la cámara aunque tuviera 5 V y estuviera conectada; se resolvió con un adaptador OTG "tonto" de USB-C a USB-A.

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
| MPU-6050 (opcional, GY-521) | Mismo bus I2C, dirección 0x68 (AD0 a GND o suelto); VCC a 3V3 |
| Alimentación | VIN, GND |

## 10. Cambio de placa R3 ↔ Q

1. Retirar el Proto Shield con todos los dupont.
2. Quitar los 4 tornillos M3×8.
3. Cambiar la placa.
4. Volver a colocar el shield.
5. Mover el puente de VCC: **3V3** para Q, **5V** para R3.
6. En Q: montar pedestal, cabeza, repisa y hub.

## 11. Ruedas

Parámetros CAD actuales: `D_RUEDA` = 45 mm, `A_RUEDA` = 17 mm.

- Medidas reales del kit; el pozo del piso 1 se calcula de `D_RUEDA` y `MOT_H`.
- El ancho cuenta para el límite de 120 mm.
- Al cambiar la rueda: recalibrar `T_CELDA` y `T_90`.

## 12. Pruebas de alimentación

### Test 1: sin PD (en casa, hub UGREEN)

Nota: en la práctica se resolvió con un adaptador OTG "tonto" USB-C a USB-A (ver sección 7).

1. Q alimentado por VIN desde la batería. Hub sin alimentar. Cámara conectada al hub.
2. Ejecutar `lsusb` y `v4l2-ctl --list-devices`.
3. Si la cámara no aparece: medir ≥ 4.8 V en el hub; revisar `adb shell lsusb` y `adb shell ls /dev/video*`; reconectar el hub; revisar soldaduras; cargar la batería. Si sigue, probar el workaround de modo host.
4. Si el hub tiene entrada PD: probar con su cargador.

| Paso | Resultado |
|---|---|
| 1–2 | Pendiente |
| 3 | Pendiente |
| 4 | Pendiente |

## 13. Pendientes

| # | Pendiente | Qué decide | Estado |
|---|---|---|---|
| 1 | Mástil | Pedestal impreso 20 × 20 con inserto M4 | Resuelto |
| 2 | Altura de la pared | Ajuste de `ZONA_PASO` (lente a 162 mm) | En la sede |
| 3 | Rueda real: diámetro y ancho | `D_RUEDA`, `A_RUEDA`, pozo, límite de 120 mm, `T_CELDA`, `T_90` | Pendiente |
| 4 | Referencia y dimensiones del hub | Repisa y espacio. Candidato: Arduino USB-C Hub 8-in-1 (https://www.robotshop.com/products/arduino-usb-c-hub-8in-1-for-uno-q) | Pendiente |
| 5 | Resultado del test sin PD | Si se compra el módulo PD | Pendiente |
| 6 | Posición exacta del USB-C del UNO Q | Repisa, mástil y cable | Medir |
| 7 | Alinear `uno_q/README.md` con el mapa de pines de la sección 9 | Ya coinciden | Resuelto |
| 8 | Conseguir MPU-6050 (GY-521) | Giros por ángulo (`ADELANTO`, `KG`) en lugar de solo por tiempo (`MS_90`). Sin él el robot gira por tiempo | Pendiente |

## 14. Fuentes

- Datasheet ABX00162 / ABX00173: https://694757fbdf180503949db099--docs-content.netlify.app/resources/datasheets/ABX00162-ABX00173-datasheet.pdf
- Foro: USB desactivado con VIN: https://forum.arduino.cc/t/usb-power-disabled-if-using-vin-power-pin/1411831
- Foro: cámara USB en UNO Q: https://forum.arduino.cc/t/connecting-usb-camera-to-uno-q/1412062
- arduino-router: https://github.com/arduino/arduino-router
- Foro: transferencia bidireccional MCU–MPU vía Router Bridge: https://forum.arduino.cc/t/uno-q-overview-of-bidirectional-data-transfer-between-mcu-and-mpu-via-router-bridge/1446178
- Hub: https://www.robotshop.com/products/arduino-usb-c-hub-8in-1-for-uno-q
- Workaround de modo host: https://github.com/Psalmustrack/arduino-uno-q-usb-fix
