#include "packet.h"

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
}

void loop() {
  // put your main code here, to run repeatedly:
  if (Serial.available()) {        
    Serial.write(Serial.read());
  }
}

/**
 * Performs 3-way handshake.
 * 
 * Returns: boolean where true signifies successful handshake and false signifies failed handshake
 */
bool doHandshake() {
  if (!Serial.available()) {
    return false;
  }
  // At this point, Bluetooth connection is confirmed established
  return true;
}
