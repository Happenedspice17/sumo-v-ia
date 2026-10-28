#include "config.h"
#include "twi.h"
#include <util/twi.h>

void twiInit() {
  PORTC |= _BV(PC4) | _BV(PC5);          // pull-ups internos (los modulos ya traen los suyos)
  TWSR = 0;                              // prescaler 1
  TWBR = ((F_CPU / 400000UL) - 16) / 2;  // 400 kHz
  TWCR = _BV(TWEN);
}

// Espera TWINT; si el bus se traba no se queda colgado para siempre
static bool espera() {
  uint16_t n = 0;
  while (!(TWCR & _BV(TWINT)))
    if (++n == 0) return false;
  return true;
}

void twiAlto() {
  TWCR = _BV(TWINT) | _BV(TWSTO) | _BV(TWEN);
  uint16_t n = 0;
  while ((TWCR & _BV(TWSTO)) && ++n);
}

static uint8_t arranque(uint8_t sla) {
  TWCR = _BV(TWINT) | _BV(TWSTA) | _BV(TWEN);
  if (!espera()) return 1;
  uint8_t s = TW_STATUS;
  if (s != TW_START && s != TW_REP_START) return 2;
  TWDR = sla;
  TWCR = _BV(TWINT) | _BV(TWEN);
  if (!espera()) return 1;
  s = TW_STATUS;
  if (s != TW_MT_SLA_ACK && s != TW_MR_SLA_ACK) return 3;
  return 0;
}

uint8_t twiInicio(uint8_t dir) {
  uint8_t e = arranque(dir << 1);
  if (e) twiAlto();
  return e;
}

uint8_t twiByte(uint8_t b) {
  TWDR = b;
  TWCR = _BV(TWINT) | _BV(TWEN);
  if (!espera()) return 1;
  return TW_STATUS == TW_MT_DATA_ACK ? 0 : 4;
}

uint8_t twiEscribeReg(uint8_t dir, uint8_t reg, const uint8_t* d, uint8_t n) {
  uint8_t e = arranque(dir << 1);
  if (!e) e = twiByte(reg);
  while (!e && n--) e = twiByte(*d++);
  twiAlto();
  return e;
}

uint8_t twiLeeReg(uint8_t dir, uint8_t reg, uint8_t* d, uint8_t n) {
  uint8_t e = arranque(dir << 1);
  if (!e) e = twiByte(reg);
  if (!e) e = arranque((dir << 1) | 1);   // repeated start
  while (!e && n) {
    TWCR = _BV(TWINT) | _BV(TWEN) | (n > 1 ? _BV(TWEA) : 0);
    if (!espera()) e = 1;
    else *d++ = TWDR;
    n--;
  }
  twiAlto();
  return e;
}
