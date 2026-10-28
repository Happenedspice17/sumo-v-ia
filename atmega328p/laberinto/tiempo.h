#pragma once
#include <stdint.h>

// Timer1 en CTC a 1 kHz: cuenta milisegundos y marca un tick cada 10 ms
void tiempoInit();
uint32_t ms();
uint16_t ahora();        // ticks de 10 ms
bool esperaTick();       // true una vez por tick
void esperaMs(uint16_t t);
