#include <Arduino_RouterBridge.h>
#include <Wire.h>
#include <VL53L0X.h>
#include "oled.h"
#include <Adafruit_TCS34725.h>

// ---------- Pines ----------
// Mismo mapa que el R3: se cambia de placa sin mover un dupont
#define ENA 5
#define ENB 6
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 10
#define BTN 2
const uint8_t XSHUT[3] = {A0, A1, A2};   // izq, frente, der

// ---------- Calibracion ----------
long msCelda = 700;           // ms por celda de 18 cm (solo si el frontal no ve pared: avanza por tiempo; con 600 hacia 15-16 cm).
                              // Se calibra desde la web (avance de prueba de 10 cm) y Python lo manda al arrancar: set_ms
const long MS_90 = 250;       // ms por giro de 90 grados (solo sin MPU-6050)
const int VEL_EXPLORA = 140;
const int VEL_LENTO = 100;    // cuando la camara ve blanco (pared) en el camino
const int VEL_GIRO = 130;
const int VEL_MIN = 80;
const int AJUSTE_DER = -10;   // PWM de diferencia: negativo = mas fuerza al motor izquierdo (en pista se iba a la izquierda)
const bool INV_IZQ = true;    // true si ese motor gira al reves (en vez de voltear cables)
const bool INV_DER = true;
const int PARED = 120;        // mm: lectura menor = hay pared (lados)
// Geometria del chasis (CAD, origen en el eje de las ruedas): frontal 54 mm adelante del eje; laterales a 43 mm del
// centro y 40 adelante. Celda de 180 con paredes de 12: del centro de la celda a la cara de la pared hay 84 mm.
const int MEDIA_CELDA = 84;
const int TOF_F_Y = 54, TOF_L_X = 43, TOF_L_Y = 40;
const int PARED_F = 55;       // mm reales (frontal calibrado): menos de esto = pared en su celda
const int D_FRENTE = MEDIA_CELDA - TOF_F_Y;   // 30 mm reales: el frontal lee esto con el eje al centro de la celda
const int D_CERCA = 5;        // mm: si queda mas de esto por debajo de D_FRENTE, se hace para atras
const int FRENA_K = 2;        // PWM por mm: con pared al frente baja la velocidad al acercarse
const int D_LADO = MEDIA_CELDA - TOF_L_X;     // 41 mm: cada lateral con el robot centrado en el carril
const float KC = 0.8;         // ganancia de centrado
const float KD = 0;           // ganancia de rumbo segun que tan rapido se acerca a una pared (en simulacion 0.3 torcia el rumbo)
const int CELDA = 180;        // mm de centro a centro de celda
const int RANGO = 250;        // v2: el frontal solo de cerca (pared en su celda o la siguiente). Su cono de 25 grados ve las paredes
                              // laterales desde ~300-400 mm (en pista leyo 407 con la pared a 4 celdas): mas lejos no mide el pasillo
const int SALTO = 120;        // mm: cambio brusco entre 2 lecturas (50 -> 200, 100 -> 300)
const int TRAS_SALTO = CELDA / 2 + TOF_L_Y - 45;  // v2: 85 mm tras acabarse una pared lateral: centro de esa celda. Menos que en v1 (110): el umbral
                              // la detecta antes que el salto brusco, y son 2 lecturas de confirmacion. CALIBRAR EN PISTA: en simulacion sirve de 75 a 95;
                              // si al parar en una abertura queda adelantado, baja; si queda atras, sube
const int TRAS_CIERRA = CELDA / 2 + TOF_L_Y - 15; // v2: 115 mm tras EMPEZAR una pared lateral (poco sensible: de 105 a 135 da igual en simulacion)
const uint32_t T_CTRL = 10;
const uint32_t T_COLOR = 30;

// ---------- Colores ----------
// r, g, b normalizados (r/(r+g+b)) y brillo c. Llenar con el modo calibracion.
struct Ref { const char* nom; float r, g, b, c; };
Ref refs[] = {
  {"PISO",  0.282, 0.379, 0.333, 153},
  {"ROJO",  0.602, 0.208, 0.188, 581},
  {"VERDE", 0.155, 0.535, 0.309, 636},
  {"AZUL",  0.16, 0.329, 0.508, 354},
  {"AMAR",  0.409, 0.449, 0.142, 1836},
};
const int NCOL = sizeof(refs) / sizeof(refs[0]);
const float DIST_MAX = 0.02;
const float BRILLO_MIN = 1.3;  // piso negro: una marca refleja al menos 1.3x mas que el piso (quita falsos positivos)

Oled oled(128, 64, &Wire, -1);
Adafruit_TCS34725 tcs(TCS34725_INTEGRATIONTIME_24MS, TCS34725_GAIN_4X);
VL53L0X tof[3];
int dist[3] = {9999, 9999, 9999};
int crudo[3] = {9999, 9999, 9999};   // lectura sin calibrar
float tofA[3] = {1, 1, 1}, tofB[3] = {0, 0, 0};   // mm reales = A * crudo + B (los manda Python, calibrados con vernier)
bool tofOk = false;

