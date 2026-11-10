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
const long MS_CELDA = 600;    // ms por celda de 18 cm
const long MS_RAPIDA = 400;   // ms por celda en corridas rapidas
const long MS_90 = 250;       // ms por giro de 90 grados
const int VEL_EXPLORA = 140;
const int VEL_RAPIDA = 220;
const int VEL_GIRO = 130;
const int VEL_MIN = 80;
const int AJUSTE_DER = 0;     // suma PWM al motor derecho si se desvia
const bool INV_IZQ = true;    // true si ese motor gira al reves (en vez de voltear cables)
const bool INV_DER = true;
const int PARED = 120;        // mm: lectura menor = hay pared (lados)
const int PARED_F = 130;      // mm: al frente, menos de esto = pared (de 140 para arriba no hay)
const int D_FRENTE = 55;      // mm al frente con el robot centrado en la celda
const int D_CERCA = 15;       // mm: si queda mas de esto por debajo de D_FRENTE, se hace para atras
const int FRENA_K = 2;        // PWM por mm: con pared al frente baja la velocidad al acercarse
const int D_LADO = 50;        // mm a una pared lateral con el robot centrado
const float KC = 0.8;         // ganancia de centrado
const float OFF_COLOR = 0.2;  // distancia eje->sensor de color, en celdas
// Odometria ligera (medidas del CAD, chasis/chasis.scad; el eje de las ruedas es el centro del robot)
const int CELDA = 180;        // mm de centro a centro de celda
const int Y_LADO = 40;        // VL53L0X laterales adelante del eje (TOF_LADO)
const int MEDIA_PARED = 6;    // mitad del grueso de la pared
const int BORDE_AJ = 0;       // mm: ajuste del borde por el cono del sensor (calibrar si corrige de mas)
const int FRENTE_ODO = 400;   // mm: hasta aqui el frontal corrige la distancia que falta
const int MAX_CORR = 45;      // mm: correcciones mas grandes se ignoran (lectura mala)
const uint32_t T_CTRL = 10;
const uint32_t T_COLOR = 30;

// ---------- Colores ----------
// r, g, b normalizados (r/(r+g+b)) y brillo c. Llenar con el modo calibracion.
struct Ref { const char* nom; float r, g, b, c; };
Ref refs[] = {
  {"PISO",  0.33, 0.33, 0.33, 900},
  {"ROJO",  0.58, 0.22, 0.20, 400},
  {"VERDE", 0.26, 0.46, 0.28, 350},
  {"AZUL",  0.20, 0.32, 0.48, 300},
  {"AMAR",  0.42, 0.40, 0.18, 700},
};
const int NCOL = sizeof(refs) / sizeof(refs[0]);
const float DIST_MAX = 0.02;
const float BRILLO_MIN = 1.3;  // piso negro: una marca refleja al menos 1.3x mas que el piso (quita falsos positivos)

Oled oled(128, 64, &Wire, -1);
Adafruit_TCS34725 tcs(TCS34725_INTEGRATIONTIME_24MS, TCS34725_GAIN_4X);
VL53L0X tof[3];
int dist[3] = {9999, 9999, 9999};
bool tofOk = false;

enum { NADA, AVANZA, GIRA };
volatile int cmd = NADA;
volatile int arg = 0;
volatile int rapido = 0;
volatile int ocupado = 0;
volatile int colorPend = 0;
volatile int arranque = 0;
volatile int refresca = 1;
volatile uint32_t nRpc = 0;   // sube cada vez que Python pregunta: si no cambia, Python no corre
volatile char ult = '-';

int cuenta[NCOL] = {0};
int estado = 0;
const char* ESTADOS[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "BORRADO", "SIN CAM"};

