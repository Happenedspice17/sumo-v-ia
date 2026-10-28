# Compilar y cargar sin Microchip Studio:  make  /  make cargar PUERTO=COM5
MCU = atmega328p
F_CPU = 16000000UL
PUERTO ?= /dev/ttyUSB0
BAUD ?= 115200
CXXFLAGS = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=gnu++11 -Wall -ffunction-sections -fdata-sections -fno-exceptions
SRC = $(wildcard *.cpp)

laberinto.hex: laberinto.elf
	avr-objcopy -O ihex -R .eeprom $< $@
	avr-size -C --mcu=$(MCU) $<

laberinto.elf: $(SRC) $(wildcard *.h)
	avr-g++ $(CXXFLAGS) -Wl,--gc-sections $(SRC) -lm -o $@

cargar: laberinto.hex
	avrdude -p $(MCU) -c arduino -P $(PUERTO) -b $(BAUD) -U flash:w:$<:i

clean:
	rm -f laberinto.elf laberinto.hex
