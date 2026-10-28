#include "config.h"
#include "tcs.h"
#include "twi.h"
#include "tiempo.h"

#define TCS 0x29

static void tcsW(uint8_t reg, uint8_t v) {
  twiEscribeReg(TCS, 0x80 | reg, &v, 1);
}

bool tcsInit() {
  uint8_t id = 0;
  if (twiLeeReg(TCS, 0x80 | 0x12, &id, 1)) return false;
  if (id != 0x44 && id != 0x4D) return false;
  tcsW(0x01, 0xF6);   // ATIME: 10 ciclos = 24 ms
  tcsW(0x0F, 0x01);   // ganancia 4x
  tcsW(0x00, 0x01);   // PON
  esperaMs(3);
  tcsW(0x00, 0x03);   // PON + AEN
  return true;
}

void tcsLee(uint16_t &c, uint16_t &r, uint16_t &g, uint16_t &b) {
  uint8_t d[8] = {0};
  twiLeeReg(TCS, 0xA0 | 0x14, d, 8);   // auto-incremento desde CDATAL
  c = d[0] | (d[1] << 8);
  r = d[2] | (d[3] << 8);
  g = d[4] | (d[5] << 8);
  b = d[6] | (d[7] << 8);
}