enum { NADA, AVANZA, GIRA, CENTRA };
volatile int cmd = NADA;
volatile int arg = 0;
volatile bool alin = false;   // el GIRA en curso es una alineacion: no mueve el rumbo deseado
volatile int ocupado = 0;
volatile int colorPend = 0;
volatile int arranque = 0;
volatile int refresca = 1;
volatile uint32_t nRpc = 0;   // sube cada vez que Python pregunta: si no cambia, Python no corre
volatile char ult = '-';
volatile int pideAlto = 0;    // Python pide parar ya (encontro el amarillo)

int cuenta[NCOL] = {0};
int estado = 0;
const char* ESTADOS[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "BORRADO", "SIN CAM"};
const char* FASES[] = {"", "SENSA", "DECIDE", "GIRA", "AVANZA", "ESCANEA"};
int fase = 0;
const int AMAR = 4;           // refs[4]: la meta; el sketch para solo, sin esperar al Python

int tipo = NADA;
int dirL, dirR;
long dur;
bool soloTiempo = false;      // avance de prueba: por tiempo aunque vea pared (calibra msCelda)
long total;                   // mm del avance en curso
long pedido;                  // mm que pidio Python (tope de saltos)
int objetivo = -1;            // lectura del frontal donde parar; -1 = no ve pared, va por tiempo
long hecho = 0;               // mm que recorrio el ultimo avance
int vmax = VEL_EXPLORA;
int saltos = 0;               // ToF que saltaron hacia lejos en este avance (1 izq, 2 frente, 4 der)
int cierres = 0;              // v2: laterales donde empezo una pared en este avance (1 izq, 4 der)
// v2: pared lateral "de carril" = la de su propia celda. Con el robot de 120 en un carril de 168 el lateral lee de 17 a 65 mm;
// mas de eso NO es su pared: es la del pasillo perpendicular que el cono alcanza al pasar una abertura (lee 80-120 mm).
// Centrarse con esa lectura jalaba el robot hacia la abertura hasta chocar.
const int CARRIL_SI = 75, CARRIL_NO = 95;   // mm: empieza pared por debajo de 75, se acaba por encima de 95 (2 lecturas seguidas)
bool lado[3];                 // hay pared de carril a ese lado (1 no se usa)
int nLado[3];
uint32_t tQuieto = 0;         // v2: desde cuando esta quieto (recalibra la deriva del giroscopio)
uint32_t tLat = 0;            // v2: rumbo con una pared lateral: inicio de la ventana, lecturas al inicio, que lados siguen con pared
int lat0[2];
bool latOk[2];
float devLat;
int nLat;
int nSalto[3];                // lecturas seguidas con cambio brusco (cuenta a la 2a: una lectura mala no)
uint32_t tIni;
float vel;
int dMin;                     // menor distancia al frente en este avance
uint32_t tBaja;               // ultima vez que bajo: si ya no baja con pared enfrente, esta empujando la pared

// ---------- MPU-6050 (opcional) ----------
// Si responde en 0x68 al arrancar, gira por angulo y sostiene el rumbo en recta; si no, todo va por tiempo.
const uint8_t MPU_ADDR = 0x68;   // no "MPU": es una macro de CMSIS (la unidad de proteccion de memoria del Cortex-M33)
const float LSB_DPS = 65.5;   // +-500 grados/s
const float ADELANTO = 6;     // grados: corta el giro antes por la inercia (calibrar: si se pasa, sube)
const float KG = 2.0;         // PWM por grado de desvio en recta
bool mpuOk = false;
float yaw = 0, bias = 0;      // grados con el signo del montaje
int signo = 0;                // +1/-1 segun como quedo montado; lo aprende en el primer giro (0 = aun no)
float ref = 0;                // rumbo deseado (derecha +), valido con signo conocido
float yaw0;                   // yaw al iniciar el giro
uint32_t tGyro;
// Acelerometro: choques, robot levantado. Giroscopio: giro atorado
const float CHOQUE_G = 1.5;   // g: golpe horizontal sobre el promedio que hace sospechar un choque (calibrar con el log)
const float CHOQUE_FUERTE = 2.5;  // g: sin pared enfrente para confirmarlo, solo un golpe asi cuenta como choque
const int CONFIRMA_MS = 250;  // ms despues del golpe: si el frontal no bajo 10 mm, el robot esta trabado = choque
const float LEVANTA_G = 0.8;  // g: si la vertical baja de esto 150 ms seguidos, lo levantaron o se volteo
const int RETRO_MS = 450;     // ms para atras despues de un choque (a VEL_RETRO)
const int VEL_RETRO = 110;
const int ATORADO_MS = 400;   // ms girando sin que el giroscopio vea 2 grados: atorado contra la pared
float axF = 0, ayF = 0, pico = 0;
int choque = 0, levantado = 0, atorones = 0;
uint32_t tRetro = 0, tLev = 0, tGiroMov = 0, tDes = 0, tChoque = 0;
int fChoque = 0;
float yawMov = 0;

