#include <Adafruit_NeoPixel.h>
#include <IRremote.hpp>
#include <Wire.h>

#define ACTION_INTERVAL 600
#define BUTTON_PIN 4
#define BUTTON_DEBOUNCE_DELAY 5
#define LED_PIN LED_BUILTIN
#define IR_ADDRESS 0x0102
#define IR_COMMAND 0x34
#define IR_TRN_PIN 5
#define LED_STRIP_PIN 3
#define PIXEL_COUNT 8
#define PIXEL_BRIGHTNESS 60
#define BUZZER_DURATION 200
#define BUZZER_FREQ 2000
#define BUZZER_PIN 2
#define GUN_MAGAZINE_SIZE 6
#define RELOAD_BUZZER_FREQ 3000
#define RELOAD_BUZZER_DURATION 500

IRsend irsend(IR_TRN_PIN);
Adafruit_NeoPixel pixels(PIXEL_COUNT, LED_STRIP_PIN, NEO_GRB + NEO_KHZ800);

void gunSetup();
byte getButtonState();
bool getIsFired();
void reload();
void visualiseBulletCount();