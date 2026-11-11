// Version SIN MPU-6050: giros y rectas por tiempo. La version con MPU (que tambien funciona sin el) esta en ../sketch/
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
const long MS_CELDA = 600;    // ms por celda de 18 cm (solo si el frontal no ve pared: avanza por tiempo)
const long MS_90 = 250;       // ms por giro de 90 grados
const int VEL_EXPLORA = 140;
const int VEL_LENTO = 100;    // cuando la camara ve blanco (pared) en el camino
const int VEL_GIRO = 130;
const int VEL_MIN = 80;
const int AJUSTE_DER = 0;     // suma PWM al motor derecho si se desvia
const bool INV_IZQ = true;    // true si ese motor gira al reves (en vez de voltear cables)
const bool INV_DER = true;
const int PARED = 120;        // mm: lectura menor = hay pared (lados)
const int PARED_F = 130;      // mm: al frente, menos de esto = pared (de 140 para arriba no hay)
const int D_FRENTE = 130;     // mm: al leer esto al frente se detiene (el sensor lee de mas: nunca llega a 50)
const int D_CERCA = 10;       // mm: si queda mas de esto por debajo de D_FRENTE, se hace para atras
const int FRENA_K = 2;        // PWM por mm: con pared al frente baja la velocidad al acercarse
const int D_LADO = 50;        // mm a una pared lateral con el robot centrado
const float KC = 0.8;         // ganancia de centrado
const float KD = 0.3;         // ganancia de rumbo: corrige segun que tan rapido se acerca a una pared lateral
const int D_LADO_MIN = 90;    // mm: solo corrige si un lateral lee menos de esto (se aleja de esa pared)
const int CELDA = 180;        // mm de centro a centro de celda
const int RANGO = 1000;       // mm: con el frontal leyendo menos, avanza por distancia; mas lejos, por tiempo
const int SALTO = 120;        // mm: cambio brusco entre 2 lecturas (50 -> 200, 100 -> 300)
const int TRAS_SALTO = 124;   // mm tras abrirse un lateral: centro de esa celda (90 + 40 del sensor - 6 de media pared)
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

enum { NADA, AVANZA, GIRA };
volatile int cmd = NADA;
volatile int arg = 0;
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
long total;                   // mm del avance en curso
int objetivo = -1;            // lectura del frontal donde parar; -1 = no ve pared, va por tiempo
long hecho = 0;               // mm que recorrio el ultimo avance
int vmax = VEL_EXPLORA;
int saltos = 0;               // ToF que saltaron hacia lejos en este avance (1 izq, 2 frente, 4 der)
int nSalto[3];                // lecturas seguidas con cambio brusco (cuenta a la 2a: una lectura mala no)
uint32_t tIni;
float vel;
int dMin;                     // menor distancia al frente en este avance
uint32_t tBaja;               // ultima vez que bajo: si ya no baja con pared enfrente, esta empujando la pared

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
// Sin MPU gira en su lugar por tiempo (aproximado). Devuelve 2 si hay que esperar el giro.
int rpcAjustar(int g) {
  ult = 'J';
  if (ocupado || g == 0) return 0;
  arg = g;
  cmd = GIRA;
  ocupado = 1;
  return 2;
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
    total = max((long)arg, 1L);
    dur = max(total * MS_CELDA / CELDA, 50L);
    objetivo = dist[1] < RANGO ? max(dist[1] - (int)total, D_FRENTE) : -1;
    saltos = 0;
    dMin = 9999;
    tBaja = millis();
    tCen = 0;
  } else {
    dirL = arg > 0 ? 1 : -1;
    dirR = -dirL;
    dur = max(abs(arg) * MS_90 / 90, 30L);
  }
  cmd = NADA;
}

// Deja el avance con f mm por recorrer (antes faltaban fAntes): por el frontal o, sin pared a la vista, por tiempo
void faltan(long fAntes, long f) {
  total += f - fAntes;
  if (dist[1] < RANGO) {
    objetivo = max(dist[1] - (int)f, D_FRENTE);
  } else {
    objetivo = -1;
    tIni = millis() - (total - f) * MS_CELDA / CELDA;
    dur = max(total * MS_CELDA / CELDA, 50L);
  }
}

// Cambio brusco en un ToF durante un avance. Se abre un lateral: para al centro de esa celda para escanearla.
// Salta el frontal: vuelve a medir lo que falta desde la nueva lectura.
void salto(int i, int antes, long f) {
  if (dist[i] > antes) saltos |= 1 << i;
  if (i == 1) faltan(f, f);
  else if (dist[i] > antes && dist[i] >= PARED) faltan(f, TRAS_SALTO);
}

void termina() {
  if (tipo == AVANZA) hecho = total - falta();
  frena();
  tipo = NADA;
  ocupado = 0;
}

// Centrado con los 2 laterales: e = posicion entre paredes; de = que tan rapido cambia (rumbo torcido)
float centrado() {
  bool L = dist[0] < D_LADO_MIN, R = dist[2] < D_LADO_MIN;   // lejos de las 2 paredes: va derecho
  int e = 0;
  if (L && R) e = dist[0] - dist[2];
  else if (L) e = dist[0] - D_LADO_MIN;
  else if (R) e = D_LADO_MIN - dist[2];
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
  if (tipo == GIRA) {
    if (t >= dur) termina();
    else motores(dirL * VEL_GIRO, dirR * VEL_GIRO);
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
  if (objetivo < 0 && dist[1] < RANGO) objetivo = max(dist[1] - (int)falta(), D_FRENTE);   // aparece pared: sigue por distancia
  long f = falta();
  if (f <= 0 || t > 3 * dur) { termina(); return; }   // 3 * dur: seguro si el frontal deja de bajar
  const float zona = CELDA / 4.0f;
  float tope = f < zona ? VEL_MIN + (vmax - VEL_MIN) * f / zona : vmax;
  if (dist[1] < D_FRENTE + 100) tope = min(tope, (float)VEL_MIN + FRENA_K * (dist[1] - D_FRENTE));   // frena al acercarse
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
  Bridge.provide("ajustar", rpcAjustar);
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

  if (refresca && tipo == NADA && cmd == NADA) {   // la OLED tarda ~25 ms: nunca en movimiento
    refresca = 0;
    pinta();
  }
}
