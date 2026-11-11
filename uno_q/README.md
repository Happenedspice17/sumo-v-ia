# Iteración B – Arduino UNO Q (con cámara)

El STM32 mueve los motores, lee los sensores y maneja la OLED (`sketch/`). Linux corre Python con la cámara y resuelve el laberinto (`python/`). Se comunican por Bridge.

## Conexiones

| Componente | Pin del módulo | UNO Q |
|---|---|---|
| L298N | ENA (quitar jumper) | D5 |
| L298N | IN1 / IN2 | D7 / D8 |
| L298N | ENB (quitar jumper) | D6 |
| L298N | IN3 / IN4 | D9 / D10 |
| L298N | 12V / GND | Batería + / GND |
| VL53L0X izq / frente / der | XSHUT | A0 / A1 / A2 |
| VL53L0X ×3, TCS34725, OLED | SDA / SCL | SDA / SCL |
| VL53L0X ×3 (VCC), TCS34725 (VIN), OLED | VCC / GND | 3.3V / GND |
| TCS34725 (morado) | LED / INT | sin conectar (LED siempre encendido) |
| Botón de arranque | a GND | D2 |
| Batería 2S 18650 (conector T) | + | interruptor → VIN |
| Cámara USB | | hub USB‑C |

VCC (3.3V), GND, SDA y SCL se reparten en la mini protoboard del Proto Shield: columnas VCC, GND, SDA, SCL. Con la Q el puente de VCC va a 3V3 (con el R3 va a 5V). Los pines son los mismos que en el R3 (`../atmega328p/`): para cambiar de placa se saca el shield con sus dupont. Ver `../docs/uno_q.md`.

GND común entre todo. No alimentes el UNO Q con el regulador de 5 V del L298N. La posición física de cada pieza está en `../chasis/chasis.pdf`.

## Programación (Arduino App Lab)

1. Crea una app nueva llamada `Laberinto`.
2. Copia `sketch/sketch.ino`, `python/main.py`, `python/requirements.txt` y `assets/index.html` (carpeta `assets/` en la raíz de la app).
3. Agrega el brick **WebUI - HTML** (panel Bricks). Sin él no hay página web.
4. En las librerías del sketch agrega `Adafruit SSD1306`, `Adafruit GFX Library`, `Adafruit TCS34725` y `VL53L0X` (de Pololu).
5. Pulsa **Run**. App Lab carga el sketch al STM32 y arranca el Python.
6. Marca la app para que arranque sola: `arduino-app-cli properties set default user:laberinto2`.

La página web se ve por WiFi en `http://<IP>:7000`. La IP cambia según la red: App Lab la muestra al darle Run, o con `adb shell hostname -I`. La laptop o el celular y la placa deben estar en la misma red.

Con el hub conectado al USB-C, App Lab se conecta por WiFi (el puerto no puede ir a la laptop y al hub a la vez). Conecta cámara y hub antes de Run.

**Alimentación del hub:** con la Q alimentada por VIN, su USB-C no da 5 V al hub. El hub debe recibir energía por su puerto PD: cargador PD, o 5 V ≥ 3 A del regulador del robot a un cable USB-C cortado conectado al puerto PD del hub, o módulo DC-DC con salida USB-C PD desde la batería. Alimentar solo la cámara con 5 V externos no basta.

## Calibración

1. **Colores**: con la app corriendo abre `http://<ip de la Q>:7000` (App Lab muestra el link). El asistente pide los 5 colores uno por uno; cada botón promedia 5 lecturas. Se guarda en `/app/datos/colores.json` y se carga al MCU en cada arranque (`set_ref`). Los guardados tienen prioridad. Sin archivo guardado se usan los valores de fábrica (`REFS` en `main.py`, igual a `refs[]` del sketch): PISO 0.282,0.379,0.333,153; ROJO 0.602,0.208,0.188,581; VERDE 0.155,0.535,0.309,636; AZUL 0.16,0.329,0.508,354; AMAR 0.409,0.449,0.142,1836.
   **Sensores**: enciende con el botón presionado. La OLED muestra `r g b c`, el color detectado y las 3 distancias. Centra el robot en una celda y anota `D_LADO` y `D_FRENTE`.
