#include "packet.h"
#include "CRC8.h"

bool doHandshake();

bool hasHandshake = false;
uint16_t seqNum = 0;
String receiveBuffer = "";

void createPacket(BlePacket &packet, byte packetType, short seqNum, byte data[16]) {
  packet.metadata = packetType;
  packet.packetId = seqNum;
  for (byte i = 0; i < 16; i += 1) {
    packet.data[i] = data[i];
  }
  // TODO: Implement proper checksum
  packet.checksum = 1;
}

void sendDummyPacket() {
  BlePacket dummyPacket;
  dummyPacket.metadata = 0;
  dummyPacket.packetId = 2;
  dummyPacket.data[0] = (byte)'D';
  dummyPacket.data[1] = (byte)'U';
  dummyPacket.data[2] = (byte)'M';
  dummyPacket.data[3] = (byte)'M';
  dummyPacket.data[4] = (byte)'Y';
  //dummyPacket.checksum = 1;
  CRC8 crcGen;
  crcGen.add((uint8_t) dummyPacket.metadata);
  crcGen.add((uint8_t) dummyPacket.packetId);
  for (auto c : dummyPacket.data) {
    crcGen.add((uint8_t) c);
  }
  dummyPacket.checksum = crcGen.calc();
  Serial.write((byte *) &dummyPacket, sizeof(dummyPacket));
}

void sendAckPacket() {
  BlePacket ackPacket;
  ackPacket.metadata = 1;
  ackPacket.packetId = 0;
  ackPacket.data[0] = (byte)'A';
  ackPacket.data[1] = (byte)'C';
  ackPacket.data[2] = (byte)'K';
  ackPacket.data[3] = 0;
  ackPacket.data[4] = 0;
  ackPacket.checksum = 1;
  Serial.write((byte *) &ackPacket, sizeof(ackPacket));
}

void sendSynPacket(byte seqNum) {
  BlePacket ackPacket;
  ackPacket.metadata = 1;
  ackPacket.packetId = 0;
  ackPacket.data[0] = (byte)'A';
  ackPacket.data[1] = (byte)'C';
  ackPacket.data[2] = (byte)'K';
  ackPacket.data[3] = 0;
  ackPacket.data[4] = 0;
  ackPacket.checksum = 1;
  Serial.write((byte *) &ackPacket, sizeof(ackPacket));
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
}

/* Works after resetting the AT settings and putting Beetle in GAP Peripheral mode again */
/* HELLO packet from laptop somehow not detected by Beetle still
 * But packet transmission from Beetle to laptop now works
 * Packet transmission from laptop to Beetle likely is working too, I just can't parse the incoming packets from laptop on the
* Beetle for some reason
 */
void loop() {
  if (Serial.available()) {
    char newByte = Serial.read();
    // Append new byte to receive buffer
    receiveBuffer += newByte;
    // ACK complete packet
    if (receiveBuffer.length() >= PACKET_SIZE) {
      String curr = receiveBuffer.substring(0, PACKET_SIZE);
      receiveBuffer.remove(0, PACKET_SIZE);
      /* if (curr == HELLO) {
        sendAckPacket();
        delay(50);
      } */
      if (curr.charAt(0) != packetIds::ACK) {
        sendAckPacket();
        delay(50);
      }
    }
   
    /*int result = 0;
    // Clear the receiver buffer
    while (Serial.available()) {
      result += Serial.read();
    }
    sendAckPacket(); */
    //Serial.write(Serial.read());
  } else {
    sendDummyPacket();
    delay(250);
    // 70: 01110000
    // 74: 01110100
  }
  //delay(250);
}

// Broken test code
/*void loop() {
  if (Serial.available() > 0) {
    String data = "";
    while (Serial.available()) {
      char newByte = Serial.read();
      data += newByte;
    }
      //Serial.write(data.c_str(), data.length());
      sendAckPacket();
      delay(10);
  } else {
    sendDummyPacket();
    delay(50);
  }
}*/

/* Broken actual code */
/*void loop() {
  // Received data via BLE
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  } else {
    if (Serial.available() > 0) {
      // String input = "";
      // for (int i = 0; i < PACKET_SIZE; i += 1) {
      //   input += Serial.read();
      //   // Block until the next byte arrives
      //   while (!Serial.available());
      // }
      // Input buffer is 64-bytes long, read and clear it before buffer becomes full
      int receivedByte = Serial.read();
      // Acknowledge received data
      if (byteCount >= 20) {
        sendAckPacket();
        byteCount -= 20;
        delay(10);
      }
    } else { // Periodic push
      sendDummyPacket();
      delay(50);
    }
  }
}*/

/**
 * Performs 3-way handshake.
 * 
 * Returns: boolean where true signifies successful handshake and false signifies failed handshake
 */
/*
bool doHandshake() {
  while (!Serial.available());
  // Data received, check whether it's a HELLO packet
  byte inputs[PACKET_SIZE];
  for (int i = 0; i < PACKET_SIZE; i += 1) {
    inputs[i] = Serial.read();
    if (!Serial.available()) {
      // Receiver buffer is somehow empty, data is missing
      // TODO: Can we gracefully handle this error?
      return false;
    }
  }
  if (inputs[0] == packetIds::HELLO) {
    sendAckPacket();
    delay(25);
  }
  // Wait for SYN+ACK packet
  // while (!Serial.available());
  // for (int i = 0; i < PACKET_SIZE; i += 1) {
  //   inputs[i] = Serial.read();
  //   if (!Serial.available()) {
  //     // Receiver buffer is somehow empty, data is missing
  //     // TODO: Can we gracefully handle this error?
  //     return false;
  //   }
  // }
  // return inputs[0] == packetIds::ACK;
  return true;
}
*/
bool doHandshake() {
  while (!Serial.available());
  String helloBuffer = "";
  // Check for HELLO packet
  while (Serial.available()) {
    char nextByte = Serial.read();
    helloBuffer += nextByte;
    if (helloBuffer.length() == 20) {
      // We have received one complete packet, stop reading BLE data
      break;
    }
  }
  
  // Send SYN packet

  // Check for SYN+ACK packet
}
