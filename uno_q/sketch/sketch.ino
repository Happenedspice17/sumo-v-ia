#include <Arduino_RouterBridge.h>
#include <Wire.h>
#include <VL53L0X.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_TCS34725.h>

// ---------- Pines ----------
#define ENA 9
#define IN1 4
#define IN2 5
#define ENB 10
#define IN3 7
#define IN4 8
#define BTN 12
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
const int PARED = 120;        // mm: lectura menor = hay pared
const int D_FRENTE = 55;      // mm al frente con el robot centrado en la celda
const int D_LADO = 50;        // mm a una pared lateral con el robot centrado
const float KC = 0.8;         // ganancia de centrado
const float OFF_COLOR = 0.2;  // distancia eje->sensor de color, en celdas
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

Adafruit_SSD1306 oled(128, 64, &Wire, -1);
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

int cuenta[NCOL] = {0};
int estado = 0;
const char* ESTADOS[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "BORRADO", "SIN CAM"};

int tipo = NADA;
int dirL, dirR;
long dur, unidad;
uint32_t tIni;
float vel;

// ---------- RPC desde Python ----------
int rpcMover(int celdas, int r) {
  if (ocupado) return 0;
  arg = celdas;
  rapido = r;
  cmd = AVANZA;
  ocupado = 1;
  return 1;
}

int rpcGirar(int cuartos) {
  if (ocupado) return 0;
  arg = cuartos;
  cmd = GIRA;
  ocupado = 1;
  return 1;
}

int rpcOcupado() { return ocupado; }

int rpcColor() {
  int c = colorPend;
  colorPend = 0;
  return c;
}

int rpcArranque() {
  int a = arranque;
  arranque = 0;
  return a;
}

// bit0 izq, bit1 frente, bit2 der; -1 si no hay sensores
int rpcParedes() {
  if (!tofOk) return -1;
  return (dist[0] < PARED) | (dist[1] < PARED) << 1 | (dist[2] < PARED) << 2;
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
    dur = arg * unidad;
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
  bool paredF = dist[1] < PARED;
  if (paredF && dist[1] <= D_FRENTE) { termina(); return; }
  if (t >= dur && !(paredF && t < dur + unidad / 3)) { termina(); return; }
  int vmax = rapido ? VEL_RAPIDA : VEL_EXPLORA;
  long falta = max(dur - t, 0L);
  long zona = unidad / 4;
  float tope = falta < zona ? VEL_MIN + (vmax - VEL_MIN) * falta / (float)zona : vmax;
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

  Wire.begin();
  Wire.setClock(400000);
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
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

  if (digitalRead(BTN) == LOW) calibracion();
}

uint32_t tCtrl = 0, tColor = 0;
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
    if (btn == HIGH) arranque = (t - tBtn > 2000) ? 2 : 1;
    tBtn = t;
    btnPrev = btn;
  }

  if (refresca) {
    refresca = 0;
    pinta();
  }
}
