#include "config.h"
#include "tiempo.h"
#include <avr/interrupt.h>
#include <util/atomic.h>

static volatile uint32_t cuentaMs = 0;
static volatile uint16_t ticks = 0;
static volatile bool tick = false;

ISR(TIMER1_COMPA_vect) {
  static uint8_t sub = 0;
  cuentaMs++;
  if (++sub == 10) {
    sub = 0;
    ticks++;
    tick = true;
  }
}

void tiempoInit() {
  TCCR1A = 0;
  TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);   // CTC, prescaler 64
  OCR1A = 249;                                   // 16 MHz / 64 / 250 = 1 kHz
  TIMSK1 = _BV(OCIE1A);
  sei();
}

uint32_t ms() {
  uint32_t t;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { t = cuentaMs; }
  return t;
}

uint16_t ahora() {
  uint16_t t;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { t = ticks; }
  return t;
}

bool esperaTick() {
  if (!tick) return false;
  tick = false;
  return true;
}

void esperaMs(uint16_t t) {
  uint32_t t0 = ms();
  while (ms() - t0 < t);
}
