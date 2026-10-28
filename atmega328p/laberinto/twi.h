#pragma once
#include <stdint.h>

// I2C maestro por registros (TWI), 400 kHz. Las funciones devuelven 0 si todo salio bien.
void twiInit();
uint8_t twiEscribeReg(uint8_t dir, uint8_t reg, const uint8_t* d, uint8_t n);
uint8_t twiLeeReg(uint8_t dir, uint8_t reg, uint8_t* d, uint8_t n);

// Para transmisiones largas (pantalla)
uint8_t twiInicio(uint8_t dir);
uint8_t twiByte(uint8_t b);
void twiAlto();
