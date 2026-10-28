#include "config.h"
#include "oled.h"
#include "twi.h"
#include "fuente.h"

#define OLED 0x3C

static uint8_t columna = 0;

static const uint8_t INICIO[] PROGMEM = {
  0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0x8D, 0x14, 0x20, 0x02,
  0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
};

static void comando(uint8_t c) {
  twiEscribeReg(OLED, 0x00, &c, 1);
}

bool oledInit() {
  if (twiInicio(OLED)) return false;
  twiAlto();
  for (uint8_t i = 0; i < sizeof(INICIO); i++) comando(pgm_read_byte(&INICIO[i]));
  oledBorra();
  return true;
}

void oledPos(uint8_t col, uint8_t renglon) {
  columna = col;
  comando(0xB0 | (renglon & 7));
  comando(col & 0x0F);
  comando(0x10 | (col >> 4));
}

static void datos(const uint8_t* d, uint8_t n, bool flash) {
  if (twiInicio(OLED)) return;
  twiByte(0x40);
  while (n--) twiByte(flash ? pgm_read_byte(d++) : *d++);
  twiAlto();
}

void oledFinRenglon() {
  static const uint8_t cero[16] = {0};
  while (columna < 128) {
    uint8_t n = 128 - columna > 16 ? 16 : 128 - columna;
    datos(cero, n, false);
    columna += n;
  }
}

void oledBorra() {
  for (uint8_t r = 0; r < 8; r++) {
    oledPos(0, r);
    oledFinRenglon();
  }
  oledPos(0, 0);
}

void oledLetra(char c) {
  if (columna > 122) return;
  if (c < 32 || c > 126) c = '?';
  uint8_t g[6];
  for (uint8_t i = 0; i < 5; i++) g[i] = pgm_read_byte(&FUENTE[(c - 32) * 5 + i]);
  g[5] = 0;
  datos(g, 6, false);
  columna += 6;
}

void oledTexto(const char* s) {
  while (*s) oledLetra(*s++);
}

void oledTextoP(const char* s) {
  char c;
  while ((c = pgm_read_byte(s++))) oledLetra(c);
}

void oledNum(int32_t n) {
  char b[12];
  uint8_t i = 0;
  if (n < 0) { oledLetra('-'); n = -n; }
  do { b[i++] = '0' + n % 10; n /= 10; } while (n);
  while (i) oledLetra(b[--i]);
}

void oledDec(int32_t n, uint8_t dec) {
  int32_t p = 1;
  for (uint8_t i = 0; i < dec; i++) p *= 10;
  if (n < 0) { oledLetra('-'); n = -n; }
  oledNum(n / p);
  oledLetra('.');
  int32_t f = n % p;
  for (p /= 10; p > f && p > 1; p /= 10) oledLetra('0');
  oledNum(f);
}
