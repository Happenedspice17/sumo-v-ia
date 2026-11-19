# Graph Report - sumo-v-ia  (2026-11-19)

## Corpus Check
- 60 files · ~182,409 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 25 file(s) not represented in the graph (top: .stl 12, (none) 4, .csv 3)

## Summary
- 1134 nodes · 1900 edges · 63 communities (51 shown, 12 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c7210f87`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.cpp
- regAddr
- VL53L0X
- generar_manuales.py
- 3. Parte A: UNO R3 con Microchip Studio
- uno_q/python/main.py
- generar_pdf.py
- Oled
- Robot de laberinto: Arduino UNO Q
- manual_tecnico.md
- Etapas
- Robot de laberinto – Arduino UNO R3 (ATmega328P)
- app.yaml
- Iteración B – Arduino UNO Q (con cámara)
- CLAUDE.md
- Ponytail Help
- ponytail-audit/SKILL.md
- Ponytail Gain
- ponytail-review/SKILL.md
- Ponytail
- ponytail-debt/SKILL.md
- .claude/CLAUDE.md
- manual_uso.md
- md_pdf.js
- gen
- rpc
- Robot
- Robot
- uno_q_v2/python/main.py
- vision
- rpc
- 🤖 Robot resolvedor de laberintos
- vision
- decidir
- decidir
- cam_puntos
- math
- iniciar
- uno_q_v2/sim/sim2d.py
- guarda_cam
- corrida
- api_tof_cal
- corrida
- 🤖 Iteración B – Arduino UNO Q (con cámara)
- manual_jueces.md
- os
- historial_cambios.md
- Pruebas realizadas
- loc_observa
- loc_observa
- Registro
- uno_q_v2/app.yaml
- Registro
- package.json
- ⚙️ Funcionamiento
- 2. Hardware
- angulo
- loc_inicia
- loc_inicia
- 7. Energía

## God Nodes (most connected - your core abstractions)
1. `regAddr` - 60 edges
2. `Etapas` - 60 edges
3. `VL53L0X` - 49 edges
4. `rpc()` - 26 edges
5. `rpc()` - 24 edges
6. `Oled` - 21 edges
7. `Oled` - 21 edges
8. `calibracion()` - 19 edges
9. `main()` - 18 edges
10. `Robot` - 17 edges

## Surprising Connections (you probably didn't know these)
- `4.7 Agregar las librerías del sketch` --references--> `VL53L0X`  [INFERRED]
  docs/GUIA_PROGRAMACION.md → atmega328p/laberinto/VL53L0X.h
- `Cómo cargar la app (una vez)` --references--> `VL53L0X`  [INFERRED]
  docs/manual_uso.md → atmega328p/laberinto/VL53L0X.h
- `💻 Programación (Arduino App Lab)` --references--> `VL53L0X`  [INFERRED]
  uno_q/README.md → atmega328p/laberinto/VL53L0X.h
- `💻 Programación (Arduino App Lab)` --references--> `VL53L0X`  [INFERRED]
  uno_q_v2/README.md → atmega328p/laberinto/VL53L0X.h
- `3. Protocolo RPC (Bridge)` --references--> `arranque()`  [INFERRED]
  docs/manual_tecnico.md → atmega328p/laberinto/twi.cpp

## Import Cycles
- None detected.

## Communities (63 total, 12 thin omitted)

### Community 0 - "main.cpp"
Cohesion: 0.07
Nodes (54): acota(), avanzar(), bordes(), borrar(), calibracion(), cargar(), centrado(), clasifica() (+46 more)

### Community 1 - "regAddr"
Cohesion: 0.03
Nodes (59): regAddr, ALGO_PART_TO_PART_RANGE_OFFSET_MM, ALGO_PHASECAL_CONFIG_TIMEOUT, ALGO_PHASECAL_LIM, CROSSTALK_COMPENSATION_PEAK_RATE_MCPS, DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, DYNAMIC_SPAD_REF_EN_START_OFFSET, FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT (+51 more)

### Community 2 - "VL53L0X"
Cohesion: 0.07
Nodes (34): datos(), arranque(), espera(), twiAlto(), twiByte(), twiEscribeReg(), twiInicio(), twiLeeReg() (+26 more)

### Community 3 - "generar_manuales.py"
Cohesion: 0.05
Nodes (35): acercar(), bb(), caja_contenido(), correr(), etiquetar(), hacer(), hy(), pin_nano() (+27 more)

### Community 4 - "3. Parte A: UNO R3 con Microchip Studio"
Cohesion: 0.05
Nodes (41): 1. Qué hay en el repositorio y qué placa usa qué código, 2. Descargar el repositorio (Windows), 3.10 Flashear y comprobar, 3.11 Alternativa: compilar con el Makefile, 3.1 Instalar Microchip Studio 7, 3.2 Conseguir avrdude, 3.3 Conectar la placa y encontrar el puerto COM, 3.4 Crear el proyecto en Microchip Studio (+33 more)

### Community 5 - "uno_q/python/main.py"
Cohesion: 0.10
Nodes (12): api_avance_prueba(), api_control(), api_guardar(), api_lectura(), api_tof(), clasifica(), cuadra_angulo(), enviar_refs() (+4 more)

### Community 6 - "generar_pdf.py"
Cohesion: 0.15
Nodes (17): agujero(), alzados(), caja(), cota(), ejes(), en_laberinto(), frente(), oled_pines() (+9 more)

### Community 7 - "Oled"
Cohesion: 0.06
Nodes (16): Oled, buf_, bus_, dir_, h_, w_, x_, y_ (+8 more)

### Community 9 - "Robot de laberinto: Arduino UNO Q"
Cohesion: 0.13
Nodes (15): 10. Cambio de placa R3 ↔ Q, 11. Ruedas, 12. Pruebas de alimentación, 13. Pendientes, 14. Fuentes, 1. Plan, 3. Comunicación MCU ↔ Linux (Bridge), 4. Estrategia de corridas (+7 more)

### Community 10 - "manual_tecnico.md"
Cohesion: 0.06
Nodes (31): Etapa 54. `uno_q_v2/`: confía en las paredes, no en los milímetros (13-nov), 10. Página web, 11.1 Sketch (STM32), 11.2 Python (Linux), 11. Parámetros calibrables, 12.1 En pista y en competencia (v2), 12. Evolución del diseño, 13. Control de versiones (+23 more)

### Community 11 - "Etapas"
Cohesion: 0.03
Nodes (58): Etapa 10. Piso 2 modelado igual al ya impreso (7-nov), Etapa 11. Cuna del motor: ajuste fino del hueco (7-nov), Etapa 12. OLED en la cabeza de la cámara y mástil 2020 (7-nov), Etapa 13. Diagrama de conexiones (7-nov), Etapa 14. Cámara en el UNO Q: búsqueda del nodo de video (7 y 8-nov), Etapa 15. Diagnóstico en la OLED (8-nov), Etapa 16. Panel web de calibración de colores (8-nov), Etapa 17. Manuales (8-nov) (+50 more)

### Community 12 - "Robot de laberinto – Arduino UNO R3 (ATmega328P)"
Cohesion: 0.25
Nodes (7): Alimentación, Bus I2C, Cableado, Cambio R3 ↔ UNO Q, Funcionamiento, Programar con Microchip Studio, Robot de laberinto – Arduino UNO R3 (ATmega328P)

### Community 13 - "app.yaml"
Cohesion: 0.29
Nodes (6): bricks, arduino:web_ui, description, icon, name, ports

### Community 14 - "Iteración B – Arduino UNO Q (con cámara)"
Cohesion: 0.22
Nodes (6): 🧭 Arquitectura, 🎛️ Calibración, 🔌 Conexiones, 📖 Glosario, 🤖 Iteración B – Arduino UNO Q (con cámara), 💻 Programación (Arduino App Lab)

### Community 16 - "Ponytail Help"
Cohesion: 0.22
Nodes (8): Band (Claude Code), Configure Default Mode, Deactivate, Levels, More, Ponytail Help, Skills, Update

### Community 17 - "ponytail-audit/SKILL.md"
Cohesion: 0.40
Nodes (4): 1. Map first, 2. Look for, 3. Check before you report, 4. Output

### Community 18 - "Ponytail Gain"
Cohesion: 0.40
Nodes (4): Boundaries, Honesty boundary, Ponytail Gain, Scoreboard

### Community 19 - "ponytail-review/SKILL.md"
Cohesion: 0.40
Nodes (4): 1. Understand first, 2. Look for, 3. Check before you report, 4. Output

### Community 20 - "Ponytail"
Cohesion: 0.40
Nodes (4): Before you write, Levels, Ponytail, The smallest complete change

### Community 21 - "ponytail-debt/SKILL.md"
Cohesion: 0.50
Nodes (3): Boundaries, Output, Scan

### Community 23 - "manual_uso.md"
Cohesion: 0.11
Nodes (18): 10. Glosario, 1. Antes de empezar, 2. Cómo encenderlo, 3. Cómo usar el botón D2, 4.1 Colores (una vez por pista), 4.2 Sensores de distancia (una vez, o si mueves un sensor), 4.2b Avance sin encoders (una vez, o si cambia la batería o el piso), 4.3 Cámara (una vez, o si mueves la cámara) (+10 more)

### Community 24 - "md_pdf.js"
Cohesion: 0.29
Nodes (4): { chromium }, path, { chromium }, path

### Community 26 - "rpc"
Cohesion: 0.09
Nodes (26): abrir_camara(), ajuste(), api_tof_cal(), avanzar(), borrar(), buscar_color(), cargar(), cuadrar() (+18 more)

### Community 27 - "Robot"
Cohesion: 0.06
Nodes (6): lee(), Mapa, Robot, falta(), fin(), v()

### Community 28 - "Robot"
Cohesion: 0.06
Nodes (4): Mapa, Robot, falta(), fin()

### Community 29 - "uno_q_v2/python/main.py"
Cohesion: 0.10
Nodes (18): api_avance_cal(), api_avance_prueba(), api_control(), api_guardar(), api_lectura(), api_tof(), cam_pixel(), clasifica() (+10 more)

### Community 30 - "vision"
Cohesion: 0.10
Nodes (16): aberturas(), api_cam_cero(), api_cam_dist(), api_cam_giro(), api_cam_sens(), api_foto(), bordes(), contraste() (+8 more)

### Community 31 - "rpc"
Cohesion: 0.16
Nodes (16): avanzar(), borrar(), buscar_color(), cuadrar(), detener(), esperar(), estado(), fase() (+8 more)

### Community 32 - "🤖 Robot resolvedor de laberintos"
Cohesion: 0.09
Nodes (23): 10. Página web sin interferir con la corrida, 1. Avance por distancia en lugar de por tiempo, 2. Votos en el mapa en lugar de sobrescribir, 3. Umbrales con margen medido, 4. Detección de discontinuidades ("saltos"), 5. Calibración lineal de los ToF, 6. Giroscopio para los giros, 7. La cámara como sensor auxiliar, no primario (+15 more)

### Community 33 - "vision"
Cohesion: 0.10
Nodes (11): aberturas(), angulo(), api_cam_dist(), api_cam_incl(), bordes(), contraste(), fila_pared(), mm_fila() (+3 more)

### Community 34 - "decidir"
Cohesion: 0.12
Nodes (11): al_centro(), anota(), brujula(), celda(), decidir(), frontera(), libre(), por_pista() (+3 more)

### Community 35 - "decidir"
Cohesion: 0.12
Nodes (11): al_centro(), anota(), brujula(), celda(), decidir(), frontera(), libre(), por_pista() (+3 more)

### Community 36 - "cam_puntos"
Cohesion: 0.16
Nodes (12): Etapa 56. La cámara como mapa del piso (13-nov), 7.4 La cámara como mapa del piso (v2), api_foto(), base_pared(), cam_cols(), cam_lejos(), cam_piso(), cam_puntos() (+4 more)

### Community 37 - "math"
Cohesion: 0.22
Nodes (4): imagen(), mide(), camino(), ve()

### Community 38 - "iniciar"
Cohesion: 0.16
Nodes (8): abrir_camara(), api_cam_expo(), aplica_expo(), cargar(), iniciar(), lee(), paso(), vigilar_cam()

### Community 40 - "guarda_cam"
Cohesion: 0.18
Nodes (7): api_cam_cero(), api_cam_expo(), api_cam_giro(), api_cam_sens(), aplica_expo(), fuga_ahora(), guarda_cam()

### Community 41 - "corrida"
Cohesion: 0.17
Nodes (5): corrida(), decide_alt(), laberinto(), lote(), pista_real()

### Community 42 - "api_tof_cal"
Cohesion: 0.22
Nodes (7): ajuste(), api_avance_cal(), api_tof_cal(), enviar_tof(), escribe(), estado_tof_cal(), guardar()

### Community 43 - "corrida"
Cohesion: 0.18
Nodes (5): corrida(), decide_alt(), laberinto(), lote(), pista_real()

### Community 44 - "🤖 Iteración B – Arduino UNO Q (con cámara)"
Cohesion: 0.18
Nodes (11): 🧭 Arquitectura, Botón, web y cámara, 🎛️ Calibración, 🔌 Conexiones, ⚙️ Funcionamiento, Giros y MPU-6050, 📖 Glosario, 🤖 Iteración B – Arduino UNO Q (con cámara) (+3 more)

### Community 45 - "manual_jueces.md"
Cohesion: 0.20
Nodes (9): Arquitectura: dos cerebros, una placa, Calibración desde el celular, El reto y nuestra respuesta, Hardware y chasis a medida, Lo que aprendimos, Movimiento sin encoders, MPU-6050: giros reales, rumbo con las paredes, Se ubica solo en la pista (+1 more)

### Community 46 - "os"
Cohesion: 0.31
Nodes (4): lote(), uno(), lote(), uno()

### Community 47 - "historial_cambios.md"
Cohesion: 0.25
Nodes (7): Arquitectura según el grafo de conocimiento, Cómo leer esta bitácora, Decisiones de ingeniería, Glosario, Lecciones aprendidas, Línea de tiempo, Pendientes

### Community 48 - "Pruebas realizadas"
Cohesion: 0.25
Nodes (8): Electrónica y alimentación, Herramientas de prueba integradas en el robot, Mediciones e iteraciones físicas, Pendiente, Pruebas en pista, Pruebas realizadas, Sensores, Software

### Community 49 - "loc_observa"
Cohesion: 0.25
Nodes (4): leidas(), loc_mueve(), loc_observa(), tramo()

### Community 50 - "loc_observa"
Cohesion: 0.25
Nodes (4): leidas(), loc_mueve(), loc_observa(), tramo()

### Community 52 - "uno_q_v2/app.yaml"
Cohesion: 0.29
Nodes (6): bricks, arduino:web_ui, description, icon, name, ports

### Community 54 - "package.json"
Cohesion: 0.40
Nodes (5): dependencies, mermaid@11.4.1, description, private, mermaid

### Community 55 - "⚙️ Funcionamiento"
Cohesion: 0.40
Nodes (5): Botón, web y cámara, ⚙️ Funcionamiento, Giros y MPU-6050, Python: decide en cada paso, Sketch (STM32): solo mueve el robot

### Community 57 - "2. Hardware"
Cohesion: 0.50
Nodes (4): 2. Hardware, Programación (Arduino App Lab), R3 frente a Q, UNO Q

### Community 61 - "7. Energía"
Cohesion: 0.67
Nodes (3): 7. Energía, Problema del USB-C con VIN, Ruta PD en el robot

## Knowledge Gaps
- **94 isolated node(s):** `SYSRANGE_START`, `SYSTEM_THRESH_HIGH`, `SYSTEM_THRESH_LOW`, `SYSTEM_SEQUENCE_CONFIG`, `SYSTEM_RANGE_CONFIG` (+89 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 605 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VL53L0X` connect `VL53L0X` to `regAddr`, `3. Parte A: UNO R3 con Microchip Studio`, `🤖 Iteración B – Arduino UNO Q (con cámara)`, `Iteración B – Arduino UNO Q (con cámara)`, `historial_cambios.md`, `manual_uso.md`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `VL53L0X` (e.g. with `4.7 Agregar las librerías del sketch` and `Arquitectura según el grafo de conocimiento`) actually correct?**
  _`VL53L0X` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SYSRANGE_START`, `SYSTEM_THRESH_HIGH`, `SYSTEM_THRESH_LOW` to the rest of the system?**
  _94 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.cpp` be split into smaller, more focused modules?**
  _Cohesion score 0.07108478341355054 - nodes in this community are weakly interconnected._
- **Why does `Etapas` connect `Etapas` to `manual_tecnico.md`, `cam_puntos`, `historial_cambios.md`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Should `regAddr` be split into smaller, more focused modules?**
  _Cohesion score 0.03389830508474576 - nodes in this community are weakly interconnected._
- **Why does `regAddr` connect `regAddr` to `VL53L0X`, `historial_cambios.md`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._