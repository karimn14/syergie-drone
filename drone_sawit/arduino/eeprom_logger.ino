// eeprom_logger.ino – Log spray counts and errors to EEPROM
#include <EEPROM.h>
#define SPRAY_COUNT_ADDR 0
#define ERROR_COUNT_ADDR 10

int sprayCount = 0;
int errorCount = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  sprayCount = EEPROM.read(SPRAY_COUNT_ADDR);
  errorCount = EEPROM.read(ERROR_COUNT_ADDR);
  Serial.print("Spray count: "); Serial.println(sprayCount);
  Serial.print("Error count: "); Serial.println(errorCount);
}

void logSpray() {
  sprayCount++;
  EEPROM.write(SPRAY_COUNT_ADDR, sprayCount);
}

void logError() {
  errorCount++;
  EEPROM.write(ERROR_COUNT_ADDR, errorCount);
}

void loop() {
  // Example usage: call logSpray() or logError() in your main sprayer logic
}
