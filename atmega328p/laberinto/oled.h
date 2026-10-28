#pragma once
#include <stdint.h>

// SSD1306 128x64 por I2C (0x3C), texto 5x7 en 8 renglones de 21 caracteres
bool oledInit();
void oledBorra();
void oledPos(uint8_t col, uint8_t renglon);   // col en pixeles 0-127
void oledLetra(char c);
void oledTexto(const char* s);
void oledTextoP(const char* s);               // texto en flash (PSTR)
void oledNum(int32_t n);
void oledDec(int32_t n, uint8_t dec);         // n con punto decimal: oledDec(57, 2) -> 0.57
void oledFinRenglon();                        // borra hasta el final del renglon
