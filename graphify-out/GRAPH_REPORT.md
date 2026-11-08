# Graph Report - sumo-v-ia  (2026-11-08)

## Corpus Check
- 38 files · ~39,173 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: .stl 11, (none) 4, .csv 2)

## Summary
- 492 nodes · 881 edges · 24 communities (22 shown, 2 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 113 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `03a76102`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.cpp
- regAddr
- VL53L0X
- generar_manuales.py
- 3. Parte A: UNO R3 con Microchip Studio
- main.py
- generar_pdf.py
- Oled
- renders.py
- Robot de laberinto: Arduino UNO Q
- twi.cpp
- SequenceStepTimeouts
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
- Manual de uso: robot de laberinto (UNO Q)

## God Nodes (most connected - your core abstractions)
1. `regAddr` - 59 edges
2. `VL53L0X` - 46 edges
3. `Oled` - 21 edges
4. `calibracion()` - 18 edges
5. `main()` - 18 edges
6. `manual_ensamble()` - 16 edges
7. `Robot de laberinto: Arduino UNO Q` - 15 edges
8. `planta_piso1()` - 13 edges
9. `3. Parte A: UNO R3 con Microchip Studio` - 12 edges
10. `avanzar()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `4.7 Agregar las librerías del sketch` --references--> `VL53L0X`  [INFERRED]
  docs/GUIA_PROGRAMACION.md → atmega328p/laberinto/VL53L0X.h
- `Programación (Arduino App Lab)` --references--> `VL53L0X`  [INFERRED]
  uno_q/README.md → atmega328p/laberinto/VL53L0X.h
- `4.10 Cómo funciona Bridge (en dos frases y un ejemplo)` --references--> `girar()`  [INFERRED]
  docs/GUIA_PROGRAMACION.md → atmega328p/laberinto/main.cpp
- `Robot de laberinto – Microcontroladores 2` --references--> `pdf()`  [INFERRED]
  README.md → chasis/generar_pdf.py
- `3.9 Crear la herramienta externa para flashear` --references--> `w()`  [INFERRED]
  docs/GUIA_PROGRAMACION.md → atmega328p/img/diagrama.py

## Import Cycles
- None detected.

## Communities (24 total, 2 thin omitted)

### Community 0 - "main.cpp"
Cohesion: 0.07
Nodes (52): acota(), avanzar(), bordes(), borrar(), calibracion(), cargar(), centrado(), clasifica() (+44 more)

### Community 1 - "regAddr"
Cohesion: 0.03
Nodes (59): regAddr, ALGO_PART_TO_PART_RANGE_OFFSET_MM, ALGO_PHASECAL_CONFIG_TIMEOUT, ALGO_PHASECAL_LIM, CROSSTALK_COMPENSATION_PEAK_RATE_MCPS, DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, DYNAMIC_SPAD_REF_EN_START_OFFSET, FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT (+51 more)

### Community 2 - "VL53L0X"
Cohesion: 0.10
Nodes (17): SequenceStepEnables, dss, final_range, msrc, pre_range, tcc, vcselPeriodType, VcselPeriodFinalRange (+9 more)

### Community 3 - "generar_manuales.py"
Cohesion: 0.09
Nodes (23): bloque(), caja(), construir(), _destino(), _eco(), escribir_csv(), fig(), h1() (+15 more)

### Community 4 - "3. Parte A: UNO R3 con Microchip Studio"
Cohesion: 0.05
Nodes (39): w(), 1. Qué hay en el repositorio y qué placa usa qué código, 2. Descargar el repositorio (Windows), 3.10 Flashear y comprobar, 3.11 Alternativa: compilar con el Makefile, 3.1 Instalar Microchip Studio 7, 3.2 Conseguir avrdude, 3.3 Conectar la placa y encontrar el puerto COM (+31 more)

### Community 5 - "main.py"
Cohesion: 0.18
Nodes (23): abrir_camara(), avanzar(), bloqueado(), bordes(), borrar(), cargar(), dentro(), esperar() (+15 more)

### Community 6 - "generar_pdf.py"
Cohesion: 0.14
Nodes (17): agujero(), alzados(), caja(), cota(), ejes(), en_laberinto(), frente(), oled_pines() (+9 more)

### Community 7 - "Oled"
Cohesion: 0.12
Nodes (8): Oled, buf_, bus_, dir_, h_, w_, x_, y_

### Community 8 - "renders.py"
Cohesion: 0.13
Nodes (13): acercar(), bb(), caja_contenido(), correr(), etiquetar(), hacer(), hy(), pin_nano() (+5 more)

### Community 9 - "Robot de laberinto: Arduino UNO Q"
Cohesion: 0.09
Nodes (22): 10. Cambio de placa R3 ↔ Q, 11. Ruedas, 12. Pruebas de alimentación, 13. Pendientes, 14. Fuentes, 1. Plan, 2. Hardware, 3. Comunicación MCU ↔ Linux (Bridge) (+14 more)

### Community 10 - "twi.cpp"
Cohesion: 0.42
Nodes (9): datos(), arranque(), espera(), twiAlto(), twiByte(), twiEscribeReg(), twiInicio(), twiInit() (+1 more)

### Community 11 - "SequenceStepTimeouts"
Cohesion: 0.22
Nodes (9): SequenceStepTimeouts, final_range_mclks, final_range_us, final_range_vcsel_period_pclks, msrc_dss_tcc_mclks, msrc_dss_tcc_us, pre_range_mclks, pre_range_us (+1 more)

### Community 12 - "Robot de laberinto – Arduino UNO R3 (ATmega328P)"
Cohesion: 0.25
Nodes (7): Alimentación, Bus I2C, Cableado, Cambio R3 ↔ UNO Q, Funcionamiento, Programar con Microchip Studio, Robot de laberinto – Arduino UNO R3 (ATmega328P)

### Community 13 - "app.yaml"
Cohesion: 0.33
Nodes (5): bricks, description, icon, name, ports

### Community 14 - "Iteración B – Arduino UNO Q (con cámara)"
Cohesion: 0.33
Nodes (5): Calibración, Conexiones, Funcionamiento, Iteración B – Arduino UNO Q (con cámara), Programación (Arduino App Lab)

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

### Community 23 - "Manual de uso: robot de laberinto (UNO Q)"
Cohesion: 0.18
Nodes (10): 0. Antes de prender, 1. Prender, 2. El botón D2, 3. La pantalla, 4. Jugar (la competencia), 5. Calibrar colores (una vez por pista / luz), 6. Calibrar movimiento (en `sketch.ino`, sección Calibracion), 7. Si algo falla (+2 more)

## Knowledge Gaps
- **87 isolated node(s):** `SYSRANGE_START`, `SYSTEM_THRESH_HIGH`, `SYSTEM_THRESH_LOW`, `SYSTEM_SEQUENCE_CONFIG`, `SYSTEM_RANGE_CONFIG` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 246 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VL53L0X` connect `VL53L0X` to `regAddr`, `SequenceStepTimeouts`, `3. Parte A: UNO R3 con Microchip Studio`, `Iteración B – Arduino UNO Q (con cámara)`?**
  _High betweenness centrality (0.271) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `VL53L0X` (e.g. with `4.7 Agregar las librerías del sketch` and `Programación (Arduino App Lab)`) actually correct?**
  _`VL53L0X` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SYSRANGE_START`, `SYSTEM_THRESH_HIGH`, `SYSTEM_THRESH_LOW` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.cpp` be split into smaller, more focused modules?**
  _Cohesion score 0.07343987823439878 - nodes in this community are weakly interconnected._
- **Why does `regAddr` connect `regAddr` to `VL53L0X`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `calibracion()` (e.g. with `oledBorra()` and `oledDec()`) actually correct?**
  _`calibracion()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `regAddr` be split into smaller, more focused modules?**
  _Cohesion score 0.03389830508474576 - nodes in this community are weakly interconnected._