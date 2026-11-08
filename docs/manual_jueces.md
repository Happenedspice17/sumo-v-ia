# Robot de laberinto: descripción técnica

Microcontroladores 2 · Plataforma principal: Arduino UNO Q · Respaldo: Arduino UNO R3 (ATmega328P, bare-metal)

## 1. Planteamiento

Robot autónomo diferencial para un laberinto de 16 × 16 celdas de 180 mm. Debe llegar a la meta (2 × 2 celdas centrales), regresar al origen y contar marcas de color en el piso. La estrategia es en dos fases: exploración con *flood fill* y, con el mapa persistido, corrida rápida restringida a celdas visitadas.

## 2. Arquitectura de cómputo

El UNO Q integra dos procesadores con particiones de responsabilidad estrictas:

| Dominio | Procesador | SO | Responsabilidad |
|---|---|---|---|
| Tiempo real | STM32U585 (Cortex-M33) | Zephyr (sketch Arduino) | Lazo de control de motores, adquisición de sensores, clasificación de color, HMI (OLED, botón) |
| Planeación | Qualcomm QRB2210 (Cortex-A53) | Debian Linux | Mapa, *flood fill*, selección de trayectoria, persistencia, visión (OpenCV) |

**Enlace:** RPC MessagePack sobre el enlace interno MCU–MPU, enrutado por el servicio `arduino-router`. El MCU expone procedimientos y Linux los invoca por *polling*:

| Procedimiento | Semántica |
|---|---|
| `mover(n, rápido)` | Encola avance de *n* celdas; no bloqueante, devuelve 0 si hay movimiento en curso |
| `girar(k)` | Giro en sitio de *k* × 90° (signo = sentido) |
| `ocupado()` | 1 mientras hay un movimiento activo |
| `paredes()` | Máscara de 3 bits (izq, frente, der) por umbral sobre los ToF |
| `color()` | Último evento de color codificado como `c + 16·k` (clase *c*, desplazamiento *k* celdas desde el origen del movimiento) |
| `arranque()` | Evento del botón: 1 corto, 2 largo (> 2 s) |
| `set_cuenta`, `set_estado` | Actualización de la HMI |

El reparto aísla la latencia no determinista de Linux (planificador, E/S, visión) del lazo de control: si Python se retrasa, el MCU completa el movimiento en curso y frena; nunca queda un actuador sin supervisión.

El firmware de respaldo para UNO R3 implementa el mismo comportamiento en un único ATmega328P, sin Arduino core: drivers propios de TWI, base de tiempo con Timer1 en CTC, PWM rápido de 8 bits por registros en Timer0 y el mismo *flood fill*.

## 3. Sensado

### 3.1 Distancia: 3 × VL53L0X (ToF, 940 nm)

- Orientación: izquierda, frente, derecha.
- Los tres comparten la dirección I²C por defecto (0x29, que además coincide con el TCS34725). Al arranque se mantienen en *reset* con XSHUT (A0–A2) y se liberan uno a uno, reasignándolos a 0x30–0x32 antes de `init()`.
- Modo continuo, *timing budget* de 20 ms (≈ 50 Hz por sensor). La lectura es no bloqueante: se consulta `RESULT_INTERRUPT_STATUS` y solo se lee el sensor con dato nuevo.
- Lecturas de 0 o > 2000 mm se tratan como fuera de rango.
- Pared ⇔ *d* < 120 mm (`PARED`).

### 3.2 Color: TCS34725

- Integración de 24 ms, ganancia 4×, con iluminación propia (LED del módulo) dentro de una capucha impresa que fija la geometría sensor–piso y bloquea la luz ambiente.
- Los registros se leen directamente, sin esperar el fin de integración, para no bloquear el lazo.
- **Clasificación:** vecino más cercano en el espacio de cromaticidad normalizada más un término de luminancia logarítmica:

  *r̂ = R/(R+G+B)*, igual para *ĝ* y *b̂*

  *d_i = (r̂ − r_i)² + (ĝ − g_i)² + (b̂ − b_i)² + 0.01 · ln²((C+1)/(C_i+1))*

  Si min *d_i* > 0.02 se clasifica como piso. La normalización da invariancia de primer orden a la intensidad; el término logarítmico separa clases de cromaticidad parecida y distinta reflectancia (blanco, amarillo).
- **Antirrebote:** se exigen 3 muestras consecutivas iguales (3 × 30 ms). El evento solo se emite en la transición piso → color, con histéresis para no contar dos veces una misma marca.
- **Localización de la marca:** durante un avance de duración nominal *T* por celda, la celda de la marca es *k = ⌊t/T + δ + 0.5⌋*, con *δ* = 0.2 celdas el desplazamiento longitudinal eje–sensor. Python deduplica por coordenada.
- Las referencias (*r_i, g_i, b_i, C_i*) se miden en sitio con un modo de calibración.

### 3.3 Visión (opcional, MPU)

- Cámara UVC en el mástil, 320 × 240, OpenCV con V4L2.
- Segmentación HSV de la pared y fracción de píxeles en tres ROI que miran la celda siguiente (fondo, izquierda, derecha).
- Las paredes detectadas se escriben en un mapa **tentativo** separado del confirmado: sirven al *flood fill* para anticipar callejones, pero nunca sobreescriben lo que miden los ToF. Si el mapa tentativo deja al robot sin camino, se recalcula ignorándolo.
- El sistema funciona sin cámara.

## 4. Control de movimiento

**Actuación:** dos micromotorreductores DC (≈ 12 × 11 mm de sección), ruedas de 45 mm y patín, con un puente H L298N. PWM en ENA/ENB, sentido en IN1–IN4 y freno activo (ambas entradas en alto con EN = 255 durante 60 ms).

