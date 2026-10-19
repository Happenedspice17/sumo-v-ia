#include <Wire.h>
#include <EEPROM.h>
#include <VL53L0X.h>
#include <SSD1306Ascii.h>
#include <SSD1306AsciiWire.h>

// ---------- Pines ----------
#define ENA 5
#define ENB 6
#define IN1 7
#define IN2 8
#define IN3 9
#define IN4 10
#define BTN 2
const uint8_t XSHUT[3] = {A0, A1, A2};   // izq, frente, der

// ---------- Laberinto ----------
#define N 16
const uint8_t INI_X = 0, INI_Y = 0, INI_R = 0;   // rumbo 0=N 1=E 2=S 3=O
const uint8_t META_X = 7, META_Y = 7;            // meta 2x2: (7,7) a (8,8)

// ---------- Calibracion ----------
const uint16_t T_CELDA = 60;    // ticks de 10 ms por celda de 18 cm
const uint16_t T_RAPIDA = 40;   // ticks por celda en corridas rapidas
const uint16_t T_90 = 25;       // ticks por giro de 90 grados
const uint8_t VEL_EXPLORA = 140, VEL_RAPIDA = 220, VEL_GIRO = 130, VEL_MIN = 80;
const int AJUSTE_DER = 0;       // suma PWM al motor derecho si se desvia
const uint16_t PARED = 120;     // mm: lectura menor = hay pared
const uint16_t D_FRENTE = 55;   // mm al frente con el robot centrado en la celda
const uint16_t D_LADO = 50;     // mm a una pared lateral con el robot centrado
const float KC = 0.8;           // ganancia de centrado
const float OFF_COLOR = 0.2;    // distancia eje->sensor de color, en celdas

// ---------- Colores ----------
struct Ref { const char* nom; float r, g, b, c; };
const Ref refs[] = {
  {"PISO",  0.33, 0.33, 0.33, 900},
  {"ROJO",  0.58, 0.22, 0.20, 400},
  {"VERDE", 0.26, 0.46, 0.28, 350},
  {"AZUL",  0.20, 0.32, 0.48, 300},
  {"AMAR",  0.42, 0.40, 0.18, 700},
};
const uint8_t NCOL = sizeof(refs) / sizeof(refs[0]);
const float DIST_MAX = 0.02;

// Cada celda: bits 0-3 paredes (N,E,S,O), bit 4 visitada, bits 5-7 color de marca
#define VISTO 0x10
uint8_t celda[N * N];
uint8_t dis[N * N];
uint8_t cuenta[NCOL];
const int8_t DX[4] = {0, 1, 0, -1};
const int8_t DY[4] = {1, 0, -1, 0};
uint8_t px, py, rumbo, estado;
const char* const EST[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "BORRADO"};

SSD1306AsciiWire oled;
VL53L0X tof[3];
uint16_t dist[3] = {9999, 9999, 9999};

// ---------- Timer1: base de tiempo de 10 ms ----------
volatile uint16_t ticks = 0;
volatile bool tick = false;

ISR(TIMER1_COMPA_vect) {
  ticks++;
  tick = true;
}

void timer1() {
  cli();
  TCCR1A = 0;
  TCCR1B = (1 << WGM12) | (1 << CS11) | (1 << CS10);   // CTC, prescaler 64
  OCR1A = 2499;                                        // 16 MHz / 64 / 2500 = 100 Hz
  TIMSK1 = (1 << OCIE1A);
  sei();
}

uint16_t ahora() {
  cli();
  uint16_t t = ticks;
  sei();
  return t;
}

bool esperaTick() {
  if (!tick) return false;
  tick = false;
  return true;
}

// ---------- TCS34725 por I2C directo ----------
#define TCS 0x29

void tcsW(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(TCS);
  Wire.write(0x80 | reg);
  Wire.write(v);
  Wire.endTransmission();
}

bool tcsInit() {
  Wire.beginTransmission(TCS);
  Wire.write(0x80 | 0x12);
  Wire.endTransmission();
  Wire.requestFrom((uint8_t)TCS, (uint8_t)1);
  uint8_t id = Wire.read();
  if (id != 0x44 && id != 0x4D) return false;
  tcsW(0x01, 0xF6);   // ATIME: 10 ciclos = 24 ms
  tcsW(0x0F, 0x01);   // ganancia 4x
  tcsW(0x00, 0x01);   // PON
  delay(3);
  tcsW(0x00, 0x03);   // PON + AEN
  return true;
}

