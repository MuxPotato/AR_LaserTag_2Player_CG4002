# Overview
- Laptop connects to each Beetle via BLE 4.0 using the Python bluepy library
- Transmit/Receive protocol used is stop-and-wait half-duplex(Beetle->laptop)
- ACK and NACK is implemented for reliable transmission: Detecting packet loss(ACK) and packet corruption(NACK)
- A variant of TCP's 3-way handshake is also implemented to initialise each Beetle's BLE connection
- Sequence number implemented currently is only for the Beetle(sender), laptop simply synchronises its sequence number with whatever the Beetle's currently is

# Source code structure
## `ble/`: Base Beetle code that performs internal comms(transmits dummy packets that are randomly generated floats to immitate IMU data)
- Requires CRC library
## `glove/`: Arduino code for glove Beetle that integrates MPU6050 logic with internal comms logic to transmit accelerometer and gyroscope code to the relay node
- NOTE: Tested and verified to be working
- Requires CRC library
## `gun/`: Arduino code for gun Beetle that integrates IR transmitter logic with internal comms logic to transmit IR data as gun packets
- NOTE: UNTESTED and currently sends dummy packets immitating isFired
- Requires CRC, IRremote library
## `vest/`: Arduino code for vest Beetle that integrates IR receiver logic with internal comms logic to transmit IR data as vest packets
- NOTE: UNTESTED and currently sends dummy packets immitating isHit
- Requires CRC, IRremote and Adafruit NeoPixel, TimerFreeTone library

# Setup
- Open any of the inos in the subfolders of this repository with `Arduino IDE`
- Compile and upload the sketch to your Beetle
- Factory reset following the steps below

## Factory reset
- Open Arduino IDE's `Serial Monitor`
- Set the line ending to `No Line Ending`, baudrate to `115200 baud`
- Send the command `+++` to the Beetle. You should see a response `Enter AT Mode`
- Change the line ending to `Both NL & CR`. Keep baudrate at `115200 baud`.
- Send the command `AT+SETTING=DEFAULT`. You should see a response `OK`
- Send the command `AT+EXIT` to exit AT mode. You should see a response `OK`
Perform factory reset of your Beetle whenever you notice that it's transmitting corrupted data. Sometimes it's not your code that's buggy, but the Beetle.

# Arduino libraries required
- CRC by Rob Tillaart: https://github.com/RobTillaart/CRC
- IRremote by shirriff, z3t0, ArminJo: https://github.com/Arduino-IRremote/Arduino-IRremote
- Adafruit NeoPixel: https://github.com/adafruit/Adafruit_NeoPixel
- TimerFreeTone by Tim Eckel: https://bitbucket.org/teckel12/arduino-timer-free-tone/wiki/Home#!download-install