// ---------- RPC desde Python ----------
int rpcMover(int mm, int lento) {
  ult = 'M';
  if (ocupado) return 0;
  arg = mm;
  vmax = lento ? VEL_LENTO : VEL_EXPLORA;
  cmd = AVANZA;
  ocupado = 1;
  return 1;
}

int eCarril = 0;              // error de centrado actual (mm; 0 = centrado) y si hay pared a los 2 lados
bool hayCarril = false;
uint32_t tParalelo = 0;       // desde cuando va centrado y paralelo a las paredes (para corregir la deriva del MPU)
int eCen;                     // centrado: error anterior, su cambio en mm/s y cuando se midio
float deCen;
unsigned long tCen;

int rpcGirar(int cuartos) {
  ult = 'G';
  if (ocupado) return 0;
  arg = cuartos * 90;           // GIRA va en grados
  cmd = GIRA;
  ocupado = 1;
  return 1;
}

// Corrige el rumbo g grados (derecha +) con lo que ve la camara antes de avanzar.
// Con MPU y signo conocido no gira: mueve el rumbo deseado y la recta lo sostiene (el giroscopio derivo).
// Si no, gira en su lugar; devuelve 2 si hay que esperar el giro, 1 si no.
// Con MPU: gira en su lugar hasta el rumbo deseado si se desvio ALIN_MIN grados o mas y no mas de lim
// (antes de avanzar lim = 45: mas es una lectura mala; tras un giro fallido lim = 180). 2 = hay que esperar.
const float ALIN_MIN = 3;
int rpcAlinear(int lim) {
  ult = 'A';
  if (ocupado || !(mpuOk && signo)) return 0;
  float e = ref - signo * yaw;
  if (fabs(e) < ALIN_MIN || fabs(e) > lim) return 0;
  arg = (int)roundf(e);
  if (arg == 0) return 0;
  alin = true;
  cmd = GIRA;
  ocupado = 1;
  return 2;
}

int rpcAjustar(int g) {
  ult = 'J';
  if (ocupado || g == 0) return 0;
  if (mpuOk && signo) { ref = signo * yaw + g; return 1; }
  arg = g;
  cmd = GIRA;
  ocupado = 1;
  return 2;
}

// Con pared enfrente a menos de lim mm: avanza o retrocede hasta quedar a D_FRENTE + k celdas de ella (centro de celda).
// 2 = hay que esperar, 0 = no hace falta.
int rpcCentrar(int lim) {
  ult = 'C';
  if (ocupado || dist[1] >= lim) return 0;
  arg = lim;
  cmd = CENTRA;
  ocupado = 1;
  return 2;
}

// Avance de prueba por tiempo (para calibrar msCelda desde la web): mm a msCelda, sin usar el frontal para medir
int rpcMoverT(int mm) {
  if (ocupado) return 0;
  soloTiempo = true;             // antes de pedir el avance: iniciaMov ya lo ve
  return rpcMover(mm, 0);
}

// v2: el signo del giroscopio depende de como quedo montado y no cambia. Antes se aprendia en el primer giro de cada
// arranque, asi que el primer tramo iba sin rumbo (en pista se desvio ~18 grados en 27 cm). Python lo guarda y lo manda
// al arrancar. s = 1 o -1 lo fija; 0 solo lo consulta.
int rpcSigno(int s) {
  if ((s == 1 || s == -1) && !ocupado) { signo = s; ref = signo * yaw; }
  return signo;
}

int rpcSetMs(int ms) {
  if (ms >= 200 && ms <= 2000) msCelda = ms;
  return msCelda;
}

int rpcOcupado() { return ocupado; }

int rpcAlto() {
  pideAlto = 1;
  return 1;
}

// mm que faltan: con pared a la vista lo dice el frontal, si no el tiempo
long falta() {
  if (tipo != AVANZA) return 0;
  long f = objetivo >= 0 ? dist[1] - objetivo : total - total * (long)(millis() - tIni) / dur;
  return constrain(f, 0L, total);
}

// 0 mm recorridos (en curso o el ultimo avance), 1 mm que faltan, 2 paredes (1 izq, 2 frente, 4 der,
// 8 en movimiento), 3 saltos del avance, 5/6/7 distancia frente/izq/der (mm)
int rpcOdo(int i) {
  switch (i) {
    case 0: return tipo == AVANZA ? total - falta() : hecho;
    case 1: return falta();
    case 2: return (dist[0] < PARED) | (dist[1] < PARED_F) << 1 | (dist[2] < PARED) << 2 | (tipo != NADA) << 3;
    case 3: return saltos;
    case 8: return signo ? (int)(signo * yaw - ref) : 0;   // desvio del rumbo deseado (grados)
    case 12: return choque;                                  // el ultimo avance choco
    case 13: return atorones;                                // veces que el ultimo giro se atoro
    case 14: { int l = levantado; levantado = 0; return l; } // lo levantaron (se borra al leerlo)
    case 15: return (int)(pico * 1000);                      // golpe maximo del ultimo avance (mg)
    case 17: return cierres;                                 // v2: laterales donde empezo pared en el ultimo avance
    case 18: return min(dist[0], 1023) << 20 | min(dist[1], 1023) << 10 | min(dist[2], 1023);   // v2: los 3 ToF en una llamada (grabacion)
    case 16: return signo ? (int)lroundf((signo * yaw - ref) * 10) : 0;   // desvio en decimas de grado (barrido de cuadrar)
    case 9: case 10: case 11: return crudo[i - 9];           // izq, frente, der sin calibrar
    case 6: return dist[0];
    case 7: return dist[2];
    default: return dist[1];
  }
}

