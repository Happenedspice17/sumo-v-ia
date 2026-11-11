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
2. **Avance**: ajusta `MS_CELDA` hasta que avance 18 cm en un pasillo sin pared enfrente, y `MS_90` para giros de 90°. `MS_RAPIDA` se ajusta igual, en rectas de varias celdas. Calibra con la batería cargada. Si se desvía, ajusta `AJUSTE_DER`.
3. **Cámara**: la página web muestra la imagen (160 × 120) con las 3 regiones: rojo = pared, verde = libre. No se guardan imágenes en `/app`: con ellas App Lab marca "failed to start". Ajusta `ROI`, `PARED_LO/HI` y `UMBRAL` en `main.py` hasta que los rectángulos salgan rojos donde hay pared en la celda siguiente.
4. **Laberinto**: ajusta `N`, `INICIO`, `RUMBO_INI` y `META` según las reglas del día.

## Funcionamiento

- Los VL53L0X leen las paredes de la celda actual, mantienen el robot centrado y lo detienen a `D_FRENTE` cuando hay pared enfrente.
- **Odometría ligera** (medidas del CAD: VL53L0X laterales 40 mm y frontal 54 mm adelante del eje; lente a 162 mm, 32 mm adelante, 25° abajo):
  - Sketch, en tiempo real: cuando un sensor lateral pasa el borde de una pared (poste entre celdas) corrige la posición y aprende la velocidad real (`escala`); con pared al frente a menos de 400 mm corrige lo que falta. Ajuste: `BORDE_AJ`, `MAX_CORR`.
  - Python, antes de cada avance: la cámara mide la distancia a la base de la pared de enfrente y le suma o resta hasta 60 mm al avance para quedar centrado. Ajuste: `CAM_INCL`, `CAM_H`, `CAM_FOV_V` (el panel dibuja la línea amarilla y los mm).
  - El panel web muestra cuánto le falta, qué paredes ve cada sensor y lo que mide la cámara. RPC `odo(i)`.
- **Antes de cada recta** se lee el frontal 3 veces (la menor): nunca avanza más celdas de las que ve libres, aunque el mapa o la cámara digan otra cosa. La cámara solo corrige distancia si el frontal no ve nada a menos de 1 m (la cámara ve las paredes de 3/4 para arriba).
- **Panel web → Ver sensores ToF:** dibujo en vivo de lo que mide cada VL53L0X y cuántas celdas libres hay al frente.
- **Los VL53L0X mandan.** Se leen en cada celda (aunque ya se conozca) y antes de cada avance: si ven pared enfrente no se avanza, y corrigen paredes del mapa en los dos sentidos. Lo que ve solo la cámara no bloquea: hace el camino `PESO_CAM` celdas más caro.
- La cámara ve por encima de las paredes: cada región de `ROI` (`"adelante,lado,pared"`) marca una pared de una celda hasta 2 adelante, aunque haya pared enfrente. Esas paredes van al mapa como tentativas, para que el flood‑fill descarte callejones antes de entrar. Si la cámara se equivoca y bloquea todo, el robot ignora esas paredes tentativas. Sin cámara, funciona solo con los VL53L0X (OLED: `SIN CAM`).
- **Cámara en los puntos ciegos de los ToF** (posiciones del CAD): antes de cada avance revisa el piso de las diagonales de enfrente (`CIEGOS`, x ±25–60 mm, y 120–220 mm); si ve algo blanco ahí no avanza por esa salida. Si el frontal pierde la lectura y la cámara ve pared a menos de `CAM_CERCA` (230 mm), cuenta como pared.
- **Busca el amarillo:** explora sin fin hasta que el TCS34725 ve AMAR (`OBJETIVO`) y la cámara también lo vio en esa celda (sin cámara basta el sensor); entonces para con el RPC `alto`. En cada celda los ToF dicen qué salidas están libres y va a la menos visitada (empate: pared derecha); no guarda paredes. Un toque a D2 lo detiene.
- Sin ruta conocida, explora hasta la meta y regresa solo al inicio. No lo recojas hasta que la OLED diga `LISTO`.
- Con ruta conocida, va directo a la meta con rectas largas a velocidad alta.
- Botón corto: siguiente corrida (pon el robot en el inicio, viendo hacia `RUMBO_INI`).
- Botón sostenido más de 2 s: borra mapa y conteo (laberinto nuevo).
- Una marca se cuenta solo si el color se sostiene 3 lecturas y antes se vio piso. Además se guarda la celda y no se vuelve a contar.
- **Cámara al arrancar:** la busca una vez (OLED `LISTO` si la encuentra, `SIN CAM` si no). Si no la encuentra, un hilo la sigue buscando cada 2 s en segundo plano, sin frenar el arranque, y pone la OLED en `LISTO` al encontrarla. La página web (`/api/foto`) reintenta abrirla cada 5 s y la reabre si se desconecta.
