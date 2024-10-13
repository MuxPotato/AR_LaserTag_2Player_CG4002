#include <TimerFreeTone.h>
#include <IRremote.hpp>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>

#define EXPECTED_IR_ADDRESS 0x0102
#define BUZZER_PIN 4
#define IR_RECV_PIN 5
#define LED_PIN LED_BUILTIN
#define LED_STRIP_PIN 3
#define PIXEL_COUNT 10

void irReceiverSetup();
void checkHealth();
bool checkIrReceiver();
void giveLife();