void tcsLee(uint16_t &c, uint16_t &r, uint16_t &g, uint16_t &b) {
  uint8_t d[8];
  Wire.beginTransmission(TCS);
  Wire.write(0xA0 | 0x14);   // auto-incremento desde CDATAL
  Wire.endTransmission();
  Wire.requestFrom((uint8_t)TCS, (uint8_t)8);
  for (uint8_t i = 0; i < 8; i++) d[i] = Wire.read();
  c = d[0] | (d[1] << 8);
  r = d[2] | (d[3] << 8);
  g = d[4] | (d[5] << 8);
  b = d[6] | (d[7] << 8);
}

uint8_t clasifica(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  float s = (float)r + g + b + 1;
  float rn = r / s, gn = g / s, bn = b / s;
  uint8_t mejor = 0;
  float dmin = 1e9;
  for (uint8_t i = 0; i < NCOL; i++) {
    float lc = log((c + 1.0) / (refs[i].c + 1.0));
    float d = sq(rn - refs[i].r) + sq(gn - refs[i].g) + sq(bn - refs[i].b) + 0.01 * sq(lc);
    if (d < dmin) { dmin = d; mejor = i; }
  }
  return dmin < DIST_MAX ? mejor : 0;
}

uint8_t ultimo = 0, racha = 0;
bool armado = true;

// Devuelve un color solo en el flanco piso -> marca, sostenido 3 lecturas
uint8_t eventoColor() {
  uint16_t c, r, g, b;
  tcsLee(c, r, g, b);
  uint8_t k = clasifica(r, g, b, c);
  racha = (k == ultimo) ? racha + 1 : 1;
  ultimo = k;
  if (racha < 3) return 0;
  if (k == 0) {
    armado = true;
    return 0;
  }
  if (!armado) return 0;
  armado = false;
  return k;
}

// ---------- VL53L0X ----------
bool tofInit() {
  for (uint8_t i = 0; i < 3; i++) {
    pinMode(XSHUT[i], OUTPUT);
    digitalWrite(XSHUT[i], LOW);
  }
  delay(10);
  for (uint8_t i = 0; i < 3; i++) {
    pinMode(XSHUT[i], INPUT);   // el modulo tiene pull-up propio
    delay(10);
    tof[i].setTimeout(50);
    if (!tof[i].init()) return false;
    tof[i].setAddress(0x30 + i);
    tof[i].setMeasurementTimingBudget(20000);
    tof[i].startContinuous();
  }
  return true;
}

void tofLee() {
  for (uint8_t i = 0; i < 3; i++) {
    if ((tof[i].readReg(VL53L0X::RESULT_INTERRUPT_STATUS) & 0x07) == 0) continue;
    uint16_t d = tof[i].readRangeContinuousMillimeters();
    dist[i] = (d == 0 || d > 2000) ? 9999 : d;
  }
}

// ---------- OLED ----------
void pinta() {
  oled.setCursor(0, 0);
  oled.print(F("LABERINTO "));
  oled.print(EST[estado]);
  oled.clearToEOL();
  uint8_t total = 0;
  for (uint8_t i = 1; i < NCOL; i++) {
    oled.setCursor(0, i + 1);
    oled.print(refs[i].nom);
    oled.setCol(70);
    oled.print(cuenta[i]);
    oled.clearToEOL();
    total += cuenta[i];
  }
  oled.setCursor(70, 7);
  oled.print(F("T: "));
  oled.print(total);
  oled.clearToEOL();
}

// ---------- Mapa ----------
bool dentro(int8_t x, int8_t y) { return x >= 0 && x < N && y >= 0 && y < N; }

void setPared(uint8_t x, uint8_t y, uint8_t d) {
  celda[x * N + y] |= 1 << d;
  int8_t nx = x + DX[d], ny = y + DY[d];
  if (dentro(nx, ny)) celda[nx * N + ny] |= 1 << ((d + 2) % 4);
}

void bordes() {
  for (uint8_t i = 0; i < N; i++) {
    setPared(i, 0, 2);
    setPared(i, N - 1, 0);
    setPared(0, i, 3);
    setPared(N - 1, i, 1);
  }
}

void guardar() {
  EEPROM.update(0, 0xA5);
  for (uint16_t i = 0; i < N * N; i++) EEPROM.update(1 + i, celda[i]);
}

void borrar() {
  memset(celda, 0, sizeof(celda));
  memset(cuenta, 0, sizeof(cuenta));
  bordes();
  guardar();
}

