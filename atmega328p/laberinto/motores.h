#pragma once
#include <stdint.h>

// L298N: PWM con Timer0 (Fast PWM, ~977 Hz) en D5/D6, direccion en D7-D10
void motoresInit();
void motores(int l, int r);   // -255..255
void frena();
