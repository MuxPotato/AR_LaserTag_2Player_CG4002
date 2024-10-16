#include <TimerFreeTone.h>
#include <IRremote.hpp>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>

#define EXPECTED_IR_ADDRESS 0x0102
#define BUZZER_PIN 4
#define GUNSHOT_HIT_BUZZER_FREQ 400
#define PLAYER_FULL_HP 100
#define IR_RECV_PIN 5
#define LED_PIN LED_BUILTIN
#define LED_STRIP_PIN 3
#define NUM_HP_LED 10

void irReceiverSetup();
void checkHealth();
void doDamage();
void doGunshotHit();
void doRespawn();
bool getIsShotFromIr();
void giveLife();
void updateHpLed(uint8_t givenPlayerHp);
