#include "packet.hpp"

HandshakeStatus handshakeStatus = STAT_NONE;
bool hasHandshake = false;
uint16_t seqNum = 0;
unsigned long sentPacketTime = 0;
CircularBuffer<char> recvBuff{};
CircularBuffer<BlePacket> sendBuffer{};

void sendDummyPacket() {
  BlePacket dummyPacket;
  // Dummy IMU data
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = seqNum;
  /* Generate 2 sets of 3 random floating point 
   * numbers to represent IMU gyroscope(x1, y1, z1) 
   * and accelerometer(x2, y2, z2) data */
  float x1 = random(0, 100);
  float y1 = random(0, 100);
  float z1 = random(0, 100);
  float x2 = random(0, 100);
  float y2 = random(0, 100);
  float z2 = random(0, 100);
  /* Pack the floating point numbers into the 
   * 16-byte data array */
  floatToData(dummyPacket.data, x1, y1, z1, x2, y2, z2);
  dummyPacket.crc = getCrcOf(dummyPacket);
  sendBuffer.push_back(dummyPacket);
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
  ackPacket.crc = getCrcOf(ackPacket);
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
  synPacket.crc = getCrcOf(synPacket);
  sendBuffer.push_back(synPacket);
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  }
  // Assert: hasHandshake == true
  if (Serial.available()) {
    BlePacket currPacket;
    readPacket(recvBuff, currPacket);
    if ((currPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
      hasHandshake = false;
      handshakeStatus = STAT_HELLO;
      return;
    } else if ((currPacket.metadata & LOWER_4BIT_MASK) != PacketType::ACK) {
      sendAckPacket(currPacket.seqNum);
    }
  }

  if (hasHandshake) {
    if (!sendBuffer.isFull()) {
      sendDummyPacket();
    }
    if (!sendBuffer.isEmpty()) {
      BlePacket firstPacket = sendBuffer.get(FIRST_ELEMENT);
      sendPacket(firstPacket);
      unsigned long sentTime = millis();
      BlePacket resultPacket;
      readPacket(recvBuff, resultPacket);
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

bool doHandshake() {
  unsigned long prevTime = millis();
  uint16_t prevSeqNum = seqNum;
  while (true) {
    if (handshakeStatus == STAT_NONE) {
      /* Either Beetle got powered off accidentally and reconnected, 
       * or Beetle is connecting to laptop for the first time */
      BlePacket mPacket;
      readPacket(recvBuff, mPacket);
      if ((mPacket.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        handshakeStatus = STAT_HELLO;
        prevSeqNum = mPacket.seqNum;
      }
    } else if (handshakeStatus == STAT_HELLO) {
      BlePacket ackPacket;
      createAckPacket(ackPacket, prevSeqNum);
      Serial.write((byte *) &ackPacket, sizeof(ackPacket));
      prevTime = millis();
      handshakeStatus = STAT_ACK;
    } else if (handshakeStatus == STAT_ACK) {
      BlePacket packet;
      readPacket(recvBuff, packet);
      if ((millis() - prevTime) > BLE_TIMEOUT) {
        // Timeout, retransmit ACK packet
        handshakeStatus = STAT_HELLO;
        prevTime = millis();
        continue;
      }
      // Check whether laptop sent SYN+ACK
      if ((packet.metadata & LOWER_4BIT_MASK) == PacketType::ACK) {
        handshakeStatus = STAT_SYN;
        return true;
      } else if ((packet.metadata & LOWER_4BIT_MASK) == PacketType::HELLO) {
        // HELLO packet again, restart handshake
        handshakeStatus = STAT_HELLO;
      }
    }
  }
  return false;
}


bool sendPacketFrom(CircularBuffer<BlePacket> &sendBuffer) {
  // Nothing can be done if the buffer is empty!
  if (sendBuffer.isEmpty()) {
    return false;
  }
  // There's 1 or more packets to send
  BlePacket packet = sendBuffer.pop_front();
  sendPacket(packet);
  if (shouldIncSeqNumFor(packet)) {
    seqNum += 1;
  }
  return true;
}
