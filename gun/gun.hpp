#include <Adafruit_NeoPixel.h>
#include <IRremote.hpp>
#include <Wire.h>

#define ACTION_INTERVAL 500
#define BUTTON_PIN 4
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

// Define pin numbers
const int buttonPin = 4;         // Pin connected to the button
const int ledPin = LED_BUILTIN;  // Pin connected to the built-in LED
const int irPin = 5;             // Pin connected to the IR transmitter
const int ledStripPin = 3;       //Pin connected to LED strip
const int pixelCount = 8;
const int buzzerPin = 2;

IRsend irsend(irPin);
Adafruit_NeoPixel pixels(pixelCount, ledStripPin, NEO_GRB + NEO_KHZ800);

void reload();
void visualiseBulletCount();