void cargar() {
  if (EEPROM.read(0) != 0xA5) {
    borrar();
    return;
  }
  for (uint16_t i = 0; i < N * N; i++) {
    celda[i] = EEPROM.read(1 + i);
    uint8_t c = celda[i] >> 5;
    if (c && c < NCOL) cuenta[c]++;
  }
}

bool enMeta(bool inicio, uint8_t x, uint8_t y) {
  if (inicio) return x == INI_X && y == INI_Y;
  return x >= META_X && x <= META_X + 1 && y >= META_Y && y <= META_Y + 1;
}

// BFS desde el objetivo; solo = usar solo celdas ya visitadas
void flood(bool inicio, bool solo) {
  static uint8_t q[N * N];
  uint16_t h = 0, t = 0;
  memset(dis, 255, sizeof(dis));
  for (uint8_t x = 0; x < N; x++)
    for (uint8_t y = 0; y < N; y++)
      if (enMeta(inicio, x, y)) {
        dis[x * N + y] = 0;
        q[t++] = x * N + y;
      }
  while (h < t) {
    uint8_t i = q[h++];
    int8_t x = i / N, y = i % N;
    for (uint8_t d = 0; d < 4; d++) {
      if (celda[i] & (1 << d)) continue;
      int8_t nx = x + DX[d], ny = y + DY[d];
      if (!dentro(nx, ny)) continue;
      uint8_t j = nx * N + ny;
      if (dis[j] != 255) continue;
      if (solo && !((celda[i] & VISTO) && (celda[j] & VISTO))) continue;
      dis[j] = dis[i] + 1;
      q[t++] = j;
    }
  }
}

// ---------- Movimiento ----------
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

void registraColor(uint8_t ox, uint8_t oy, float prog) {
  uint8_t c = eventoColor();
  if (!c) return;
  uint8_t k = prog + OFF_COLOR + 0.5;
  int8_t x = ox + DX[rumbo] * k, y = oy + DY[rumbo] * k;
  if (!dentro(x, y)) return;
  uint8_t &m = celda[x * N + y];
  if (m >> 5) return;   // esta celda ya tiene marca contada
  m |= c << 5;
  cuenta[c]++;
  pinta();
}

float centrado() {
  bool L = dist[0] < PARED, R = dist[2] < PARED;
  int e = 0;
  if (L && R) e = (int)dist[0] - (int)dist[2];
  else if (L) e = (int)dist[0] - (int)D_LADO;
  else if (R) e = (int)D_LADO - (int)dist[2];
  return constrain(KC * e, -40, 40) + AJUSTE_DER / 2.0;
}

void avanzar(uint8_t n, bool rapido) {
  uint16_t tc = rapido ? T_RAPIDA : T_CELDA;
  uint16_t dur = n * tc, extra = dur + tc / 3, zona = tc / 4;
  uint8_t vmax = rapido ? VEL_RAPIDA : VEL_EXPLORA;
  uint16_t t0 = ahora();
  float v = VEL_MIN;
  while (true) {
    if (!esperaTick()) continue;
    uint16_t t = ahora() - t0;
    tofLee();
    if (t % 3 == 0) registraColor(px, py, t / (float)tc);
    bool paredF = dist[1] < PARED;
    if (paredF && dist[1] <= D_FRENTE) break;
    if (t >= dur && !(paredF && t < extra)) break;
    uint16_t falta = dur > t ? dur - t : 0;
    float tope = falta < zona ? VEL_MIN + (vmax - VEL_MIN) * falta / (float)zona : vmax;
    v = min(v + 6.0f, tope);
    float corr = centrado();
    motores(v - corr, v + corr);
  }
  frena();
  px += DX[rumbo] * n;
  py += DY[rumbo] * n;
}

void girar(int8_t q) {
  if (!q) return;
  int8_t s = q > 0 ? 1 : -1;
  uint16_t t0 = ahora(), dur = abs(q) * T_90;
  while (ahora() - t0 < dur) {
    if (!esperaTick()) continue;
    tofLee();
    if ((ahora() - t0) % 3 == 0) registraColor(px, py, 0);
    motores(s * VEL_GIRO, -s * VEL_GIRO);
  }
  frena();
  rumbo = (rumbo + q + 4) % 4;
}

void girarA(uint8_t h) {
  uint8_t dif = (h - rumbo + 4) % 4;
  girar(dif == 3 ? -1 : dif);
}

void sensar() {
  uint8_t &m = celda[px * N + py];
  if (m & VISTO) return;
  uint16_t t0 = ahora();
  while (ahora() - t0 < 6) tofLee();
  if (dist[0] < PARED) setPared(px, py, (rumbo + 3) % 4);
  if (dist[1] < PARED) setPared(px, py, rumbo);
  if (dist[2] < PARED) setPared(px, py, (rumbo + 1) % 4);
  m |= VISTO;
}