int rpcColor() {
  int c = colorPend;
  colorPend = 0;
  return c;
}

volatile uint16_t raw[4];   // r g b c de la ultima lectura (para el dashboard)

int rpcRaw(int i) { return raw[constrain(i, 0, 3)]; }

// a en milesimas, b en decimas de mm
int rpcSetTof(int i, int a, int b) {
  if (i < 0 || i > 2) return 0;
  tofA[i] = a / 1000.0f;
  tofB[i] = b / 10.0f;
  return 1;
}

// r, g, b en milesimas
int rpcSetRef(int i, int r, int g, int b, int c) {
  if (i < 0 || i >= NCOL) return 0;
  refs[i].r = r / 1000.0f; refs[i].g = g / 1000.0f; refs[i].b = b / 1000.0f; refs[i].c = c;
  return 1;
}

int rpcArranque() {
  nRpc++;
  int a = arranque;
  arranque = 0;
  return a;
}

int rpcCuenta(int idx, int n) {
  if (idx > 0 && idx < NCOL) cuenta[idx] = n;
  refresca = 1;
  return 1;
}

int rpcFase(int f) {
  fase = constrain(f, 0, 5);
  refresca = 1;
  return 1;
}

int rpcEstado(int e) {
  estado = constrain(e, 0, 6);
  refresca = 1;
  return 1;
}

// ---------- Motores ----------
void motores(int l, int r) {
  if (INV_IZQ) l = -l;
  if (INV_DER) r = -r;
  digitalWrite(IN1, l >= 0);
  digitalWrite(IN2, l < 0);
  digitalWrite(IN3, r >= 0);
  digitalWrite(IN4, r < 0);
  analogWrite(ENA, constrain(abs(l), 0, 255));
  analogWrite(ENB, constrain(abs(r), 0, 255));
}

void frena() {
  digitalWrite(IN1, HIGH); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, HIGH);
  analogWrite(ENA, 255); analogWrite(ENB, 255);
  delay(60);
  analogWrite(ENA, 0); analogWrite(ENB, 0);
}

void iniciaMov() {
  tIni = millis();
  vel = VEL_MIN;
  tipo = cmd;
  if (cmd == AVANZA) {
    dirL = dirR = 1;
    total = pedido = max((long)arg, 1L);
    dur = max(total * msCelda / CELDA, 50L);
    objetivo = dist[1] < RANGO && !soloTiempo ? max(dist[1] - (int)total, D_FRENTE) : -1;
    if (objetivo >= 0 && dist[1] - total < D_FRENTE) total = max(dist[1] - D_FRENTE, 0);   // pared antes: solo cuenta lo que cabe
    saltos = 0;
    cierres = 0;
    for (int i = 0; i < 3; i += 2) { lado[i] = dist[i] < (CARRIL_SI + CARRIL_NO) / 2; nLado[i] = 0; }
    tLat = 0;
    choque = 0;
    pico = 0;
    tRetro = 0;
    tChoque = 0;
    dMin = 9999;
    tBaja = millis();
    tCen = 0;
  } else if (cmd == CENTRA) {
    objetivo = D_FRENTE + CELDA * (int)lroundf((dist[1] - D_FRENTE) / (float)CELDA);
  } else {
    dirL = arg > 0 ? 1 : -1;
    dirR = -dirL;
    dur = max(abs(arg) * MS_90 / 90, 30L);
    yaw0 = yaw;
    yawMov = yaw;
    tGiroMov = millis();
    tDes = 0;
    atorones = 0;
    if (signo && !alin) ref += arg;
    alin = false;
  }
  cmd = NADA;
}

// Deja el avance con f mm por recorrer (antes faltaban fAntes): por el frontal o, sin pared a la vista, por tiempo
void faltan(long fAntes, long f) {
  total += f - fAntes;
  if (dist[1] < RANGO && !soloTiempo) {
    objetivo = max(dist[1] - (int)f, D_FRENTE);
    if (dist[1] - f < D_FRENTE) total -= f - max(dist[1] - D_FRENTE, 0);
  } else {
    objetivo = -1;
    tIni = millis() - (total - f) * msCelda / CELDA;
    dur = max(total * msCelda / CELDA, 50L);
  }
}

// Cambio brusco en un ToF durante un avance. Se abre un lateral: para al centro de esa celda para escanearla.
// Salta el frontal: vuelve a medir lo que falta desde la nueva lectura.
void salto(int i, int antes, long f) {
  if (soloTiempo) return;        // avance de prueba: nada lo alarga
  if (i != 1) return;            // v2: los laterales van por borde(), con umbral (no por salto brusco)
  if (dist[i] > antes) saltos |= 1 << i;
  if (i == 1) faltan(f, f);
}

