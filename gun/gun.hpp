#include <TimerFreeTone.h>
#include <Adafruit_NeoPixel.h>
#include <IRremote.hpp>
#include <Wire.h>
#include "packet.hpp"

#define ACTION_INTERVAL 600
#define BUTTON_PIN 4
#define BUTTON_DEBOUNCE_DELAY 5
#define LED_PIN LED_BUILTIN
#define IR_COMMAND 0x34
#define IR_TRN_PIN 5
#define LED_STRIP_PIN 3
#define PIXEL_COUNT 8
#define PIXEL_BRIGHTNESS 60
#define BUZZER_PIN 2
#define GUN_MAGAZINE_SIZE 6
#define GUN_MAGAZINE_EMPTY_BUZZER_FREQ 350
#define GUN_MAGAZINE_EMPTY_BUZZER_DURATION 200
#define GUNFIRE_BUZZER_FREQ 1300
#define GUNFIRE_BUZZER_DURATION 100
#define RELOAD_BUZZER_FREQ 600
#define RELOAD_BUZZER_DURATION 150
// Player-specific macros
#define PLAYER_ID 1
#define IR_ADDRESS_PLAYER_1 0xABCD
#define IR_ADDRESS_PLAYER_2 0x1234
#define GET_OUR_IR_ADDRESS() ((PLAYER_ID == 1) ? IR_ADDRESS_PLAYER_1 : IR_ADDRESS_PLAYER_2)

IRsend irsend(IR_TRN_PIN);
Adafruit_NeoPixel pixels(PIXEL_COUNT, LED_STRIP_PIN, NEO_GRB + NEO_KHZ800);

BlePacket createGunPacket(bool mIsFired);
void gunSetup();
void fireGun();
byte getButtonState();
bool getIsFired();
void reload();
void visualiseBulletCount();

void getPacketDataFor(bool mIsFired, byte packetData[PACKET_DATA_SIZE]) {
  packetData[0] = mIsFired ? 1 : 0;
}