2. **Avance**: con pared enfrente a menos de 1 m (`RANGO`) avanza por distancia y no hay que calibrar. Sin pared a la vista avanza por tiempo: ajusta `MS_CELDA` hasta que avance 18 cm, y `MS_90` para giros de 90°. Calibra con la batería cargada. Si se desvía, ajusta `AJUSTE_DER`.
3. **Cámara**: busca el amarillo (`HUE_AMAR`) y el blanco de las paredes en el piso por donde va a pasar (`ZONA_PASO`, `BLANCO_LO/HI`, `BLANCO_MAX` en `main.py`). La página web muestra la imagen (160 × 120): recuadro amarillo donde ve el amarillo, y el camino en rojo si ve blanco o verde si ve negro. Ajusta `ZONA_PASO` para que en un pasillo libre salga verde. No se guardan imágenes en `/app`: con ellas App Lab marca "failed to start".

## Funcionamiento

**Sketch (STM32)**, solo mueve el robot:

- Avanza por distancia: al arrancar toma la lectura del frontal y para cuando bajó 180 mm (`CELDA`). Si el frontal no ve nada a menos de 1 m va por tiempo (`MS_CELDA`), y si a medio avance aparece una pared sigue por distancia. Siempre para a 130 mm de la pared de enfrente (`D_FRENTE`) y se hace para atrás si queda más cerca.
- **Cambio brusco** (una lectura cambia `SALTO` = 120 mm o más y se repite en la siguiente): si se abre un lateral, para al centro de esa celda (`TRAS_SALTO` = 124 mm después) para escanearla; si salta el frontal, vuelve a medir lo que falta. Python lo lee con `odo(3)`.
- Con `mover(mm, lento)` baja a `VEL_LENTO` (la pide Python cuando la cámara ve blanco).
- En recta solo corrige el rumbo si un lateral lee menos de 90 mm (`D_LADO_MIN`).
- Gira 90° por tiempo (`MS_90`).
- Lee los ToF y el sensor de color y se los da al Python. RPC `odo(i)`: 0 mm recorridos, 1 mm que faltan, 3 saltos (1 izq, 2 frente, 4 der), 5/6/7 frente/izq/der.

**Python**, decide en cada paso:

1. Lee los 3 ToF, la menor de 3 lecturas de cada uno (5 si en el avance hubo un cambio brusco). Las anota como paredes de la celda en el mapa.
2. Prioridad: de frente (≥ 150 mm); si no, izquierda (lateral ≥ 120 mm); si no, derecha; si no, media vuelta.
3. Tras un cambio brusco va a la salida libre que lleve a una celda que no está en el mapa, la de lectura más lejana.
4. Si ya pasó 3 veces por esa celda (rodea una isla) toma la salida que ha usado menos; la cámara desempata hacia el amarillo. La celda sale de los mm que de verdad avanzó.
5. Antes de cada avance la cámara revisa el piso del camino: negro → normal; blanco (pared) → va lento y el frontal hace el doble check (el sketch para a 130 mm si de verdad hay pared).
6. Cada color que lee el TCS34725 (3 lecturas seguidas) va al mapa en la celda donde está el sensor y se cuenta una vez. Amarillo = meta: se detiene (OLED `META`).
7. El mapa (paredes, colores y meta) se guarda en `/app/datos/mapa.json`. En la siguiente corrida, si conoce la meta, va por el camino más corto conocido (BFS, OLED `RAPIDO`); si algo no cuadra, sigue explorando desde ahí.

- Botón corto: corrida nueva (pon el robot en el inicio). Otro toque la detiene. Sostenido más de 2 s: borra el mapa y el conteo (laberinto nuevo). Cada corrida empieza en la misma celda y viendo al mismo lado.
- **Panel web → Ver sensores ToF:** dibujo en vivo de lo que mide cada VL53L0X y qué haría el robot.
- **Cámara al arrancar:** la busca una vez (OLED `LISTO` si la encuentra, `SIN CAM` si no). Un hilo revisa cada 2 s: si no hay cámara la busca y si se desconecta pone `SIN CAM`.
