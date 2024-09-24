#include "packet.hpp"
#include "CRC8.h"

HandshakeStatus handshakeStatus = STAT_NONE;
bool hasHandshake = false;
uint16_t seqNum = 0;
int sentSeqNum = -1;
unsigned long sentPacketTime = 0;
//String receiveBuffer = "";
CircularBuffer<char> newRecvBuff{};
//char recvBuff[PACKET_SIZE];
CircularBuffer<BlePacket> sendBuffer{};

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

void floatToData(char data[16], float x1, float y1, float z1, float x2, float y2, float z2) {
  short x1s = (short) (x1 * 100);
  data[0] = (char) x1s;
  data[1] = (char) x1s >> BITS_PER_BYTE;
  short y1s = (short) (y1 * 100);
  data[2] = (char) y1s;
  data[3] = (char) y1s >> BITS_PER_BYTE;
  short z1s = (short) (z1 * 100);
  data[4] = (char) z1s;
  data[5] = (char) z1s >> BITS_PER_BYTE;
  short x2s = (short) (x2 * 100);
  data[6] = (char) x2s;
  data[7] = (char) x2s >> BITS_PER_BYTE;
  short y2s = (short) (y2 * 100);
  data[8] = (char) y2s;
  data[9] = (char) y2s >> BITS_PER_BYTE;
  short z2s = (short) (z2 * 100);
  data[10] = (char) z2s;
  data[11] = (char) z2s >> BITS_PER_BYTE;
  // Padding bytes
  data[12] = 0;
  data[13] = 0;
  data[14] = 0;
  data[15] = 0;
}

void sendDummyPacket() {
  BlePacket dummyPacket;
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = seqNum;
  /* dummyPacket.data[0] = (byte)'D';
  dummyPacket.data[1] = (byte)'U';
  dummyPacket.data[2] = (byte)'M';
  dummyPacket.data[3] = (byte)'M';
  dummyPacket.data[4] = (byte)'Y'; */
  float x1 = random(0, 100);
  float y1 = random(0, 100);
  float z1 = random(0, 100);
  float x2 = random(0, 100);
  float y2 = random(0, 100);
  float z2 = random(0, 100);
  floatToData(dummyPacket.data, x1, y1, z1, x2, y2, z2);
  //dummyPacket.checksum = 1;
  /* CRC8 crcGen;
  crcGen.add((uint8_t) dummyPacket.metadata);
  crcGen.add((uint8_t) dummyPacket.seqNum);
  for (auto c : dummyPacket.data) {
    crcGen.add((uint8_t) c);
  }
  dummyPacket.checksum = crcGen.calc(); */
  dummyPacket.checksum = getCrcOf(dummyPacket);
  //Serial.write((byte *) &dummyPacket, sizeof(dummyPacket));
  sendBuffer.push_back(dummyPacket);
  //seqNum += 1;
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
  //Serial.write((byte *) &ackPacket, sizeof(ackPacket));
  sendBuffer.push_back(ackPacket);
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
  //Serial.write((byte *) &synPacket, sizeof(synPacket));
  sendBuffer.push_back(synPacket);
  //seqNum += 1;
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
}

/* Works after resetting the AT settings and putting Beetle in GAP Peripheral mode again */
/* Basic unreliable communication without ACK, except for handshake
 */
