#pragma once
#include <stdint.h>

// TCS34725 por registros I2C (0x29)
bool tcsInit();
void tcsLee(uint16_t &c, uint16_t &r, uint16_t &g, uint16_t &b);