int tipo = NADA;
int dirL, dirR;
long dur, unidad;
long total;                   // mm del avance en curso
long dur0;                    // duracion sin corregir
float escala[2] = {1, 1};     // velocidad aprendida (explorar, rapido): 1.1 = va 10% mas lento que MS_CELDA
int extraMm = 0;              // mm extra que pide Python (correccion de la camara)
int nCorr = 0, ultCorr = 0;   // correcciones del ultimo avance y la ultima en mm
bool ladoVe[2];               // pared vista a la izq / der (con antirrebote)
int ladoRacha[2];
uint32_t tIni;
float vel;
int dMin;                     // menor distancia al frente en este avance
uint32_t tBaja;               // ultima vez que bajo: si ya no baja con pared enfrente, esta empujando la pared

// ---------- RPC desde Python ----------
int rpcMover(int celdas, int r, int extra) {
  ult = 'M';
  if (ocupado) return 0;
  arg = celdas;
  extraMm = constrain(extra, -60, 60);
  rapido = r;
  cmd = AVANZA;
  ocupado = 1;
  return 1;
}

int rpcGirar(int cuartos) {
  ult = 'G';
  if (ocupado) return 0;
  arg = cuartos;
  cmd = GIRA;
  ocupado = 1;
  return 1;
}

int rpcOcupado() { return ocupado; }

long pActual() { return tipo == AVANZA ? total * (long)(millis() - tIni) / dur : 0; }

