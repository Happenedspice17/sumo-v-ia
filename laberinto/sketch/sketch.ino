#include <Arduino_RouterBridge.h>
#include <Wire.h>
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
#define ENC_L 2
#define ENC_R 3
#define BTN 12

// ---------- Calibracion ----------
#define USE_ENC 1             // 0 = sin encoders, mueve por tiempo
const long TICKS_CELDA = 360; // ticks por 18 cm
const long TICKS_90 = 120;    // ticks por giro de 90 grados
const long OFF_COLOR = 60;    // distancia eje->sensor de color, en ticks
const long MS_CELDA = 600;    // solo si USE_ENC = 0
const long MS_90 = 250;
const int VEL_EXPLORA = 140;
const int VEL_RAPIDA = 220;
const int VEL_GIRO = 130;
const int VEL_MIN = 80;
const float KP = 2.0;
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

volatile long ticksL = 0, ticksR = 0;
void isrL() { ticksL++; }
void isrR() { ticksR++; }

enum { NADA, AVANZA, GIRA };
volatile int cmd = NADA;
volatile int arg = 0;
volatile int velObj = VEL_EXPLORA;
volatile int ocupado = 0;
volatile int colorPend = 0;
volatile int arranque = 0;
volatile int refresca = 1;

int cuenta[NCOL] = {0};
int estado = 0;
const char* ESTADOS[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "ERR CAM"};

bool enMov = false;
int dirL, dirR;
long meta;
uint32_t tIni;
float vel;

// ---------- RPC desde Python ----------
int rpcMover(int celdas, int rapido) {
  if (ocupado) return 0;
  arg = celdas;
  velObj = rapido ? VEL_RAPIDA : VEL_EXPLORA;
  cmd = AVANZA;
  ocupado = 1;
  return 1;
}

int rpcGirar(int cuartos) {
  if (ocupado) return 0;
  arg = cuartos;
  velObj = VEL_GIRO;
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

int rpcCuenta(int idx, int n) {
  if (idx > 0 && idx < NCOL) cuenta[idx] = n;
  refresca = 1;
  return 1;
}

int rpcEstado(int e) {
  estado = constrain(e, 0, 5);
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

long progreso() {
#if USE_ENC
  return (ticksL + ticksR) / 2;
#else
  return millis() - tIni;
#endif
}

void iniciaMov() {
  noInterrupts();
  ticksL = ticksR = 0;
  interrupts();
  tIni = millis();
  vel = VEL_MIN;
  if (cmd == AVANZA) {
    dirL = dirR = 1;
    meta = arg * (USE_ENC ? TICKS_CELDA : MS_CELDA);
  } else {
    dirL = arg > 0 ? 1 : -1;
    dirR = -dirL;
    meta = abs(arg) * (USE_ENC ? TICKS_90 : MS_90);
  }
  cmd = NADA;
  enMov = true;
}

void control() {
  long p = progreso();
  long falta = meta - p;
  if (falta <= 0) {
    frena();
    enMov = false;
    ocupado = 0;
    return;
  }
  // Rampa: acelera al inicio y baja en el ultimo cuarto de celda
  long zona = (USE_ENC ? TICKS_CELDA : MS_CELDA) / 4;
  float tope = falta < zona ? VEL_MIN + (velObj - VEL_MIN) * falta / (float)zona : velObj;
  vel = min(vel + 6.0f, tope);
  float corr = USE_ENC ? KP * (ticksL - ticksR) : 0;
  motores(dirL * (vel - corr), dirR * (vel + corr));
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
    long pos = enMov && cmd == NADA && dirL == dirR ? progreso() : 0;
    long celda = USE_ENC ? (pos + OFF_COLOR + TICKS_CELDA / 2) / TICKS_CELDA : 0;
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
    float s = r + g + b + 1;
    const char* nom = refs[clasifica(r, g, b, c)].nom;
    Monitor.print("r "); Monitor.print(r / s, 2);
    Monitor.print(" g "); Monitor.print(g / s, 2);
    Monitor.print(" b "); Monitor.print(b / s, 2);
    Monitor.print(" c "); Monitor.print(c);
    Monitor.print(" -> "); Monitor.println(nom);
    oled.clearDisplay();
    oled.setCursor(0, 0);
    oled.println("CALIBRACION");
    oled.print("r "); oled.println(r / s, 2);
    oled.print("g "); oled.println(g / s, 2);
    oled.print("b "); oled.println(b / s, 2);
    oled.print("c "); oled.println(c);
    oled.println(nom);
    oled.display();
    delay(300);
  }
}

void setup() {
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(BTN, INPUT_PULLUP);
  pinMode(ENC_L, INPUT_PULLUP);
  pinMode(ENC_R, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_L), isrL, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_R), isrR, RISING);
  motores(0, 0);

  Wire.begin();
  Wire.setClock(400000);
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  oled.setTextColor(SSD1306_WHITE);
  if (!tcs.begin()) {
    oled.clearDisplay();
    oled.setCursor(0, 0);
    oled.println("SIN SENSOR COLOR");
    oled.display();
    while (true) delay(100);
  }

  Bridge.begin();
  Monitor.begin();
  Bridge.provide("mover", rpcMover);
  Bridge.provide("girar", rpcGirar);
  Bridge.provide("ocupado", rpcOcupado);
  Bridge.provide("color", rpcColor);
  Bridge.provide("arranque", rpcArranque);
  Bridge.provide("set_cuenta", rpcCuenta);
  Bridge.provide("set_estado", rpcEstado);

  if (digitalRead(BTN) == LOW) calibracion();
}

uint32_t tCtrl = 0, tColor = 0;
int btnPrev = HIGH;
uint32_t tBtn = 0;

void loop() {
  uint32_t t = millis();

  if (cmd != NADA && !enMov) iniciaMov();

  if (t - tCtrl >= T_CTRL) {
    tCtrl = t;
    if (enMov) control();
  }

  if (t - tColor >= T_COLOR) {
    tColor = t;
    leeColor();
  }

  int btn = digitalRead(BTN);
  if (btn != btnPrev && t - tBtn > 50) {
    tBtn = t;
    btnPrev = btn;
    if (btn == LOW) arranque = 1;
  }

  if (refresca) {
    refresca = 0;
    pinta();
  }
}