// ---------- Estrategias ----------
bool explorar(bool inicio, uint8_t est) {
  static const uint8_t orden[4] = {0, 1, 3, 2};   // prefiere seguir derecho
  estado = est;
  pinta();
  while (!enMeta(inicio, px, py)) {
    sensar();
    flood(inicio, false);
    uint8_t i = px * N + py;
    if (dis[i] == 255) return false;
    int8_t mejor = -1;
    uint8_t dm = 255;
    for (uint8_t o = 0; o < 4; o++) {
      uint8_t d = (rumbo + orden[o]) % 4;
      if (celda[i] & (1 << d)) continue;
      int8_t nx = px + DX[d], ny = py + DY[d];
      if (!dentro(nx, ny)) continue;
      if (dis[nx * N + ny] < dm) {
        dm = dis[nx * N + ny];
        mejor = d;
      }
    }
    if (mejor < 0) return false;
    girarA(mejor);
    avanzar(1, false);
  }
  sensar();
  guardar();
  return true;
}

bool rutaConocida() {
  flood(false, true);
  return dis[INI_X * N + INI_Y] != 255;
}

void rapida() {
  estado = 3;
  pinta();
  while (!enMeta(false, px, py)) {
    uint8_t i = px * N + py;
    uint8_t h = 0;
    for (uint8_t d = 0; d < 4; d++) {
      int8_t nx = px + DX[d], ny = py + DY[d];
      if (!(celda[i] & (1 << d)) && dentro(nx, ny) && dis[nx * N + ny] == dis[i] - 1) {
        h = d;
        break;
      }
    }
    uint8_t n = 0;
    int8_t cx = px, cy = py;
    while (true) {
      uint8_t c = cx * N + cy;
      int8_t nx = cx + DX[h], ny = cy + DY[h];
      if ((celda[c] & (1 << h)) || !dentro(nx, ny) || dis[nx * N + ny] != dis[c] - 1) break;
      cx = nx;
      cy = ny;
      n++;
    }
    girarA(h);
    avanzar(n, true);
  }
}

// ---------- Calibracion: encender con el boton presionado ----------
void calibracion() {
  oled.clear();
  while (true) {
    uint16_t c, r, g, b;
    tcsLee(c, r, g, b);
    tofLee();
    float s = (float)r + g + b + 1;
    oled.setCursor(0, 0);
    oled.print(F("CALIBRACION"));
    oled.setCursor(0, 2); oled.print(F("r ")); oled.print(r / s, 2); oled.clearToEOL();
    oled.setCursor(0, 3); oled.print(F("g ")); oled.print(g / s, 2); oled.clearToEOL();
    oled.setCursor(0, 4); oled.print(F("b ")); oled.print(b / s, 2); oled.clearToEOL();
    oled.setCursor(0, 5); oled.print(F("c ")); oled.print(c);
    oled.print(' '); oled.print(refs[clasifica(r, g, b, c)].nom); oled.clearToEOL();
    oled.setCursor(0, 7);
    oled.print(dist[0]); oled.print(' ');
    oled.print(dist[1]); oled.print(' ');
    oled.print(dist[2]); oled.clearToEOL();
    delay(200);
  }
}

void falla(const __FlashStringHelper* msg) {
  oled.clear();
  oled.print(msg);
  while (true);
}

void setup() {
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(BTN, INPUT_PULLUP);
  motores(0, 0);

  Wire.begin();
  Wire.setClock(400000);
  oled.begin(&Adafruit128x64, 0x3C);
  oled.setFont(System5x7);
  oled.clear();
  if (!tcsInit()) falla(F("SIN SENSOR COLOR"));
  if (!tofInit()) falla(F("SIN VL53L0X"));
  timer1();
  if (digitalRead(BTN) == LOW) calibracion();
  cargar();
  pinta();
}

void loop() {
  if (digitalRead(BTN) == HIGH) return;
  uint16_t t0 = ahora();
  delay(30);
  while (digitalRead(BTN) == LOW);
  if (ahora() - t0 > 200) {   // sostenido mas de 2 s
    borrar();
    estado = 5;
    pinta();
    return;
  }
  delay(500);
  px = INI_X;
  py = INI_Y;
  rumbo = INI_R;
  if (rutaConocida()) {
    rapida();
    estado = 4;
  } else {
    explorar(false, 1);
    explorar(true, 2);
    estado = 0;
  }
  guardar();
  pinta();
}