// 0 mm recorridos, 1 mm que faltan, 2 paredes (1 izq, 2 frente, 4 der, 8 en movimiento),
// 3 correcciones del ultimo avance, 4 ultima correccion (mm), 5/6/7 distancia frente/izq/der (mm)
int rpcOdo(int i) {
  long p = pActual();
  switch (i) {
    case 0: return p;
    case 1: return tipo == AVANZA ? total - p : 0;
    case 2: return (dist[0] < PARED) | (dist[1] < PARED_F) << 1 | (dist[2] < PARED) << 2 | (tipo != NADA) << 3;
    case 3: return nCorr;
    case 4: return ultCorr;
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

// bit0 izq, bit1 frente, bit2 der; -1 si no hay sensores
int rpcParedes() {
  if (!tofOk) return -1;
  return (dist[0] < PARED) | (dist[1] < PARED_F) << 1 | (dist[2] < PARED) << 2;
}

int rpcCuenta(int idx, int n) {
  if (idx > 0 && idx < NCOL) cuenta[idx] = n;
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
    unidad = rapido ? MS_RAPIDA : MS_CELDA;
    total = (long)arg * CELDA + extraMm;
    dur0 = max((long)(total * unidad / CELDA * escala[rapido ? 1 : 0]), 50L);
    dur = dur0;
    nCorr = 0;
    dMin = 9999;
    tBaja = millis();
    for (int i = 0; i < 2; i++) { ladoVe[i] = dist[i * 2] < PARED; ladoRacha[i] = 0; }
  } else {
    dirL = arg > 0 ? 1 : -1;
    dirR = -dirL;
    unidad = MS_CELDA;
    dur = abs(arg) * MS_90;
  }
  cmd = NADA;
}

void termina() {
  frena();
  tipo = NADA;
  ocupado = 0;
}

// La posicion se lleva por tiempo; una correccion recorre el reloj del movimiento
void corrige(long pc, float g) {
  long e = pc - pActual();
  if (abs(e) > MAX_CORR) return;
  e = (long)(e * g);
  long t = millis() - tIni;
  if (g >= 1 && pc > 30) {
    // borde lateral: corrige la posicion y la velocidad (se recuerda para los siguientes avances)
    dur = constrain(total * t / pc, dur0 * 7 / 10, dur0 * 14 / 10);
    float &es = escala[rapido ? 1 : 0];
    es = constrain(0.7f * es + 0.3f * es * dur / dur0, 0.6f, 1.6f);
  } else {
    tIni -= e * dur / total;
  }
  nCorr++;
  ultCorr = e;
}

void odometria() {
  // Bordes de pared a los lados: el sensor pasa por un poste justo en la frontera entre celdas
  for (int i = 0; i < 2; i++) {
    bool w = dist[i * 2] < PARED;
    if (w == ladoVe[i]) { ladoRacha[i] = 0; continue; }
    if (++ladoRacha[i] < 2) continue;
    ladoVe[i] = w;
    ladoRacha[i] = 0;
    long p = pActual(), mejor = 0, dmin = 99999;
    for (int k = 0; k < arg; k++) {
      long pc = (long)CELDA * k + CELDA / 2 + (w ? -MEDIA_PARED : MEDIA_PARED) - Y_LADO + BORDE_AJ;
      if (abs(pc - p) < dmin) { dmin = abs(pc - p); mejor = pc; }
    }
    corrige(mejor, 1.0f);
  }
  // Pared al frente en rango: lo que falta es la distancia menos D_FRENTE
  if (dist[1] < FRENTE_ODO) corrige(total - (dist[1] - D_FRENTE), 0.2f);
}

float centrado() {
  bool L = dist[0] < PARED, R = dist[2] < PARED;
  int e = 0;
  if (L && R) e = dist[0] - dist[2];
  else if (L) e = dist[0] - D_LADO;
  else if (R) e = D_LADO - dist[2];
  return constrain(KC * e, -40, 40) + AJUSTE_DER / 2.0f;
}

void control() {
  long t = millis() - tIni;
  if (tipo == GIRA) {
    if (t >= dur) termina();
    else motores(dirL * VEL_GIRO, dirR * VEL_GIRO);
    return;
  }
  // Con pared enfrente se detiene por distancia; si no, por tiempo
  bool paredF = dist[1] < PARED_F;
  if (dist[1] < dMin - 3) { dMin = dist[1]; tBaja = millis(); }
  if (paredF && millis() - tBaja > 300) { termina(); return; }   // pegado a la pared y ya no se acerca: alto
  if (paredF && dist[1] <= D_FRENTE) {
    // muy pegado: se hace para atras hasta D_FRENTE (maximo 0.8 s mas)
    if (dist[1] < D_FRENTE - D_CERCA && t < dur + 800) { motores(-VEL_MIN, -VEL_MIN); return; }
    termina();
    return;
  }
  if (t >= dur && !(paredF && t < dur + unidad / 3)) { termina(); return; }
  odometria();
  t = millis() - tIni;
  int vmax = rapido ? VEL_RAPIDA : VEL_EXPLORA;
  long falta = max(dur - t, 0L);
  long zona = unidad / 4;
  float tope = falta < zona ? VEL_MIN + (vmax - VEL_MIN) * falta / (float)zona : vmax;
  if (paredF) tope = min(tope, (float)VEL_MIN + FRENA_K * (dist[1] - D_FRENTE));   // frena al acercarse
  vel = min(vel + 6.0f, tope);
  float corr = centrado();
  motores(vel - corr, vel + corr);
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
    dist[i] = (d == 0 || d > 2000) ? 9999 : d;
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
    long celda = 0;
    if (tipo == AVANZA) celda = (long)((millis() - tIni) / (float)unidad + OFF_COLOR + 0.5f);
    colorPend = k + 16 * celda;
  }
}

// ---------- OLED ----------
void pinta() {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print("LABERINTO  ");
  oled.println(ESTADOS[estado]);
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

  Bridge.begin();
  Monitor.begin();
  Bridge.provide("mover", rpcMover);
  Bridge.provide("girar", rpcGirar);
  Bridge.provide("ocupado", rpcOcupado);
  Bridge.provide("color", rpcColor);
  Bridge.provide("arranque", rpcArranque);
  Bridge.provide("paredes", rpcParedes);
  Bridge.provide("set_cuenta", rpcCuenta);
  Bridge.provide("set_estado", rpcEstado);
  Bridge.provide("raw", rpcRaw);
  Bridge.provide("set_ref", rpcSetRef);
  Bridge.provide("odo", rpcOdo);

  if (digitalRead(BTN) == LOW) calibracion();
}

uint32_t tCtrl = 0, tColor = 0, tOled = 0;
int btnPrev = HIGH;
uint32_t tBtn = 0;

void loop() {
  uint32_t t = millis();

  if (cmd != NADA && tipo == NADA) iniciaMov();

  tofLee();

  if (t - tCtrl >= T_CTRL) {
    tCtrl = t;
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

  if (refresca) {
    refresca = 0;
    pinta();
  }
}