// v2: orilla de pared lateral durante un avance = el sensor cruzo una orilla de celda. Sin encoders, las orillas son la regla.
// Se acaba la pared (abertura): para al centro de esa celda para escanearla. Empieza una pared: lo que falta se ajusta
// al centro de celda mas cercano a lo que ya creia (el tiempo solo dice cuantas celdas, la orilla dice donde).
void borde(int i, bool pared, long f) {
  if (soloTiempo) return;
  if (!pared) {
    saltos |= 1 << i;
    faltan(f, TRAS_SALTO);
  } else {
    cierres |= 1 << i;
    long k = lroundf((f - TRAS_CIERRA) / (float)CELDA);
    faltan(f, TRAS_CIERRA + CELDA * max(k, 0L));
  }
}

void termina() {
  soloTiempo = false;
  if (tipo == AVANZA) hecho = total - falta();
  if (tipo == GIRA && mpuOk && !signo && fabs(yaw - yaw0) > 30) {
    signo = (yaw - yaw0) * dirL > 0 ? 1 : -1;   // primer giro: aprende hacia donde crece el yaw
    ref = signo * yaw0 + arg;
  }
  frena();
  tipo = NADA;
  tQuieto = millis();
  ocupado = 0;
}

// Centrado con los 2 laterales: e = posicion entre paredes; de = que tan rapido cambia (rumbo torcido)
float centrado() {
  // centrado en el carril: con las 2 paredes, que lean lo mismo; con una, que lea D_LADO (geometria del chasis)
  bool L = dist[0] < CARRIL_NO, R = dist[2] < CARRIL_NO;   // v2: solo paredes de su carril; sin ellas va derecho (rumbo del MPU)
  int e = 0;
  if (L && R) e = dist[0] - dist[2];
  else if (L) e = 2 * (dist[0] - D_LADO);
  else if (R) e = 2 * (D_LADO - dist[2]);
  eCarril = e;
  hayCarril = L && R;
  unsigned long now = millis();
  if (!(L || R)) { tCen = 0; deCen = 0; }
  else if (!tCen) { tCen = now; eCen = e; deCen = 0; }
  else if (now - tCen >= 100) {          // cada 100 ms: mm/s que se acerca a un lado
    deCen = (e - eCen) * 1000.0f / (now - tCen);
    eCen = e;
    tCen = now;
  }
  return constrain(KC * e + KD * deCen, -40, 40) + AJUSTE_DER / 2.0f;
}