**Lazo a 100 Hz (T = 10 ms)**, sin encoders:

1. **Perfil de velocidad trapezoidal en lazo abierto:** rampa de aceleración de +6 PWM por ciclo desde `VEL_MIN`, crucero a `VEL_EXPLORA` o `VEL_RAPIDA` y desaceleración lineal en el último cuarto de la duración nominal. Busca no perder tracción y reducir el error de posición al detenerse.
2. **Centrado lateral (P):** *u = K_c · e*, saturado en ±40 PWM, aplicado diferencialmente: *PWM_L = v − u*, *PWM_R = v + u*.
   - Con dos paredes: *e = d_izq − d_der*.
   - Con una pared: error contra la distancia nominal `D_LADO`.
   - Sin paredes: lazo abierto con compensación estática `AJUSTE_DER`, que corrige la asimetría de los motores.
3. **Paro por referencia externa:** si hay pared al frente, el avance termina por distancia (*d_frente* ≤ `D_FRENTE`) y no por tiempo. Hay una tolerancia de +T/3 para alcanzarla. Así el error longitudinal acumulado se reinicia en cada celda con pared frontal.
4. Los giros en sitio son por tiempo (`MS_90`) a PWM constante.

**Limitaciones reconocidas:** sin odometría ni IMU, los avances sin pared frontal y los giros dependen de la tensión de batería y de la fricción. Se mitiga con la recalibración en sitio de `MS_CELDA` y `MS_90` (procedimiento documentado), el paro por pared y el centrado continuo. La mejora natural sería sumar encoders en cuadratura y un giróscopo para cerrar el lazo en posición y rumbo.

## 5. Planeación (Linux, Python)

- **Mapa:** 16 × 16 celdas, 4 bits por celda (N, E, S, O), con escritura simétrica en la celda vecina. El perímetro se inicializa cerrado. Se guarda además una matriz de celdas visitadas.
- ***Flood fill*:** BFS desde el conjunto objetivo, O(N²) = 256 celdas por recálculo; se recalcula tras cada celda.
  - **Exploración** (supuesto optimista): lo desconocido es transitable. Ante un empate entre vecinos, el orden de preferencia es seguir de frente, luego derecha, izquierda y media vuelta. Esto minimiza giros, que son la mayor fuente de error.
  - **Fases:** origen → meta → origen. El regreso explora otras rutas y aumenta la probabilidad de que el camino óptimo quede en celdas visitadas.
- **Corrida rápida** (supuesto pesimista): solo cruza aristas entre celdas ambas visitadas. Los tramos rectos consecutivos se fusionan en un solo comando `mover(n)` para aprovechar el perfil trapezoidal y no detenerse en cada celda.
- **Persistencia:** el mapa y las marcas se guardan en JSON en la memoria de la placa y sobreviven al apagado. Un toque largo del botón borra el mapa.

## 6. Hardware

| Subsistema | Implementación |
|---|---|
| Alimentación | Batería 2S (6.0–8.4 V) → interruptor → L298N (V_S) y VIN del UNO Q (7–24 V, reguladores conmutados) |
| Lógica de potencia | Regulador 78M05 del L298N (requiere V_in ≳ 7 V). Entradas compatibles con 3.3 V (V_IH ≥ 2.3 V) |
| Bus I²C | 400 kHz, VCC del bus a 3.3 V para no exponer los GPIO del Q a *pull-ups* de 5 V. Dispositivos: 3 × VL53L0X, TCS34725, SSD1306 |
| HMI | OLED SSD1306 128 × 64 con driver propio. Muestra estado, conteos por color y un contador de *heartbeat* RPC para diagnosticar la comunicación MCU–MPU |
| Chasis | Paramétrico en OpenSCAD, dos pisos impresos en FDM (Bambu X2D), insertos de latón M3 termofijados, mástil de perfil de aluminio 2020 para la cámara. Huella ≤ 120 mm, compatible con la celda de 180 mm. Interferencias verificadas con intersección CSG de todas las piezas |
| Intercambio de placa | Mismo mapa de pines en Q y R3 a través de un Proto Shield; solo cambia el puente de VCC del bus (3V3 ↔ 5V) |

**Presupuesto de tensión en motores:** el L298N es bipolar (Darlington) y cae ≈ 2–3 V por puente. Con 7.4 V nominales llegan ≈ 4.5–5 V a los motores. Es la principal ineficiencia del diseño; un puente MOSFET (TB6612FNG, DRV8833) la eliminaría.

## 7. Parámetros calibrables

| Parámetro | Valor base | Efecto |
|---|---|---|
| `MS_CELDA` / `MS_RAPIDA` | 600 / 400 ms | Duración nominal por celda (exploración / rápida) |
| `MS_90` | 250 ms | Duración de giro de 90° |
| `VEL_EXPLORA` / `VEL_RAPIDA` / `VEL_GIRO` / `VEL_MIN` | 140 / 220 / 130 / 80 | PWM (8 bits) |
| `KC` | 0.8 PWM/mm | Ganancia proporcional de centrado |
| `PARED` | 120 mm | Umbral de detección de pared |
| `D_FRENTE` / `D_LADO` | 55 / 50 mm | Referencias de paro frontal y de centrado con una pared |
| `AJUSTE_DER` | 0 | Compensación estática de asimetría |
| `refs[]` | en sitio | Centroides de color |

## 8. Repositorio

- `uno_q/sketch/`: firmware MCU (C++)
- `uno_q/python/`: planeación y visión
- `atmega328p/`: respaldo bare-metal
- `chasis/`: CAD paramétrico y STL
- `docs/`: manuales y diagramas
