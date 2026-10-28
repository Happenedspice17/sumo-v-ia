#include "config.h"
#include "motores.h"
#include "tiempo.h"
#include <stdlib.h>

void motoresInit() {
  DDRD |= _BV(PD5) | _BV(PD6) | _BV(PD7);
  DDRB |= _BV(PB0) | _BV(PB1) | _BV(PB2);
  TCCR0A = _BV(WGM01) | _BV(WGM00);   // Fast PWM 8 bits; salidas conectadas en pwm()
  TCCR0B = _BV(CS01) | _BV(CS00);     // prescaler 64
  motores(0, 0);
}

// izq = OC0B (D5, ENA), der = OC0A (D6, ENB). Con 0 se desconecta la salida para que no quede un pulso.
static void pwm(bool der, uint8_t v) {
  uint8_t com = der ? _BV(COM0A1) : _BV(COM0B1);
  if (der) OCR0A = v; else OCR0B = v;
  if (v) TCCR0A |= com;
  else {
    TCCR0A &= ~com;
    PORTD &= ~(der ? _BV(PD6) : _BV(PD5));
  }
}

static uint8_t limita(int v) {
  v = abs(v);
  return v > 255 ? 255 : v;
}

void motores(int l, int r) {
  if (l >= 0) PORTD |= _BV(PD7); else PORTD &= ~_BV(PD7);   // IN1
  if (l < 0) PORTB |= _BV(PB0); else PORTB &= ~_BV(PB0);    // IN2
  if (r >= 0) PORTB |= _BV(PB1); else PORTB &= ~_BV(PB1);   // IN3
  if (r < 0) PORTB |= _BV(PB2); else PORTB &= ~_BV(PB2);    // IN4
  pwm(false, limita(l));
  pwm(true, limita(r));
}

void frena() {
  PORTD |= _BV(PD7);
  PORTB |= _BV(PB0) | _BV(PB1) | _BV(PB2);
  pwm(false, 255);
  pwm(true, 255);
  esperaMs(60);
  pwm(false, 0);
  pwm(true, 0);
}
