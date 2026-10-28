// Robot de laberinto - Arduino Nano (ATmega328P), C++ sin librerias de Arduino
// Perifericos usados: TWI (I2C), Timer0 (PWM motores), Timer1 (base de tiempo), EEPROM
#include "config.h"
#include <avr/eeprom.h>
#include <avr/pgmspace.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include "tiempo.h"
#include "twi.h"
#include "oled.h"
#include "tcs.h"
#include "motores.h"
#include "VL53L0X.h"

// Cada celda: bits 0-3 paredes (N,E,S,O), bit 4 visitada, bits 5-7 color de marca
#define VISTO 0x10
uint8_t celda[N * N];
uint8_t dis[N * N];
uint8_t cuenta[NCOL];
const int8_t DX[4] = {0, 1, 0, -1};
const int8_t DY[4] = {1, 0, -1, 0};
uint8_t px, py, rumbo, estado;
const char* const EST[] = {"LISTO", "EXPLORA", "REGRESO", "RAPIDO", "META", "BORRADO"};

VL53L0X tof[3];   // izq, frente, der
uint16_t dist[3] = {9999, 9999, 9999};

template <class T> T acota(T v, T a, T b) { return v < a ? a : (v > b ? b : v); }
float cuad(float x) { return x * x; }

// ---------- Color ----------
uint8_t clasifica(uint16_t r, uint16_t g, uint16_t b, uint16_t c) {
  float s = (float)r + g + b + 1;
  float rn = r / s, gn = g / s, bn = b / s;
  uint8_t mejor = 0;
  float dmin = 1e9;
  for (uint8_t i = 0; i < NCOL; i++) {
    float lc = log((c + 1.0) / (refs[i].c + 1.0));
    float d = cuad(rn - refs[i].r) + cuad(gn - refs[i].g) + cuad(bn - refs[i].b) + 0.01 * cuad(lc);
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
// XSHUT en PC0..PC2: salida en 0 = apagado; entrada = encendido (el modulo tiene pull-up a 2.8 V)
bool tofInit() {
  PORTC &= ~0x07;
  DDRC |= 0x07;
  esperaMs(10);
  for (uint8_t i = 0; i < 3; i++) {
    DDRC &= ~_BV(i);
    esperaMs(10);
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
  for (uint8_t i = 0; i < 3; i++) {
    if ((tof[i].readReg(VL53L0X::RESULT_INTERRUPT_STATUS) & 0x07) == 0) continue;
    uint16_t d = tof[i].readRangeContinuousMillimeters();
    dist[i] = (d == 0 || d > 2000) ? 9999 : d;
  }
}

// ---------- OLED ----------
void pinta() {
  oledPos(0, 0);
  oledTextoP(PSTR("LABERINTO "));
  oledTexto(EST[estado]);
  oledFinRenglon();
  uint8_t total = 0;
  for (uint8_t i = 1; i < NCOL; i++) {
    oledPos(0, i + 1);
    oledTexto(refs[i].nom);
    oledPos(70, i + 1);
    oledNum(cuenta[i]);
    oledFinRenglon();
    total += cuenta[i];
  }
  oledPos(70, 7);
  oledTextoP(PSTR("T: "));
  oledNum(total);
  oledFinRenglon();
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

#define EE_MARCA ((uint8_t*)0)
#define EE_MAPA ((uint8_t*)1)

void guardar() {
  eeprom_update_byte(EE_MARCA, 0xA5);
  eeprom_update_block(celda, EE_MAPA, sizeof(celda));
}

void borrar() {
  memset(celda, 0, sizeof(celda));
  memset(cuenta, 0, sizeof(cuenta));
  bordes();
  guardar();
}

void cargar() {
  if (eeprom_read_byte(EE_MARCA) != 0xA5) {
    borrar();
    return;
  }
  eeprom_read_block(celda, EE_MAPA, sizeof(celda));
  for (uint16_t i = 0; i < N * N; i++) {
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
  return acota(KC * e, -40.0f, 40.0f) + AJUSTE_DER / 2.0;
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
    v = v + 6 < tope ? v + 6 : tope;
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

// ---------- Boton ----------
// Espera a que se suelte y devuelve cuanto estuvo presionado, en ticks de 10 ms
uint16_t pulsacion() {
  uint16_t t0 = ahora();
  esperaMs(30);
  while (BTN_ABAJO());
  return ahora() - t0;
}

// ---------- Calibracion: encender con el boton presionado ----------
// Muestra color y distancias. Boton corto: avanza 1 celda. Boton largo: gira 90 grados a la derecha.
void calibracion() {
  oledBorra();
  while (BTN_ABAJO());
  esperaMs(50);
  while (true) {
    if (BTN_ABAJO()) {
      uint16_t t = pulsacion();
      esperaMs(500);
      if (t > 100) girar(1);
      else avanzar(1, false);
      oledBorra();
    }
    uint16_t c, r, g, b;
    tcsLee(c, r, g, b);
    tofLee();
    uint32_t s = (uint32_t)r + g + b + 1;
    oledPos(0, 0);
    oledTextoP(PSTR("CALIBRACION"));
    oledPos(0, 2); oledTextoP(PSTR("r ")); oledDec(r * 100UL / s, 2); oledFinRenglon();
    oledPos(0, 3); oledTextoP(PSTR("g ")); oledDec(g * 100UL / s, 2); oledFinRenglon();
    oledPos(0, 4); oledTextoP(PSTR("b ")); oledDec(b * 100UL / s, 2); oledFinRenglon();
    oledPos(0, 5); oledTextoP(PSTR("c ")); oledNum(c);
    oledLetra(' '); oledTexto(refs[clasifica(r, g, b, c)].nom); oledFinRenglon();
    oledPos(0, 7);
    oledNum(dist[0]); oledLetra(' ');
    oledNum(dist[1]); oledLetra(' ');
    oledNum(dist[2]); oledFinRenglon();
    uint16_t t1 = ahora();
    while (ahora() - t1 < 20 && !BTN_ABAJO()) tofLee();
  }
}

void falla(const char* msg) {
  oledBorra();
  oledTextoP(msg);
  motores(0, 0);
  while (true);
}

int main() {
  motoresInit();
  PORTD |= _BV(PD2);   // boton con pull-up
  tiempoInit();
  twiInit();
  esperaMs(50);
  oledInit();
  if (!tofInit()) falla(PSTR("SIN VL53L0X"));
  if (!tcsInit()) falla(PSTR("SIN SENSOR COLOR"));
  if (BTN_ABAJO()) calibracion();
  cargar();
  pinta();

  while (true) {
    if (!BTN_ABAJO()) continue;
    if (pulsacion() > 200) {   // sostenido mas de 2 s
      borrar();
      estado = 5;
      pinta();
      continue;
    }
    esperaMs(500);
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
}