void control() {
  long t = millis() - tIni;
  if (tipo == CENTRA) {
    long e = dist[1] - objetivo;
    if (labs(e) <= 4 || t > 1000) { termina(); return; }
    int v = labs(e) > 15 ? VEL_MIN : VEL_MIN - 10;
    motores(e > 0 ? v : -v, e > 0 ? v : -v);
    return;
  }
  if (tipo == GIRA) {
    if (!mpuOk) {
      if (t >= dur) termina();
      else motores(dirL * VEL_GIRO, dirR * VEL_GIRO);
      return;
    }
    // atorado: las ruedas empujan y el giroscopio no ve giro (una esquina contra la pared): atras 200 ms y sigue
    if (tDes) {
      if (millis() < tDes) { motores(-VEL_MIN, -VEL_MIN); return; }
      tDes = 0;
      yawMov = yaw;
      tGiroMov = millis();
    }
    if (fabs(yaw - yawMov) > 2) { yawMov = yaw; tGiroMov = millis(); }
    else if (millis() - tGiroMov > ATORADO_MS) {
      if (++atorones > 2) { termina(); return; }
      tDes = millis() + 200;
      return;
    }
    // con MPU: hasta el rumbo deseado (absoluto: corrige lo que se paso o le falto en giros anteriores)
    float f = signo ? (ref - signo * yaw) * dirL : abs(arg) - fabs(yaw - yaw0);
    if (f <= min(ADELANTO, abs(arg) / 3.0f) || t >= max(3 * dur, 1500L)) { termina(); return; }
    int v = f < 25 ? (VEL_GIRO + VEL_MIN) / 2 : VEL_GIRO;
    motores(dirL * v, dirR * v);
    return;
  }
  // Golpe del acelerometro: es choque solo si el robot dejo de avanzar (el frontal no bajo 10 mm en CONFIRMA_MS).
  // Sin pared enfrente a la vista no se puede confirmar asi: solo cuenta un golpe muy fuerte.
  // (En pista, golpes de 0.75 a 1.5 g sin chocar: vibracion de los motores y del arranque.)
  if (tChoque && millis() - tChoque > CONFIRMA_MS) {
    bool trabado = fChoque < RANGO ? fChoque - dist[1] < 10 : pico > CHOQUE_FUERTE;
    tChoque = 0;
    if (trabado) {
      choque = 1;
      tRetro = millis() + RETRO_MS;
    }
  }
  // Choque: atras RETRO_MS y termina; Python vuelve a leer y se aleja de la pared antes de avanzar
  if (tRetro) {
    if (millis() < tRetro) { motores(-VEL_RETRO, -VEL_RETRO); return; }
    tRetro = 0;
    termina();
    return;
  }
  // Avanza por distancia con el frontal; sin pared a la vista, por tiempo
  bool paredF = dist[1] < PARED_F;
  if (dist[1] < dMin - 3) { dMin = dist[1]; tBaja = millis(); }
  if (paredF && millis() - tBaja > 300) { termina(); return; }   // pegado a la pared y ya no se acerca: alto
  if (dist[1] <= D_FRENTE) {
    // muy pegado: se hace para atras hasta D_FRENTE (maximo 0.8 s mas)
    if (dist[1] < D_FRENTE - D_CERCA && t < dur + 800) { motores(-VEL_MIN, -VEL_MIN); return; }
    termina();
    return;
  }
  if (objetivo < 0 && dist[1] < RANGO && !soloTiempo) {   // aparece pared: sigue por distancia
    long fa = falta();
    objetivo = max(dist[1] - (int)fa, D_FRENTE);
    if (dist[1] - fa < D_FRENTE) total -= fa - max(dist[1] - D_FRENTE, 0);
  }
  long f = falta();
  if (f <= 0 || t > 3 * dur) { termina(); return; }   // 3 * dur: seguro si el frontal deja de bajar
  if (total - f > pedido + TRAS_SALTO) { termina(); return; }   // varios saltos seguidos no lo alargan sin fin
  const float zona = CELDA / 4.0f;
  float tope = f < zona ? VEL_MIN + (vmax - VEL_MIN) * f / zona : vmax;
  if (dist[1] < D_FRENTE + 100) tope = min(tope, (float)VEL_MIN + FRENA_K * (dist[1] - D_FRENTE));   // frena al acercarse
  vel = min(vel + 6.0f, tope);
  float corr = centrado();
  if (mpuOk && signo) {
    corr += constrain(KG * (signo * yaw - ref), -20.0f, 20.0f);   // sostiene el rumbo
    // v2: rumbo con UNA pared lateral basta. En 300 ms junto a la misma pared, si su lectura cambio x mm mientras
    // avanzo a mm, el robot va chueco atan(x / a) respecto a la pared. El giroscopio dice otra cosa: la diferencia
    // es su deriva (o que lo pusieron chueco al salir). Corrige 30 % cada ventana, sin detenerse.
    bool L = dist[0] < CARRIL_SI, R = dist[2] < CARRIL_SI;
    float dev = signo * yaw - ref;
    if (!tLat) {
      if (L || R) { tLat = millis(); lat0[0] = dist[0]; lat0[1] = dist[2]; latOk[0] = L; latOk[1] = R; devLat = 0; nLat = 0; }
    } else {
      latOk[0] &= L; latOk[1] &= R; devLat += dev; nLat++;
      if (!(latOk[0] || latOk[1])) tLat = 0;
      else if (millis() - tLat >= 300) {
        float a = CELDA * 300.0f / msCelda, th = 0;
        int m = 0;
        if (latOk[0]) { th += atan2f(dist[0] - lat0[0], a); m++; }   // se aleja de la izquierda: va hacia la derecha (+)
        if (latOk[1]) { th -= atan2f(dist[2] - lat0[1], a); m++; }
        th = th / m * 57.3f;
        float d = devLat / nLat - th;
        if (fabs(th) < 25 && fabs(d) < 30) ref += 0.3f * d;   // hasta 30: en pista el rumbo deseado llego a quedar 21 grados chueco y ya no se corregia
        tLat = 0;
      }
    }
  }
  motores(vel - corr, vel + corr);
}

// ---------- MPU-6050 ----------
void mpuEscribe(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(v);
  Wire.endTransmission();
}

int16_t gz() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x47);               // GYRO_ZOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 2);
  uint8_t hi = Wire.read();
  uint8_t lo = Wire.read();
  return (int16_t)(hi << 8 | lo);
}

// Quieto al arrancar: mide el bias del giroscopio
bool mpuInit() {
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) return false;
  mpuEscribe(0x6B, 0);            // despierta
  mpuEscribe(0x1A, 3);            // filtro ~44 Hz
  mpuEscribe(0x1B, 0x08);         // +-500 grados/s
  mpuEscribe(0x1C, 0x00);         // acelerometro +-2 g (16384 LSB/g)
  delay(100);
  long s = 0;
  for (int i = 0; i < 200; i++) { s += gz(); delay(3); }
  bias = s / 200.0f;
  tGyro = micros();
  return true;
}

