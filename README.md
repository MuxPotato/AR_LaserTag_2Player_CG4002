# Source code structure
`ble/`: Base Beetle code that performs internal comms(transmits dummy packets that are randomly generated floats to immitate IMU data)
- Requires CRC library
`glove/`: Arduino code for glove Beetle that integrates MPU6050 logic with internal comms logic to transmit accelerometer and gyroscope code to the relay node
- NOTE: Tested and verified to be working
- Requires CRC library
`gun/`: Arduino code for gun Beetle that integrates IR transmitter logic with internal comms logic to transmit IR data as gun packets
- NOTE: UNTESTED and currently sends dummy packets immitating isFired
- Requires CRC, IRremote library
`vest/`: Arduino code for vest Beetle that integrates IR receiver logic with internal comms logic to transmit IR data as vest packets
- NOTE: UNTESTED and currently sends dummy packets immitating isHit
- Requires CRC, IRremote and Adafruit NeoPixel library

# Arduino libraries required
- CRC by Rob Tillaart: https://github.com/RobTillaart/CRC
- IRremote by shirriff, z3t0, ArminJo: https://github.com/Arduino-IRremote/Arduino-IRremote
- Adafruit NeoPixel: https://github.com/adafruit/Adafruit_NeoPixel

