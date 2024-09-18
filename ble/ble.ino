#include "packet.hpp"
#include "CRC8.h"

bool hasHandshake = false;
uint16_t seqNum = 0;
String receiveBuffer = "";

uint8_t getCrcOf(const BlePacket &packet) {
  CRC8 crcGen;
  crcGen.add((uint8_t) packet.metadata);
  crcGen.add((uint8_t) packet.seqNum);
  crcGen.add((uint8_t) packet.seqNum >> BITS_PER_BYTE);
  for (auto c : packet.data) {
    crcGen.add((uint8_t) c);
  }
  uint8_t crcValue = crcGen.calc();
  return crcValue;
}

void createPacket(BlePacket &packet, byte packetType, short givenSeqNum, byte data[16]) {
  packet.metadata = packetType;
  packet.seqNum = givenSeqNum;
  for (byte i = 0; i < 16; i += 1) {
    packet.data[i] = data[i];
  }
  // TODO: Implement proper checksum
  packet.checksum = getCrcOf(packet);
}

void sendDummyPacket() {
  BlePacket dummyPacket;
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = seqNum;
  dummyPacket.data[0] = (byte)'D';
  dummyPacket.data[1] = (byte)'U';
  dummyPacket.data[2] = (byte)'M';
  dummyPacket.data[3] = (byte)'M';
  dummyPacket.data[4] = (byte)'Y';
  //dummyPacket.checksum = 1;
  /* CRC8 crcGen;
  crcGen.add((uint8_t) dummyPacket.metadata);
  crcGen.add((uint8_t) dummyPacket.seqNum);
  for (auto c : dummyPacket.data) {
    crcGen.add((uint8_t) c);
  }
  dummyPacket.checksum = crcGen.calc(); */
  dummyPacket.checksum = getCrcOf(dummyPacket);
  Serial.write((byte *) &dummyPacket, sizeof(dummyPacket));
  seqNum += 1;
}

void sendAckPacket(uint16_t givenSeqNum) {
  BlePacket ackPacket;
  ackPacket.metadata = PacketType::ACK;
  ackPacket.seqNum = givenSeqNum;
  ackPacket.data[0] = (byte)'A';
  ackPacket.data[1] = (byte)'C';
  ackPacket.data[2] = (byte)'K';
  ackPacket.data[3] = 0;
  ackPacket.data[4] = 0;
  ackPacket.checksum = getCrcOf(ackPacket);
  Serial.write((byte *) &ackPacket, sizeof(ackPacket));
}

void sendSynPacket(byte givenSeqNum) {
  BlePacket synPacket;
  synPacket.metadata = PacketType::ACK;
  synPacket.seqNum = givenSeqNum;
  synPacket.data[0] = (byte)'A';
  synPacket.data[1] = (byte)'C';
  synPacket.data[2] = (byte)'K';
  synPacket.data[3] = (byte)'S';
  synPacket.data[4] = (byte)'Y';
  synPacket.data[5] = (byte)'N';
  synPacket.checksum = getCrcOf(synPacket);
  Serial.write((byte *) &synPacket, sizeof(synPacket));
  //seqNum += 1;
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
  if (!hasHandshake) {
    hasHandshake = doHandshake();
    return;
  }
  // Assert: hasHandshake == true
  if (Serial.available()) {
    char newByte = Serial.read();
    // Append new byte to receive buffer
    receiveBuffer += newByte;
    // ACK complete packet
    if (receiveBuffer.length() >= PACKET_SIZE) {
      String curr = receiveBuffer.substring(0, PACKET_SIZE);
      receiveBuffer.remove(0, PACKET_SIZE);
      /* if (curr == HELLO) {
        sendAckPacket(seqNum);
        delay(50);
      } */
      BlePacket currPacket;
      convertBytesToPacket(curr, currPacket);
      //if (curr.charAt(0) != PacketType::ACK) {
      if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
        sendAckPacket(seqNum);
        delay(50);
      }/*  else {
        sendSynPacket(seqNum);
      } */
    }
   
    /* int result = 0;
    // Clear the receiver buffer
    while (Serial.available()) {
      result += Serial.read();
    }
    sendAckPacket(seqNum); */
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
      sendAckPacket(seqNum);
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
        sendAckPacket(seqNum);
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
  if (inputs[0] == PacketType::HELLO) {
    sendAckPacket(seqNum);
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
  // return inputs[0] == PacketType::ACK;
  return true;
}
*/
// doHandshake() V2, doesn't work
/* bool doHandshake() {
  while (!Serial.available());
  //String helloBuffer = "";
  // Check for HELLO packet
  BlePacket currPacket;
  readPacket(currPacket);
  Serial.write((byte *) &currPacket, sizeof(currPacket));
  // TODO: Validate the packet
  if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::HELLO) {
    return false;
  }
  
  // Send SYN packet
  sendSynPacket(currPacket.seqNum);

  // Check for SYN+ACK packet
  readPacket(currPacket);
  // TODO: Validate the packet
  if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
    return false;
  }
  seqNum = currPacket.seqNum;
  return true;
} */

bool doHandshake() {
  HandshakeStatus status = STAT_NONE;
  uint16_t seqNumToUse = 0;
  unsigned long prevTime = millis();
  while (true) {
    if (!Serial.available()) {
      continue;
    }
    // Timeout waiting for HELLO packet
    if ((millis() - prevTime) > BLE_TIMEOUT) {
      break;
    }
    char newByte = Serial.read();
    // Append new byte to receive buffer
    receiveBuffer += newByte;
    // ACK complete packet
    if (receiveBuffer.length() >= PACKET_SIZE) {
      String curr = receiveBuffer.substring(0, PACKET_SIZE);
      receiveBuffer.remove(0, PACKET_SIZE);
      BlePacket currPacket;
      convertBytesToPacket(curr, currPacket);
      if ((currPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        status = STAT_HELLO;
        seqNumToUse = seqNum;
        sendAckPacket(seqNumToUse);
        prevTime = millis();
        status = STAT_ACK;
      } else if ((currPacket.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
        // Timeout waiting for SYN+ACK to the ACK packet
        if ((millis() - prevTime) > BLE_TIMEOUT) {
          break;
        }
        // Make sure that the SYN+ACK packet seq num matches our ACK packet one
        if (status == STAT_ACK && currPacket.seqNum == seqNumToUse) {
          status = STAT_SYN;
          return true;
        }
      }
    }
  } // while (true)
  return false;
}