// Cada 10 ms: golpe horizontal (sobre el promedio lento: quita la inclinacion del montaje) y vertical
void leeAccel() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);               // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6);
  float a[3];
  for (int i = 0; i < 3; i++) {
    uint8_t hi = Wire.read();
    uint8_t lo = Wire.read();
    a[i] = (int16_t)(hi << 8 | lo) / 16384.0f;
  }
  float g = hypotf(a[0] - axF, a[1] - ayF);
  axF += 0.05f * (a[0] - axF);
  ayF += 0.05f * (a[1] - ayF);
  if (tipo == AVANZA) {
    pico = max(pico, g);
    if (!tRetro && !tChoque && millis() - tIni > 150 && g > CHOQUE_G) {   // los primeros 150 ms son el arranque
      tChoque = millis();                // sospecha: se confirma en control() si el robot dejo de avanzar
      fChoque = dist[1];
    }
  }
  if (fabs(a[2]) < LEVANTA_G) {     // inclinado o en el aire
    if (!tLev) tLev = millis();
    else if (millis() - tLev > 150 && !levantado) {
      levantado = 1;
      cmd = NADA;
      if (tipo != NADA) termina();
    }
  } else {
    tLev = 0;
  }
}

void leeGyro() {
  uint32_t t = micros();
  int16_t g = gz();
  // v2: quieto medio segundo y casi sin giro: lo que mide es deriva (cambia con la temperatura); la sigue despacio
  if (tipo == NADA && millis() - tQuieto > 500 && fabs(g - bias) < 60) bias += 0.01f * (g - bias);
  yaw += (g - bias) / LSB_DPS * (t - tGyro) * 1e-6f;
  tGyro = t;
}

// ---------- VL53L0X ----------
bool tofInit() {
  for (int i = 0; i < 3; i++) {
    pinMode(XSHUT[i], OUTPUT);
    digitalWrite(XSHUT[i], LOW);
  }
  delay(10);
  for (int i = 0; i < 3; i++) {
    pinMode(XSHUT[i], INPUT);
    delay(10);
    // Cambia la direccion antes de init(): en 0x29 tambien contesta el TCS34725
    tof[i].setAddress(0x30 + i);
    tof[i].setTimeout(50);
    if (!tof[i].init()) return false;
    tof[i].setMeasurementTimingBudget(20000);
    tof[i].startContinuous();
  }
  return true;
}

void tofLee() {
  if (!tofOk) return;
  for (int i = 0; i < 3; i++) {
    if ((tof[i].readReg(VL53L0X::RESULT_INTERRUPT_STATUS) & 0x07) == 0) continue;
    int d = tof[i].readRangeContinuousMillimeters();
    if (d == 0 || d > 2000) d = 9999;
    crudo[i] = d;
    if (d != 9999) d = max((int)(tofA[i] * d + tofB[i] + 0.5f), 1);
    bool brusco = abs(d - dist[i]) >= SALTO;
    if (!brusco) nSalto[i] = 0;
    else if (++nSalto[i] < 2) continue;
    else nSalto[i] = 0;
    int antes = dist[i];
    long f = falta();               // con la lectura vieja
    dist[i] = d;
    if (brusco && tipo == AVANZA) salto(i, antes, f);
    if (i != 1) {
      bool w = dist[i] < (lado[i] ? CARRIL_NO : CARRIL_SI);
      if (w == lado[i]) nLado[i] = 0;
      else if (++nLado[i] >= 2) {
        lado[i] = w;
        nLado[i] = 0;
        if (tipo == AVANZA) borde(i, w, f);
      }
    }
  }
}

// ---------- Sensor de color ----------
int clasifica(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  if (c < refs[0].c * BRILLO_MIN) return 0;
  float s = r + g + b + 1;
  float rn = r / s, gn = g / s, bn = b / s;
  int mejor = 0;
  float dmin = 1e9;
  for (int i = 0; i < NCOL; i++) {
    float lc = log((c + 1.0f) / (refs[i].c + 1.0f));
    float d = sq(rn - refs[i].r) + sq(gn - refs[i].g) + sq(bn - refs[i].b) + 0.01f * sq(lc);
    if (d < dmin) { dmin = d; mejor = i; }
  }
  return dmin < DIST_MAX ? mejor : 0;
}

void leeRaw(uint16_t &r, uint16_t &g, uint16_t &b, uint16_t &c) {
  // Lectura directa de registros: no espera la integracion como getRawData()
  c = tcs.read16(TCS34725_CDATAL);
  r = tcs.read16(TCS34725_RDATAL);
  g = tcs.read16(TCS34725_GDATAL);
  b = tcs.read16(TCS34725_BDATAL);
}

int ultimo = 0, racha = 0;
bool armado = true;

void leeColor() {
  uint16_t r, g, b, c;
  leeRaw(r, g, b, c);
  raw[0] = r; raw[1] = g; raw[2] = b; raw[3] = c;
  int k = clasifica(r, g, b, c);
  racha = (k == ultimo) ? racha + 1 : 1;
  ultimo = k;
  if (racha < 3) return;
  if (k == 0) {
    armado = true;
  } else if (armado) {
    armado = false;
    colorPend = k;
    if (k == AMAR && tipo != NADA) termina();
  }
}

