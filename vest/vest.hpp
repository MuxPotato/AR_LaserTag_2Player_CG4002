#include <IRremote.hpp>
#include <Wire.h>

#define EXPECTED_IR_ADDRESS 0x0102
#define BUTTON_PIN 4
#define IR_RECV_PIN 5
#define LED_PIN LED_BUILTIN

bool checkIrReceiver();
void irReceiverSetup();
