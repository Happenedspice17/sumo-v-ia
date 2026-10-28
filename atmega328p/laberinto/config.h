#pragma once
#ifndef F_CPU
#define F_CPU 16000000UL
#endif
#include <avr/io.h>
#include <stdint.h>

// ---------- Pines (Arduino Nano) ----------
// ENA D5=PD5 (OC0B)  ENB D6=PD6 (OC0A)
// IN1 D7=PD7  IN2 D8=PB0  IN3 D9=PB1  IN4 D10=PB2
// Boton D2=PD2  XSHUT A0..A2=PC0..PC2  I2C A4=SDA A5=SCL
#define BTN_ABAJO() (!(PIND & _BV(PD2)))

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
const uint16_t D_FRENTE = 34;   // mm al frente con el robot centrado en la celda
const uint16_t D_LADO = 38;     // mm a una pared lateral con el robot centrado
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