// ---------- OLED ----------
void pinta() {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print(ESTADOS[estado]);
  oled.print(" ");
  oled.println(FASES[fase]);
  oled.drawLine(0, 10, 127, 10, SSD1306_WHITE);
  int total = 0;
  for (int i = 1; i < NCOL; i++) {
    oled.setCursor(0, 14 + (i - 1) * 10);
    oled.print(refs[i].nom);
    oled.setCursor(70, 14 + (i - 1) * 10);
    oled.print(cuenta[i]);
    total += cuenta[i];
  }
  oled.setCursor(0, 54);
  oled.print("PY ");
  oled.print(nRpc);
  oled.print(" ");
  oled.print(ult);
  oled.print(mpuOk ? " G" : "");
  oled.setCursor(90, 54);
  oled.print("T:");
  oled.print(total);
  oled.display();
}

void calibracion() {
  while (true) {
    uint16_t r, g, b, c;
    leeRaw(r, g, b, c);
    uint32_t t0 = millis();
    while (millis() - t0 < 300) tofLee();
    float s = r + g + b + 1;
    const char* nom = refs[clasifica(r, g, b, c)].nom;
    Monitor.print("r "); Monitor.print(r / s, 2);
    Monitor.print(" g "); Monitor.print(g / s, 2);
    Monitor.print(" b "); Monitor.print(b / s, 2);
    Monitor.print(" c "); Monitor.print(c);
    Monitor.print(" -> "); Monitor.print(nom);
    Monitor.print("  dist ");
    Monitor.print(dist[0]); Monitor.print(" ");
    Monitor.print(dist[1]); Monitor.print(" ");
    Monitor.println(dist[2]);
    oled.clearDisplay();
    oled.setCursor(0, 0);
    oled.println("CALIBRACION");
    oled.print("r "); oled.println(r / s, 2);
    oled.print("g "); oled.println(g / s, 2);
    oled.print("b "); oled.println(b / s, 2);
    oled.print("c "); oled.print(c); oled.print(" "); oled.println(nom);
    oled.print(dist[0]); oled.print(" ");
    oled.print(dist[1]); oled.print(" ");
    oled.println(dist[2]);
    oled.display();
  }
}

void falla(const char* msg) {
  oled.clearDisplay();
  oled.setCursor(0, 0);
  oled.println(msg);
  oled.display();
  while (true) delay(100);
}

void setup() {
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(BTN, INPUT_PULLUP);
  motores(0, 0);

  delay(500);  // la OLED tarda en despertar al prender por VIN
  Wire.begin();
  Wire.setClock(400000);
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C, false);  // derecha en la cabeza de la camara
  oled.setTextColor(SSD1306_WHITE);
  tofOk = tofInit();
  if (!tofOk) falla("SIN VL53L0X");
  if (!tcs.begin()) falla("SIN SENSOR COLOR");
  mpuOk = mpuInit();              // opcional: sin el, giros y rectas por tiempo

  Bridge.begin();
  Monitor.begin();
  Bridge.provide("mover", rpcMover);
  Bridge.provide("girar", rpcGirar);
  Bridge.provide("ajustar", rpcAjustar);
  Bridge.provide("alinear", rpcAlinear);
  Bridge.provide("centrar", rpcCentrar);
  Bridge.provide("mover_t", rpcMoverT);
  Bridge.provide("set_ms", rpcSetMs);
  Bridge.provide("signo", rpcSigno);
  Bridge.provide("ocupado", rpcOcupado);
  Bridge.provide("color", rpcColor);
  Bridge.provide("arranque", rpcArranque);
  Bridge.provide("set_cuenta", rpcCuenta);
  Bridge.provide("set_estado", rpcEstado);
  Bridge.provide("set_fase", rpcFase);
  Bridge.provide("raw", rpcRaw);
  Bridge.provide("set_ref", rpcSetRef);
  Bridge.provide("set_tof", rpcSetTof);
  Bridge.provide("odo", rpcOdo);
  Bridge.provide("alto", rpcAlto);

  if (digitalRead(BTN) == LOW) calibracion();
}

uint32_t tCtrl = 0, tColor = 0, tOled = 0;
int btnPrev = HIGH;
uint32_t tBtn = 0;

void loop() {
  uint32_t t = millis();

  if (pideAlto) {
    pideAlto = 0;
    cmd = NADA;
    if (tipo != NADA) termina();
    ocupado = 0;
  }
  if (cmd != NADA && tipo == NADA) iniciaMov();

  tofLee();
  if (mpuOk && micros() - tGyro >= 2000) leeGyro();

  if (t - tCtrl >= T_CTRL) {
    tCtrl = t;
    if (mpuOk) leeAccel();
    if (tipo != NADA) control();
  }

  if (t - tColor >= T_COLOR) {
    tColor = t;
    leeColor();
  }

  int btn = digitalRead(BTN);
  if (btn != btnPrev && t - tBtn > 50) {
    if (btn == HIGH) {
      arranque = (t - tBtn > 2000) ? 2 : 1;
      ult = arranque == 2 ? 'L' : 'B';
      refresca = 1;
    }
    tBtn = t;
    btnPrev = btn;
  }

  if (tipo == NADA && t - tOled >= 300) {
    tOled = t;
    refresca = 1;
  }

  if (refresca && tipo == NADA && cmd == NADA) {   // la OLED tarda ~25 ms: nunca en movimiento
    refresca = 0;
    pinta();
  }
}