void loop() {
  /* if (!hasHandshake) {
    hasHandshake = doHandshake();
    return;
  } */
  if (!hasHandshake) {
    hasHandshake = newHandshake();
  }
  // Assert: hasHandshake == true
  if (Serial.available()) {
    /*char newByte = Serial.read();
    // Append new byte to receive buffer
    receiveBuffer += newByte;
    // ACK complete packet
    if (receiveBuffer.length() >= PACKET_SIZE) {
      String curr = receiveBuffer.substring(0, PACKET_SIZE);
      receiveBuffer.remove(0, PACKET_SIZE);
      BlePacket currPacket;
      convertBytesToPacket(curr, currPacket);*/
      BlePacket currPacket = readPacket();
      if ((currPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        /* hasHandshake = false;
        handshakeStatus = STAT_HELLO;
        delay(25);
        // Bug: Somehow Beetle sends ACK but laptop doesn't receive it sometimes when reconnecting a disconnected Beetle. Doesn't happen in the first 3-way handshake after Beetle is powered on
        ackHelloPacket(seqNum); */
        hasHandshake = false;
        handshakeStatus = STAT_HELLO;
        //hasHandshake = newHandshake();
        return;
      } else if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
      //if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
        sendAckPacket(currPacket.seqNum);
        //delay(50);
      } /* else if ((currPacket.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
        // Bug: Not currently entering this if block when laptop reconnects Beetle, but the first 3-way handshake after Beetle is powered on works
        // Bug 2: Sometimes laptop receives the ACK from Beetle and sends SYN+ACK, but Beetle doesn't enter this loop/set hasHandshake = true. Other times, Beetle completes 3-way handshake after reconnection successfully
        uint16_t seqNumToUse = sentSeqNum == -1 ? 0 : sentSeqNum;
        parseSynAck(currPacket, sentSeqNum);
      } */
    /*}*/
   
  } /* else if (hasHandshake && !sendBuffer.isFull()) {
    sendDummyPacket();
    //delay(250);
  }
  if (hasHandshake && !sendBuffer.isEmpty()) {
    sendPacketFrom(sendBuffer);
    delay(50);
    // Fetch first packet
    BlePacket firstPacket = sendBuffer.get(0);

    // Send first packet without dequeue-ing
    Serial.write((byte *) &firstPacket, sizeof(firstPacket));
    unsigned long sentTime = millis();
    // Block until ACK comes. If ACK matches, dequeue
    BlePacket inPacket = readPacket();
    unsigned long recvTime = millis();
    if ((inPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
      hasHandshake = false;
      handshakeStatus = STAT_HELLO;
      return;
    }
    if ((inPacket.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
      uint16_t inSeqNum = inPacket.seqNum;
      if (inSeqNum == firstPacket.seqNum && (recvTime - sentTime) < BLE_TIMEOUT) {
        sendBuffer.pop_front();
      }
    }
  } */
  if (hasHandshake) {
    if (!sendBuffer.isFull()) {
      sendDummyPacket();
    }
    if (!sendBuffer.isEmpty()) {
      BlePacket firstPacket = sendBuffer.get(0);
      Serial.write((byte *) &firstPacket, sizeof(firstPacket));
      unsigned long sentTime = millis();
      BlePacket resultPacket = readPacket();
      if ((resultPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        hasHandshake = false;
        handshakeStatus = STAT_HELLO;
        return;
      }
      if ((resultPacket.metadata & LOWER_4BIT_MASK) == PacketType::ACK &&
        (millis() - sentTime) < BLE_TIMEOUT) {
        sendBuffer.pop_front();
      } else if ((resultPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
        sendAckPacket(resultPacket.seqNum);
      }
    }
  }
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

// V3: Working, but not adaptive. Cannot handle sudden disconnects
/* bool doHandshake() {
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
        //sendAckPacket(seqNumToUse);
        //sendPacketFrom(sendBuffer);
        BlePacket ackPacket = createAckPacket(seqNumToUse);
        Serial.write((byte *) &ackPacket, sizeof(ackPacket));
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
} */

BlePacket readPacket() {
  // V1: Completely destroys the data, bad input reading logic
  /* while (receiveBuffer.length() < PACKET_SIZE) {
    if (!Serial.available()) {
      continue;
    }
    char newByte = Serial.read();
    //if (isHeadByte(receiveBuffer.charAt(0)) || receiveBuffer.length() > 0) {
      // Append new byte to receive buffer
      receiveBuffer += newByte;
    //}
  }
  // receiveBuffer.length() >= PACKET_SIZE
  String curr = receiveBuffer.substring(0, PACKET_SIZE);
  receiveBuffer.remove(0, PACKET_SIZE);
  BlePacket currPacket;
  //convertBytesToPacket(curr, currPacket);
  currPacket.metadata = curr.charAt(0);
  currPacket.seqNum = curr.charAt(1) + (curr.charAt(2) << BITS_PER_BYTE);
  currPacket.checksum = curr.charAt(PACKET_SIZE - 1);
  return currPacket; */
  /* V2: Can perform disconnects and reconnects */
  unsigned long startTime = millis();
  while (newRecvBuff.size() < PACKET_SIZE) {
    if (!Serial.available()) {
      continue;
    }
    // TODO: Consider handling timeout
    if (millis() - startTime > BLE_TIMEOUT) {

    }
    char newByte = Serial.read();
    if (isHeadByte(newByte) || newRecvBuff.length() > 0) {
      // Append new byte to receive buffer
      newRecvBuff.push_back(newByte);
    }
  }
  // receiveBuffer.length() >= PACKET_SIZE
  BlePacket currPacket;
  convertBytesToPacket(newRecvBuff, currPacket);
  return currPacket;
  // Simplified data reading logic:
  /* int byteCount = 0;
  while (byteCount < PACKET_SIZE) {
    if (!Serial.available()) {
      continue;
    }
    char newByte = Serial.read();
    if (isHeadByte(recvBuff[0]) || byteCount > 0) {
      recvBuff[byteCount] = newByte;
      byteCount += 1;
    }
  }
  BlePacket newPacket;
  newPacket.metadata = recvBuff[0];
  newPacket.seqNum = recvBuff[1] + (recvBuff[2] << BITS_PER_BYTE);
  byte index = 3;
  for (auto &dataByte : newPacket.data) {
    dataByte = recvBuff[index];
    index += 1;
  }
  newPacket.checksum = recvBuff[PACKET_SIZE - 1];
  return newPacket; */
}

bool newHandshake() {
  unsigned long prevTime = millis();
  uint16_t prevSeqNum = seqNum;
  while (true) {
    if (handshakeStatus == STAT_NONE) {
      // Either Beetle got powered off accidentally and reconnected, or Beetle is connecting to laptop for the first time
      BlePacket mPacket = readPacket();
      if ((mPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        handshakeStatus = STAT_HELLO;
        prevSeqNum = mPacket.seqNum;
      }
    } else if (handshakeStatus == STAT_HELLO) {
      BlePacket ackPacket = createAckPacket(prevSeqNum);
      Serial.write((byte *) &ackPacket, sizeof(ackPacket));
      prevTime = millis();
      handshakeStatus = STAT_ACK;
      // TODO: Consider if the line below is the one triggering the BUG under SYN+ACK if condition below
      //prevSeqNum = seqNum;
    } else if (handshakeStatus == STAT_ACK) {
      if ((millis() - prevTime) > BLE_TIMEOUT) {
        // Timeout, retransmit ACK packet
        handshakeStatus = STAT_HELLO;
        //prevSeqNum = seqNum;
        /* BlePacket ackPacket = createAckPacket(prevSeqNum);
        Serial.write((byte *) &ackPacket, sizeof(ackPacket)); */
        prevTime = millis();
        continue;
      }
      BlePacket packet = readPacket();
      // Check whether laptop sent SYN+ACK
      if ((packet.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
        if ((millis() - prevTime) > BLE_TIMEOUT) {
          // Timeout, retransmit ACK packet
          handshakeStatus = STAT_HELLO;
          //prevSeqNum = packet.seqNum;
          continue;
        }
        // Make sure that the SYN+ACK packet seq num matches our ACK packet one
        /* BUG: Uncommenting the if condition below causes handshake to get stuck after laptop sends SYN+ACK, likely preventing hasHandshake from being set to true, so Beetle stops transmitting packets */
        // TODO: Delete commented code below
        /* BlePacket idPacket;
        char data[16];
        data[0] = (char) prevSeqNum;
        data[1] = prevSeqNum >> BITS_PER_BYTE;
        data[2] = 'v';
        data[3] = 's';
        data[4] = (char) packet.seqNum;
        data[5] = packet.seqNum >> BITS_PER_BYTE;
        createPacket(idPacket, PacketType::P2_IMU, prevSeqNum, data);
        Serial.write((byte *) &idPacket, sizeof(idPacket));
        packet.metadata = PacketType::P2_IMU; */
        //Serial.write((byte *) &packet, sizeof(packet));
        //if (packet.seqNum == prevSeqNum) {
          handshakeStatus = STAT_SYN;
          return true;
        //}
      } else if ((packet.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        // Duplicate HELLO packet, retransmit ACK
        handshakeStatus = STAT_HELLO;
        //prevSeqNum = seqNum;
      }
    }
  }
  return false;
}

BlePacket createAckPacket(uint16_t givenSeqNum) {
  BlePacket ackPacket;
  ackPacket.metadata = PacketType::ACK;
  ackPacket.seqNum = givenSeqNum;
  ackPacket.data[0] = (byte)'A';
  ackPacket.data[1] = (byte)'C';
  ackPacket.data[2] = (byte)'K';
  ackPacket.data[3] = 0;
  ackPacket.data[4] = 0;
  ackPacket.checksum = getCrcOf(ackPacket);
  return ackPacket;
}

bool sendPacketFrom(CircularBuffer<BlePacket> &sendBuffer) {
  // Nothing can be done if the buffer is empty!
  if (sendBuffer.isEmpty()) {
    return false;
  }
  // There's 1 or more packets to send
  BlePacket packet = sendBuffer.pop_front();
  Serial.write((byte *) &packet, sizeof(packet));
  if (shouldIncSeqNumFor(packet)) {
    // TODO: Fix any potential bugs and uncomment line below
    //sentSeqNum = seqNum;
    seqNum += 1;
  }
  return true;
}

void ackHelloPacket(uint16_t givenSeqNum) {
  BlePacket ackPacket = createAckPacket(givenSeqNum);
  Serial.write((byte *) &ackPacket, sizeof(ackPacket));
  sentPacketTime = millis();
  handshakeStatus = STAT_ACK;
  sentSeqNum = givenSeqNum;
}

bool parseSynAck(BlePacket &packet, uint16_t expectedSeqNum) {
  if ((packet.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
    // Make sure that the SYN+ACK packet seq num matches our ACK packet one
    if (handshakeStatus == STAT_ACK && packet.seqNum == expectedSeqNum) {
      // Timeout waiting for SYN+ACK to the ACK packet
      if ((millis() - sentPacketTime) > BLE_TIMEOUT) {
        // TODO: Switch to NACK instead
        ackHelloPacket(expectedSeqNum);
        return false;
      }
      handshakeStatus = STAT_SYN;
      // TODO: Consider if this should be set here or in the loop() function?
      hasHandshake = true;
      return true;
    }
  } else {
    return false;
  }
}

/*
 * Bug trackers
 * -No way to detect disconnect at the moment
 * -send buffer isn't cleared when Beetle is disconnected, once reconnected it continues sending data from the buffer before handshake
 * -Beetle continues queueing dummy packets even when it's disconnected so after reconnect, the seq num is much higher than at the point of disconnection
 * -Cannot perform reconnect at any time with the current doHandshake() implementation
 * -Related to above, Beetle continues sending dummy packets when reconnected before a new 3-way handshake is even done. hasHandshake() is not reset on disconnect
 * -doHandshake() shares the sendbuffer with the rest of the code which causes the ACK packet to be delayed
 */