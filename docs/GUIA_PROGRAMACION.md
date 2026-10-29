# Guía de programación paso a paso

Esta guía es para alguien que **nunca** ha usado Microchip Studio, las herramientas de Arduino, una terminal ni el Arduino UNO Q. Sigue los pasos en orden. Si un paso dice **Verifica:**, no avances hasta que se cumpla.

Contenido:

1. [Qué hay en el repositorio y qué placa usa qué código](#1-qué-hay-en-el-repositorio-y-qué-placa-usa-qué-código)
2. [Descargar el repositorio (Windows)](#2-descargar-el-repositorio-windows)
3. [Parte A: UNO R3 con Microchip Studio](#3-parte-a-uno-r3-con-microchip-studio)
4. [Parte B: Arduino UNO Q con App Lab](#4-parte-b-arduino-uno-q-con-app-lab)
5. [Calibración](#5-calibración)
6. [Problemas comunes](#6-problemas-comunes)
7. [Glosario](#7-glosario)

---

## 1. Qué hay en el repositorio y qué placa usa qué código

Un **repositorio** es una carpeta con todos los archivos del proyecto. Las carpetas que te importan son estas:

| Carpeta | Qué contiene | Para qué placa |
|---|---|---|
| `atmega328p/laberinto/` | Firmware en C++ "bare-metal" (sin librerías de Arduino) | **Arduino UNO R3** (ATmega328P). Es el **respaldo oficial** |
| `uno_q/` | App de App Lab: `sketch/sketch.ino` (microcontrolador), `python/main.py` (Linux, cámara) y `python/requirements.txt` | **Arduino UNO Q**. Es la **placa principal** (experimental) |
| `chasis/` | Piezas 3D y planos | Ninguna (es mecánica) |
| `docs/` | Manuales y documentos técnicos (`uno_q.md`) | Ninguna |

Regla sencilla:

- ¿Tienes un **UNO R3**? Haz la **Parte A** (sección 3).
- ¿Tienes un **UNO Q**? Haz la **Parte B** (sección 4).
- Los dos usan el **mismo cableado**. Para cambiar de placa solo cambias la placa (ver `atmega328p/README.md`, sección "Cambio R3 ↔ UNO Q").

### Mapa de pines (igual en las dos placas)

| Señal | Pin |
|---|---|
| ENA (L298N) | D5 |
| ENB (L298N) | D6 |
| IN1, IN2, IN3, IN4 | D7, D8, D9, D10 |
| Botón de arranque (a GND) | D2 |
| XSHUT sensores VL53L0X izq / frente / der | A0 / A1 / A2 |
| I2C (OLED, VL53L0X, TCS34725) | SDA / SCL (pines de la cabecera junto a AREF) |
| Alimentación del robot | batería 2S, interruptor, VIN y GND |

### Voltaje del bus I2C (importante)

El bus I2C lleva un puente (jumper) llamado **VCC del bus** en el proto shield.

| Placa | El puente VCC del bus va en |
|---|---|
| UNO R3 | **5V** |
| UNO Q | **3V3** |

> **Peligro:** si usas el UNO Q con el puente en 5V, puedes dañar sus pines I2C. Antes de conectar la batería o el USB al Q, revisa que el puente esté en **3V3**.

---

## 2. Descargar el repositorio (Windows)

### Opción 1: descargar un ZIP (la más fácil)

1. Abre el navegador (Chrome, Edge o Firefox) y entra a la página del repositorio en GitHub. Tu profesor o equipo te dio el enlace. Tiene esta forma:

   ```
   https://github.com/<usuario>/<repositorio>
   ```

   `<usuario>` y `<repositorio>` son los nombres reales que aparecen en el enlace que te dieron.

2. Fíjate en la rama (branch) que dice el equipo. Si te dijeron `claude/laberinto-uno-q`, ábrela en el menú desplegable de ramas (arriba a la izquierda de la lista de archivos).
3. Pulsa el botón verde **Code**.
4. Pulsa **Download ZIP**.
5. Abre la carpeta **Descargas** y localiza el `.zip`.
6. Clic derecho sobre el `.zip` y elige **Extraer todo...** y luego **Extraer**.
7. Mueve la carpeta extraída a un lugar sencillo y **sin espacios ni acentos**, por ejemplo:

   ```
   C:\robot\
   ```

**Verifica:** al abrir `C:\robot\` (o como la hayas llamado) debes ver las carpetas `atmega328p`, `uno_q`, `docs` y `chasis`.

### Opción 2: `git clone` (para quien ya tenga Git)

Una **terminal** es una ventana donde escribes comandos. En Windows: pulsa la tecla **Windows**, escribe `cmd` y pulsa Enter. Aparece una ventana negra.

1. Instala Git desde <https://git-scm.com/download/win> (acepta las opciones por defecto).
2. Cierra y vuelve a abrir la terminal.
3. Ve a una carpeta de trabajo:

   ```
   cd C:\
   ```

4. Clona el repositorio (cambia la dirección por la real):

   ```
   git clone https://github.com/<usuario>/<repositorio>.git robot
   ```

5. Entra a la carpeta y cambia a la rama indicada:

   ```
   cd robot
   git checkout claude/laberinto-uno-q
   ```

**Verifica:** `dir` muestra las carpetas `atmega328p`, `uno_q`, `docs` y `chasis`.

En el resto de la guía, `C:\robot\` es la carpeta donde quedó el repositorio. Si usaste otra, cámbiala.

---

## 3. Parte A: UNO R3 con Microchip Studio

Necesitas: una PC con **Windows**, el **UNO R3**, un cable USB A-B (el de impresora) y que el cable sea de **datos** (no solo de carga).

> Microchip Studio solo existe para Windows. En Linux o Mac usa la alternativa del Makefile (sección 3.11).

### 3.1 Instalar Microchip Studio 7

1. Abre el navegador y busca: `Microchip Studio for AVR and SAM devices download`.
2. Entra a la página oficial de **microchip.com** (el dominio debe ser `microchip.com`).
3. Descarga el instalador. Hay uno "web" (pequeño, descarga mientras instala) y uno "offline" (muy grande, instala sin internet). Cualquiera sirve.
4. Ejecuta el instalador y acepta la licencia.
5. Cuando pida elegir arquitecturas, marca **AVR 8-bit MCUs** (las demás no hacen falta).
6. Termina la instalación. Si pide reiniciar, reinicia.
7. Abre **Microchip Studio** desde el menú Inicio.

**Verifica:** se abre una ventana con una página de inicio y un menú arriba (`File`, `Edit`, `View`, `Project`, `Build`, `Debug`, `Tools`...).

(Si tu pantalla se ve distinta, sigue el asistente del instalador.)

### 3.2 Conseguir avrdude

**avrdude** es el programa que pasa el archivo `.hex` del PC a la placa por USB. Microchip Studio **no** lo trae, así que hay que conseguirlo. La forma más fácil es instalar el **Arduino IDE**, que ya lo incluye.

1. Descarga el Arduino IDE desde <https://www.arduino.cc/en/software> e instálalo.
2. **Ábrelo una vez** y espera a que termine de descargar sus herramientas la primera vez (puede tardar unos minutos). Esto es necesario para que `avrdude` exista en tu PC.
3. Busca los dos archivos que necesitas: `avrdude.exe` y `avrdude.conf`. Se guardan normalmente aquí:

   ```
   C:\Users\<tu_usuario>\AppData\Local\Arduino15\packages\arduino\tools\avrdude\<version>\bin\avrdude.exe
   C:\Users\<tu_usuario>\AppData\Local\Arduino15\packages\arduino\tools\avrdude\<version>\etc\avrdude.conf
   ```

   - `<tu_usuario>` es el nombre de tu usuario de Windows.
   - `<version>` es una carpeta con un número, por ejemplo `6.3.0-arduino17`. Entra a la que exista.
   - `AppData` es una carpeta **oculta**. Para verla, en el Explorador de archivos abre la pestaña **Ver** y marca **Elementos ocultos**. Otra forma: pulsa `Windows + R`, escribe `%LOCALAPPDATA%\Arduino15\packages\arduino\tools\avrdude` y pulsa Enter.
   - En algunas versiones `avrdude.conf` está dentro de `bin` en vez de `etc`. Si no lo ves en `etc`, búscalo en `bin`.

4. Si no los encuentras, busca en el Explorador de archivos dentro de `C:\Users\<tu_usuario>\AppData\Local\Arduino15` el texto `avrdude.exe`.
5. **Copia las dos rutas completas** a un bloc de notas. Las vas a usar en el paso 3.9. Para copiar una ruta: clic derecho sobre el archivo manteniendo **Shift** y elige **Copiar como ruta de acceso**.

**Verifica:** abre una terminal (`cmd`) y ejecuta esto con tu ruta real de `avrdude.exe` entre comillas:

```
"C:\Users\<tu_usuario>\AppData\Local\Arduino15\packages\arduino\tools\avrdude\<version>\bin\avrdude.exe" -?
```

Debe imprimir una lista de opciones que empieza con `Usage: avrdude [options]`.

> Alternativa sin Arduino IDE: puedes bajar avrdude para Windows suelto desde su página de versiones en GitHub (`github.com/avrdudes/avrdude/releases`) y descomprimirlo. Funciona igual: necesitas su `avrdude.exe` y su `avrdude.conf`.

### 3.3 Conectar la placa y encontrar el puerto COM

Un **puerto COM** es el "nombre" que Windows le da a tu placa cuando la conectas por USB, por ejemplo `COM3`. En esta guía escribimos `COM3` como **ejemplo**: tú debes poner **el número que te salga a ti**.

1. Conecta el UNO R3 al PC con el cable USB.
2. Pulsa clic derecho en el botón de Inicio y abre **Administrador de dispositivos**.
3. Abre la sección **Puertos (COM y LPT)**.
4. Busca una línea parecida a una de estas:
   - `Arduino Uno (COM3)` (placa original)
   - `USB-SERIAL CH340 (COM5)` (clon)
5. Anota el número: ese es tu `COMx`.
6. Para comprobarlo: desconecta el cable. Esa línea debe desaparecer. Vuelve a conectar: debe regresar.

**Verifica:** tienes anotado tu puerto (por ejemplo `COM3`).

Si no aparece ninguna línea, ve a la sección 6 (puerto COM no encontrado).

### 3.4 Crear el proyecto en Microchip Studio

1. En Microchip Studio: menú **File**, luego **New**, luego **Project...**
2. En la lista de la izquierda elige **C/C++**.
3. Elige **GCC C++ Executable Project**.
4. En **Name** escribe `laberinto`.
5. En **Location** elige una carpeta **fuera** del repositorio, por ejemplo `C:\proyectos_studio\`. (Así no mezclas archivos generados con el repositorio.)
6. Deja marcada la casilla **Create directory for solution** y pulsa **OK**.
7. Se abre la ventana **Device Selection**. En el cuadro de búsqueda escribe `ATmega328P`.
8. Selecciona **ATmega328P** (no `ATmega328PB` ni `ATmega328PU`) y pulsa **OK**.

**Verifica:** a la derecha, en el **Solution Explorer**, aparece el proyecto `laberinto` con un archivo `main.cpp` generado.

Si no ves el Solution Explorer: menú **View**, luego **Solution Explorer**.

### 3.5 Agregar los archivos del robot

1. En el Solution Explorer, clic derecho sobre `main.cpp` (el que creó Studio) y elige **Remove**. Elige **Delete** si pregunta (es un archivo vacío de ejemplo).
2. Clic derecho sobre el proyecto `laberinto` (el de nivel inferior, no la solución).
3. Elige **Add**, luego **Existing Item...**
4. Navega a `C:\robot\atmega328p\laberinto\`.
5. Selecciona **todos** los archivos `.cpp` y `.h`: haz clic en el primero, mantén **Shift** y haz clic en el último. Esto incluye:

   ```
   main.cpp  twi.cpp  tiempo.cpp  motores.cpp  oled.cpp  tcs.cpp  VL53L0X.cpp
   config.h  fuente.h  twi.h  tiempo.h  motores.h  oled.h  tcs.h  VL53L0X.h
   ```

   No hace falta agregar `Makefile` ni `LICENCIA_VL53L0X.txt`.
6. Pulsa la flecha pequeña junto a **Add** y elige **Add as Link**. Con eso Studio usa los archivos originales del repositorio y tus cambios a `config.h` quedan en el repositorio. Si eliges solo **Add**, copia los archivos a la carpeta del proyecto y tendrás que editar **esas** copias.

**Verifica:** en el Solution Explorer ves los 7 archivos `.cpp` y los 7 `.h`.

### 3.6 Configurar F_CPU y la optimización

El procesador del UNO R3 corre a 16 MHz. Hay que decírselo al compilador, y pedirle que optimice el tamaño.

1. Menú **Project**, luego **laberinto Properties...** (al final del menú).
2. En la lista de la izquierda abre **Toolchain**.
3. Muy importante: arriba, en **Configuration**, elige **Release** (o **All Configurations** si existe) para que lo que cambies aplique donde compilas.
4. Entra a **AVR/GNU C++ Compiler**, luego **Symbols**.
5. En **Defined symbols (-D)** pulsa el botón de agregar (el icono de **+**) y escribe exactamente:

   ```
   F_CPU=16000000UL
   ```

6. Entra a **AVR/GNU C++ Compiler**, luego **Optimization**.
7. En **Optimization Level** elige **Optimize for size (-Os)**.
8. En la misma sección marca **Prepare functions for garbage collection (-ffunction-sections)** y **Prepare data for garbage collection (-fdata-sections)** si existen esas casillas.
9. Entra a **AVR/GNU C++ Compiler**, luego **Miscellaneous**. En **Other flags** escribe:

   ```
   -std=gnu++11 -fno-exceptions
   ```

10. Entra a **AVR/GNU Linker**, luego **General** y marca **Garbage collect unused sections (-Wl,--gc-sections)**.
11. Guarda con **Ctrl + S**.
12. Si hiciste los cambios en **All Configurations**, ya están en Debug y Release. Si no, repite los pasos 3 a 10 eligiendo la otra configuración.

(Si tu pantalla se ve distinta, busca los mismos nombres: *Symbols*, *Optimization* y *Linker*. Lo esencial es `F_CPU=16000000UL` y `-Os`.)

Estos valores son los mismos que usa el `Makefile` del repositorio: `-DF_CPU=16000000UL -Os -std=gnu++11 -ffunction-sections -fdata-sections -fno-exceptions -Wl,--gc-sections`.

**Verifica:** al volver a abrir Properties, en Symbols aparece `F_CPU=16000000UL` y en Optimization aparece `-Os`.

### 3.7 Compilar

**Compilar** es convertir el código C++ en un archivo que entiende el microcontrolador.

1. En la barra superior, junto al botón verde de play, elige la configuración **Release** en el menú que dice `Debug` o `Release`.
2. Pulsa **F7** (o menú **Build**, luego **Build Solution**).
3. Mira la ventana **Output** (abajo). Si no se ve: menú **View**, luego **Output**.
4. Debe terminar con algo parecido a:

   ```
   Build succeeded.
   ========== Build: 1 succeeded, 0 failed ==========
   ```

   Verás también un resumen de memoria (Program Memory Usage y Data Memory Usage). Para este proyecto es aproximadamente 13.8 KB de flash (42%) y 1.0 KB de RAM (50%).

Si aparecen errores (texto en rojo en la pestaña **Error List**):

- `F_CPU` redefinido: está bien, solo es un aviso. No lo cambies.
- `No such file or directory`: falta agregar un archivo (revisa 3.5).
- Cualquier otro: revisa que el dispositivo sea **ATmega328P** (3.4) y que agregaste **todos** los archivos.

### 3.8 Encontrar el archivo `.hex`

El **.hex** es el programa ya compilado, listo para grabar en la placa.

1. En el Solution Explorer, clic derecho sobre el proyecto y elige **Open Folder in File Explorer**.
2. Entra a la carpeta **Release** (o **Debug** si compilaste en Debug).
3. Busca el archivo:

   ```
   laberinto.hex
   ```

   La ruta completa se ve así (ejemplo):

   ```
   C:\proyectos_studio\laberinto\laberinto\Release\laberinto.hex
   ```

**Verifica:** existe `laberinto.hex` y su fecha y hora son de hace unos segundos.

### 3.9 Crear la herramienta externa para flashear

**Flashear** es grabar el `.hex` en la memoria de la placa. Vamos a agregar un botón en Studio que llama a avrdude.

1. Menú **Tools**, luego **External Tools...**
2. Pulsa **Add**.
3. Llena los campos así:

   | Campo | Valor |
   |---|---|
   | **Title** | `Cargar UNO R3` |
   | **Command** | la ruta completa de tu `avrdude.exe` (la que anotaste en 3.2). Puedes usar **...** para buscarla. |
   | **Arguments** | ver abajo |
   | **Initial directory** | `$(TargetDir)` |

   Y marca la casilla **Use Output window**.

4. En **Arguments** pon esto en **una sola línea**. Cambia `<ruta_conf>` por la ruta real de tu `avrdude.conf` y `COM3` por **tu** puerto:

   ```
   -C "<ruta_conf>" -c arduino -p m328p -P COM3 -b 115200 -U flash:w:"$(TargetDir)$(TargetName).hex":i
   ```

   Ejemplo completo:

   ```
   -C "C:\Users\ana\AppData\Local\Arduino15\packages\arduino\tools\avrdude\6.3.0-arduino17\etc\avrdude.conf" -c arduino -p m328p -P COM3 -b 115200 -U flash:w:"$(TargetDir)$(TargetName).hex":i
   ```

   Qué significa cada parte:

   | Parte | Significado |
   |---|---|
   | `-C "<ruta_conf>"` | Archivo de configuración de avrdude |
   | `-c arduino` | Tipo de programador: bootloader de Arduino |
   | `-p m328p` | Chip: ATmega328P |
   | `-P COM3` | Puerto: **cambia `COM3` por el tuyo** |
   | `-b 115200` | Velocidad (la del UNO R3) |
   | `-U flash:w:...:i` | Escribe (`w`) en la memoria flash el archivo `.hex` (formato Intel `i`) |
   | `$(TargetDir)` y `$(TargetName)` | Studio los reemplaza solos por la carpeta de salida (`Release\`) y el nombre (`laberinto`) |

5. Pulsa **OK**.

**Verifica:** en el menú **Tools** aparece al final `Cargar UNO R3`.

### 3.10 Flashear y comprobar

1. Compila de nuevo con **F7** si cambiaste algo.
2. Revisa que la placa siga conectada y que el puerto de la herramienta sea el correcto.
3. **Cierra** cualquier programa que use ese puerto (Monitor Serie del Arduino IDE, PuTTY, etc.). Si no, avrdude no puede abrirlo.
4. Menú **Tools**, luego **Cargar UNO R3**.
5. En la ventana **Output** debe pasar esto:

   ```
   avrdude: AVR device initialized and ready to accept instructions
   avrdude: Device signature = 0x1e950f (probably m328p)
   avrdude: writing flash (xxxxx bytes):
   Writing | ################################################## | 100%
   avrdude: verifying ...
   avrdude: xxxxx bytes of flash verified
   avrdude done.  Thank you.
   ```

   (Los números exactos varían. Lo importante es `verified` y `Thank you.`)

6. Al terminar, la placa se reinicia sola y arranca el programa.

**Verifica:** la **OLED muestra texto** (por ejemplo `LABERINTO LISTO`). Si la OLED está apagada o dice `SIN VL53L0X`, ve a la sección 6.

### 3.11 Alternativa: compilar con el Makefile

Úsala si tienes `avr-gcc` instalado (Linux, Mac o Windows con WinAVR/AVR toolchain) y `make`. El `Makefile` está en `atmega328p/laberinto/`.

1. Abre una terminal. En Windows, abre la carpeta del repositorio, entra a `atmega328p\laberinto`, haz clic en la barra de direcciones, escribe `cmd` y pulsa Enter. Se abre una terminal ya ubicada en esa carpeta.
2. En Linux o Mac:

   ```
   cd ruta/al/repositorio/atmega328p/laberinto
   ```

3. Compila:

   ```
   make
   ```

   Esto crea `laberinto.hex` en la misma carpeta.

4. Flashea (el `PUERTO` es el tuyo; en Windows se usa algo como `COM3`; en Linux suele ser `/dev/ttyACM0`):

   ```
   make cargar PUERTO=COM3
   ```

   Linux:

   ```
   make cargar PUERTO=/dev/ttyACM0
   ```

5. Para borrar lo generado:

   ```
   make clean
   ```

6. Si tu placa es un Nano con bootloader viejo, usa:

   ```
   make cargar PUERTO=COM3 BAUD=57600
   ```

Para flashear sin `make`, a mano (con `avrdude` en el PATH):

```
avrdude -c arduino -p m328p -P COM3 -b 115200 -U flash:w:laberinto.hex:i
```

**Verifica (Parte A):**

- Compila sin errores y existe `laberinto.hex`.
- avrdude termina con `Thank you.`
- La OLED enciende y muestra texto.

---

## 4. Parte B: Arduino UNO Q con App Lab

### 4.1 Qué es el UNO Q

El UNO Q es **dos computadoras en una sola placa**:

- **Un microcontrolador (STM32U585)**: corre un **sketch** de Arduino. Maneja motores, sensores, OLED y botón, igual que el R3.
- **Una computadora con Linux (Qualcomm QRB2210)**: corre un programa en **Python**. Maneja la cámara USB y calcula el mapa del laberinto.

Las dos partes se hablan por **Bridge** (4.10). Todo junto se empaqueta en una **App**. La herramienta para crear y correr Apps se llama **Arduino App Lab**.

Los pines del Q son de **3.3 V**. Por eso el puente VCC del bus I2C va en **3V3**.

### 4.2 Primer encendido

1. **Antes de conectar:** confirma que el puente VCC del bus en el proto shield está en **3V3** (si no usas el proto shield, conecta los sensores a 3.3V).
2. Conecta el Q a la PC con un cable **USB-C de datos** (no uno "solo carga"). Si el cable es malo, la placa se enciende pero la PC no la ve.
3. Espera. El Linux del Q tarda **más de un minuto** en arrancar la primera vez. Los LEDs de la placa cambian mientras arranca.
4. Para pruebas sobre la mesa, el USB-C a la PC basta. Para el robot ya armado, la alimentación va por VIN o por USB-C PD. Revisa `docs/uno_q.md`, sección 7.

**Verifica:** la placa tiene LEDs encendidos. Windows hace el sonido de dispositivo nuevo conectado.

### 4.3 Instalar Arduino App Lab

1. Abre el navegador y busca: `Arduino App Lab download`.
2. Entra a la página oficial **arduino.cc** (en la página del UNO Q o en el apartado de software hay un botón para descargar App Lab).
3. Elige la versión para **Windows** y descarga el instalador.
4. Ejecútalo y sigue el asistente.
5. Abre **Arduino App Lab** desde el menú Inicio.

**Verifica:** se abre la ventana de App Lab.

(Si tu pantalla se ve distinta, sigue el asistente.)

### 4.4 Configurar la placa la primera vez

La primera vez que abres App Lab con el Q conectado por USB, debe aparecer la placa como un dispositivo disponible y un asistente de configuración.

1. En App Lab, elige tu **UNO Q** en la lista de placas detectadas (conectada por USB).
2. Sigue el asistente. Normalmente te pide:
   - Un **nombre** para la placa (por ejemplo `robot-q`). Anótalo: lo necesitas para SSH (4.9).
   - Un **usuario y contraseña** para el Linux de la placa. Anótalos: son tu acceso a la terminal. Esta guía usa el usuario `arduino` como ejemplo; usa el que tú creaste.
   - Los datos de tu red **Wi-Fi** (nombre y contraseña). Sirve para actualizaciones y para entrar por SSH. En la competencia puede no haber Wi-Fi: el robot funciona igual sin ella.
3. Deja que App Lab instale las **actualizaciones** que ofrezca (del núcleo del microcontrolador y herramientas). Puede tardar varios minutos. No desconectes la placa.
4. Cuando termine, la placa aparece como conectada.

(Si tu pantalla se ve distinta, sigue el asistente.)

**Verifica:** App Lab muestra tu Q como conectada y no hay avisos de error.

### 4.5 Crear la App

1. En App Lab busca la opción para **crear una App nueva** (suele haber un botón o enlace de tipo "Create new app" / "Nueva app"; si no lo ves, revisa el menú principal de App Lab).
2. Ponle de nombre exactamente `Laberinto`.
3. App Lab crea una carpeta con una App de ejemplo. Un App tiene dos archivos principales:
   - Un **sketch** (`sketch.ino`, en una carpeta `sketch/`): código del microcontrolador.
   - Un programa **Python** (`main.py`, en una carpeta `python/`): código de Linux.
4. En el panel izquierdo de la App ves esos archivos. Si no los ves, haz clic en el nombre de la App.

(Si tu pantalla se ve distinta, sigue el asistente.)

**Verifica:** la App `Laberinto` está abierta y ves una pestaña de sketch y una de Python.

### 4.6 Copiar los archivos del repositorio

Vas a **reemplazar** el contenido de los archivos de ejemplo por los del repositorio.

| Copia desde el repositorio | Pégalo en la App |
|---|---|
| `uno_q\sketch\sketch.ino` | El archivo del sketch (`sketch.ino`) |
| `uno_q\python\main.py` | `main.py` |
| `uno_q\python\requirements.txt` | `requirements.txt` (si no existe en la App, créalo con el mismo nombre en la carpeta `python/`) |
| `uno_q\app.yaml` | Normalmente **no** hace falta: App Lab ya creó el suyo al nombrar la App `Laberinto` |

Cómo hacerlo:

1. En el Explorador de archivos abre `C:\robot\uno_q\sketch\sketch.ino` con el **Bloc de notas**.
2. Pulsa **Ctrl + A** (seleccionar todo) y **Ctrl + C** (copiar).
3. En App Lab abre la pestaña del sketch, pulsa **Ctrl + A** y luego **Ctrl + V** (pegar). Esto reemplaza todo.
4. Repite con `main.py`.
5. Repite con `requirements.txt`. Su contenido es una sola línea:

   ```
   opencv-python-headless
   ```

6. Guarda con **Ctrl + S** en cada archivo.

**Verifica:** el sketch empieza con `#include <Arduino_RouterBridge.h>` y `main.py` empieza con `from arduino.app_utils import *`.

### 4.7 Agregar las librerías del sketch

El sketch usa librerías que hay que instalar una vez.

1. En App Lab, en el sketch, busca el apartado de **Librerías** (Libraries). Suele estar en un panel o botón cerca del editor del sketch.
2. Busca e instala **cada una** de estas (escribe el nombre en el buscador):

   | Librería | Nota |
   |---|---|
   | `Adafruit SSD1306` | Pantalla OLED |
   | `Adafruit GFX Library` | Dibujo para la OLED. Si pregunta por dependencias, acepta instalarlas todas |
   | `Adafruit TCS34725` | Sensor de color |
   | `VL53L0X` | Debe ser la de **Pololu** (revisa el autor) |

3. `Arduino_RouterBridge` y `Wire` ya vienen con la plataforma del Q: no las instales a mano.

(Si tu pantalla se ve distinta, sigue el asistente.)

**Verifica:** las cuatro librerías aparecen en la lista de instaladas.

### 4.8 Correr la App (Run) y leer los logs

1. Con la placa conectada, pulsa el botón **Run** (el botón de play, arriba a la derecha de App Lab).
2. App Lab hace tres cosas, en este orden:
   - Compila el sketch.
   - Lo carga al microcontrolador.
   - Arranca el programa Python en el Linux de la placa.
3. La primera vez puede tardar varios minutos (se instalan paquetes de Python como OpenCV). Espera. No desconectes.
4. Lee los **logs** (mensajes) en el panel inferior de App Lab:
   - La pestaña del **Monitor** muestra lo que escribe el sketch con `Monitor.print(...)` (por ejemplo, los valores de color y distancia en el modo calibración).
   - La pestaña de la **consola de Python** (o de la App) muestra lo que imprime `main.py` y los errores de Python.
5. Para **detener** la App, pulsa el botón **Stop** (aparece donde estaba Run mientras la App corre).
6. Si quieres que arranque sola al encender la placa, marca la App como de **arranque automático**. Primero asegúrate de que funcione bien con Run.

(Si tu pantalla se ve distinta, sigue el asistente.)

**Verifica (Parte B, App):**

- Run termina sin errores de compilación.
- La OLED enciende y muestra texto.
- En los logs no aparece `SIN VL53L0X`. Si aparece `SIN CAM`, solo falta la cámara: el robot funciona sin ella.

### 4.9 Abrir una terminal en el Q

Necesitas la terminal para revisar la cámara y ver por qué algo falla.

**Opción 1: terminal dentro de App Lab.** Busca en App Lab una terminal integrada (suele haber una pestaña o botón de terminal / shell). Si existe, ya estás dentro del Linux de la placa.

(Si tu pantalla se ve distinta, sigue el asistente.)

**Opción 2: SSH desde Windows.** La placa y la PC deben estar en la **misma red Wi-Fi**.

1. Abre `cmd` (tecla Windows, escribe `cmd`, Enter).
2. Escribe (cambia `arduino` por tu usuario y `robot-q` por el nombre que le diste a la placa en 4.4):

   ```
   ssh arduino@robot-q.local
   ```

3. La primera vez pregunta si confías en la placa. Escribe `yes` y pulsa Enter.
4. Escribe la contraseña de Linux que creaste. **Al escribirla no se ve nada**, ni puntitos. Es normal. Pulsa Enter.
5. Cuando veas un prompt como `arduino@robot-q:~$`, ya estás dentro.
6. Para salir:

   ```
   exit
   ```

Si `.local` no funciona, usa la dirección IP de la placa (se ve en la configuración de red de App Lab o en la página de tu router): `ssh arduino@192.168.1.50` (ejemplo).

**Revisar la cámara USB** (ya dentro de la terminal del Q, con la cámara conectada al hub):

```
lsusb
```

Debe aparecer una línea con el nombre del fabricante de tu cámara (o `UVC`/`Camera`).

```
v4l2-ctl --list-devices
```

Debe mostrar tu cámara con una ruta como `/dev/video0`. Si el comando dice `command not found`, instálalo (necesita Wi-Fi):

```
sudo apt update
sudo apt install -y v4l-utils
```

Pide la contraseña de Linux (tampoco se ve al escribir).

**Verifica:** `v4l2-ctl --list-devices` muestra la cámara con `/dev/video0`. El código usa `CAM_ID = 0` (es decir, `/dev/video0`). Si tu cámara sale con otro número, cámbialo en `main.py`.

### 4.10 Cómo funciona Bridge (en dos frases y un ejemplo)

**Bridge** es el "teléfono" entre el microcontrolador y Python: una de las partes **ofrece** una función con un nombre (`Bridge.provide`) y la otra la **llama** por ese nombre (`Bridge.call`). Python le pide cosas al microcontrolador ("avanza una celda") y recibe el resultado.

Mini ejemplo:

Lado sketch (microcontrolador), en `setup()`:

```cpp
int rpcSuma(int a, int b) {
  return a + b;
}

void setup() {
  Bridge.begin();
  Bridge.provide("suma", rpcSuma);   // ofrece la función con el nombre "suma"
}
```

Lado Python (Linux):

```python
resultado = Bridge.call("suma", 2, 3)   # llama a "suma" con 2 y 3
print(resultado)                        # imprime 5
```

En este proyecto se usa igual: el sketch ofrece `mover`, `girar`, `paredes`, `color`, etc., y `main.py` llama, por ejemplo, `Bridge.call("mover", n, rapido)`.

**Verifica (Parte B completa):** Run funciona, la OLED muestra texto, `v4l2-ctl --list-devices` ve la cámara.

---

## 5. Calibración

Los valores de fábrica son aproximados. Con tu robot, tus ruedas y tu batería hay que ajustarlos.

### 5.1 Entrar al modo calibración

1. Apaga el robot.
2. **Mantén presionado el botón** (el de D2).
3. Enciende el robot sin soltar el botón.
4. Suelta el botón cuando la OLED diga `CALIBRACION`.

En el UNO R3 esto lo hace el firmware. En el UNO Q el sketch también lo hace (enciéndelo con el botón presionado con la App corriendo o arrancando).

### 5.2 Qué hacer en el modo calibración

La pantalla muestra:

- Líneas `r`, `g`, `b` (proporciones de color en %) y `c` (brillo), y al lado el color que cree ver (PISO, ROJO, VERDE, AZUL o AMAR).
- Al final, las 3 distancias en milímetros: izquierda, frente y derecha.

Qué hacer, en orden:

1. **Colores.** Pon el sensor de color sobre el piso y anota `r g b c`. Repite sobre cada marca de color (rojo, verde, azul, amarillo). En `config.h` hay una tabla `refs[]` con una línea por color: `{"ROJO", r, g, b, c}`. Pon ahí tus valores. **Ojo:** en la OLED `r g b` aparecen como porcentaje (por ejemplo `58`); en `refs[]` van como decimal (`0.58`).
2. **Distancias.** Pon el robot **centrado** en una celda con paredes a los lados y al frente. Anota las distancias:
   - La del lado (izquierda o derecha) es `D_LADO`.
   - La del frente es `D_FRENTE`.
3. **Avanza 1 celda.** Da un pulso **corto** al botón: el robot avanza una celda (18 cm). Mide si avanzó 18 cm. Si se quedó corto, sube `T_CELDA`; si se pasó, bájalo.
4. **Gira 90.** Mantén el botón **sostenido** (más de 0.1 s): el robot gira 90 grados a la derecha. Si giró de menos, sube `T_90`; si de más, bájalo.
5. Si el robot se desvía hacia un lado al avanzar recto, ajusta `AJUSTE_DER`.
6. Calibra con la **batería cargada**: con poca carga los motores van más lento y todo cambia.

### 5.3 Constantes que vas a tocar

En el R3 están en `atmega328p/laberinto/config.h`. En el Q están al inicio de `uno_q/sketch/sketch.ino`.

| Constante | Qué significa | Valor en R3 (`config.h`) |
|---|---|---|
| `T_CELDA` | Tiempo para avanzar una celda de 18 cm (ticks de 10 ms). En el Q se llama `MS_CELDA` y va en milisegundos | 60 |
| `T_90` | Tiempo para un giro de 90 grados (ticks). En el Q: `MS_90` | 25 |
| `T_RAPIDA` | Igual que `T_CELDA` pero en corridas rápidas. En el Q: `MS_RAPIDA` | 40 |
| `PARED` | Distancia en mm: si la lectura es menor, hay pared | 120 |
| `D_FRENTE` | Distancia en mm al frente con el robot centrado | 34 |
| `D_LADO` | Distancia en mm a una pared lateral con el robot centrado | 38 |
| `AJUSTE_DER` | PWM extra al motor derecho para corregir desvío | 0 |
| `refs[]` | Referencias de color (r, g, b normalizados y brillo c) | ver `config.h` |

Ejemplo: `T_CELDA = 60` significa 60 ticks de 10 ms, es decir 600 ms por celda.

En el UNO Q, además, la cámara tiene su propia calibración en `main.py` (`ROI`, `PARED_LO/HI`, `UMBRAL`): ver `uno_q/README.md`, sección Calibración.

### 5.4 Recompilar y volver a flashear después de cambiar una constante

Un cambio en el código **no** hace efecto hasta que recompilas y flasheas otra vez.

**UNO R3 con Microchip Studio:**

1. Abre `config.h` en Studio (doble clic en el Solution Explorer).
2. Cambia el valor. Ejemplo:

   ```cpp
   const uint16_t T_CELDA = 62;
   ```

3. Guarda con **Ctrl + S**.
4. Compila con **F7** y espera `Build succeeded`.
5. Menú **Tools**, luego **Cargar UNO R3**.

**UNO R3 con Makefile:**

```
make
make cargar PUERTO=COM3
```

**UNO Q:** edita el valor en el sketch dentro de App Lab, guarda y pulsa **Run** de nuevo (si la App ya corre, primero **Stop**).

**Verifica:** el robot ahora avanza 18 cm y gira 90 grados con tus valores. Si no, repite 5.2 con un cambio pequeño cada vez (de 2 a 5 unidades).

---

## 6. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| No aparece ningún puerto COM en el Administrador de dispositivos | Cable de solo carga, cable dañado o falta el driver | Prueba otro cable USB **de datos** y otro puerto USB. Si es un clon con chip CH340, instala el driver **CH340** (busca `driver CH340 Windows`). El UNO R3 original usa un chip ATmega16U2 y Windows lo reconoce solo |
| El puerto aparece como "Dispositivo desconocido" con signo de advertencia | Driver faltante (clon CH340) | Instala el driver CH340, desconecta y vuelve a conectar la placa |
| avrdude: `can't open device "\\.\COM3"` | Puerto equivocado u ocupado por otro programa | Revisa el número en el Administrador de dispositivos. Cierra Monitor Serie, PuTTY y cualquier otro programa que use el puerto |
| avrdude: `stk500_recv(): programmer is not responding` o `not in sync: resp=0x00` | Placa equivocada, velocidad equivocada, puerto equivocado, o algo conectado a los pines D0/D1 | Verifica `-P` (puerto) y `-b 115200` (usa `-b 57600` si es un Nano viejo). Desconecta lo que esté en D0 y D1. Prueba pulsar el botón de reset justo al iniciar la carga. Confirma que el cable sea de datos |
| avrdude: `Device signature = 0x000000` o `0xffffff` | No hay comunicación con el chip | Mismo caso que arriba. Revisa cable, puerto y que la placa sea un R3/Nano con ATmega328P |
| avrdude: `cannot open config file` | Ruta de `avrdude.conf` mal escrita | Revisa el valor de `-C`. Debe ir entre comillas y apuntar al archivo `avrdude.conf` que existe |
| La herramienta externa no hace nada | Falta la casilla **Use Output window** o el `Command` está mal | Edita la herramienta en **Tools > External Tools**, revisa que `Command` apunte a `avrdude.exe` y marca **Use Output window** |
| Studio no encuentra el `.hex` | Compilaste en otra configuración (Debug en vez de Release) | Compila de nuevo y abre la carpeta de salida que corresponda. `$(TargetDir)` apunta a la configuración activa |
| OLED en blanco | Cable SDA/SCL invertido, falta alimentación del bus, puente VCC mal, o dirección I2C distinta | Revisa SDA y SCL, GND común, que el puente VCC del bus esté en 5V (R3) o 3V3 (Q). Revisa que el módulo sea un SSD1306 de 128x64 |
| OLED dice `SIN VL53L0X` | Un sensor de distancia no responde | Revisa que los tres XSHUT estén en A0, A1 y A2; que SDA/SCL y VCC lleguen a los tres sensores; y que no haya cables flojos. Los tres sensores deben alimentarse con el voltaje correcto de tu placa |
| OLED dice `SIN CAM` (solo Q) | El programa Python no ve la cámara | Es un aviso: el robot funciona sin cámara. Para arreglarlo revisa la sección siguiente |
| La cámara no se detecta en el Q (`lsusb` no la lista) | Alimentación por VIN: el USB-C puede quedar en modo dispositivo y no ve la cámara. Cable o hub defectuoso | Pruébala con el Q alimentado por **USB-C con hub PD** en vez de VIN. Revisa `docs/uno_q.md`, secciones 7 y 12. Prueba otro hub o cable |
| App Lab no encuentra la placa | Cable de solo carga, la placa aún está arrancando, o falta permiso en la PC | Usa un cable **de datos**, espera 1 a 2 minutos tras conectar, prueba otro puerto USB y reinicia App Lab. En Windows, si pide permiso o driver, acéptalo |
| Run falla compilando el sketch | Falta una librería | Revisa la sección 4.7. Instala las cuatro librerías y vuelve a pulsar Run |
| Puente VCC del bus en la posición equivocada | Se cambió de placa sin mover el puente | **R3: 5V. Q: 3V3.** Con 5V en el Q se dañan sus pines I2C. Apaga todo antes de moverlo |
| El robot avanza más o menos de una celda | Valores de calibración sin ajustar | Haz la sección 5 con la batería cargada |
| El robot se detiene a media celda sin razón | Batería baja (VIN necesita al menos 7 V) | Recarga la batería al llegar a 7.2 V |

(Los mensajes de avrdude pueden variar un poco según la versión.)

---

## 7. Glosario

| Término | Qué significa |
|---|---|
| **Firmware** | El programa que vive dentro del microcontrolador y se ejecuta al encender |
| **.hex** | Archivo con el programa ya compilado, listo para grabarse en la placa |
| **Compilar** | Convertir el código escrito (C++) en un archivo que entiende el microcontrolador (`.hex`) |
| **Flashear** | Grabar el `.hex` en la memoria de la placa |
| **avrdude** | Programa que flashea el `.hex` por USB |
| **Terminal** | Ventana donde escribes comandos de texto (`cmd` en Windows, la terminal de la placa en el Q) |
| **Puerto COM** | El nombre (por ejemplo `COM3`) que Windows da a la placa conectada por USB. En esta guía `COM3` es solo un ejemplo |
| **I2C** | Cable de dos hilos (SDA y SCL) por el que hablan la OLED y los sensores con la placa |
| **XSHUT** | Pin que enciende o apaga cada sensor VL53L0X; permite darle a cada uno una dirección I2C distinta |
| **PWM** | Pulsos que se encienden y apagan muy rápido para controlar la velocidad de un motor (pines ENA y ENB) |
| **Sketch** | Programa de Arduino para el microcontrolador (archivo `.ino`) |
| **Bridge** | Comunicación entre el microcontrolador y Python en el UNO Q: una parte ofrece funciones con `provide` y la otra las llama con `call` |
| **App** | En App Lab, el paquete que junta un sketch y un programa Python |
| **App Lab** | Programa de Arduino para crear y correr Apps en el UNO Q |
| **SSH** | Forma de abrir una terminal en la placa desde tu PC por la red |
| **Repositorio** | Carpeta con todos los archivos del proyecto, guardada en GitHub |
