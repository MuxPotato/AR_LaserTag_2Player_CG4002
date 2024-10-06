#include "packet.hpp"

HandshakeStatus handshakeStatus = STAT_NONE;
bool hasHandshake = false;
uint16_t seqNum = INITIAL_SEQ_NUM;
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
  createAckPacket(ackPacket, givenSeqNum);
  sendPacket(ackPacket);
}

void sendNackPacket(uint16_t givenSeqNum) {
  BlePacket nackPacket;
  createNackPacket(nackPacket, givenSeqNum);
  sendPacket(nackPacket);
}

void sendSynPacket(byte givenSeqNum) {
  BlePacket synPacket;
  createAckPacket(synPacket, givenSeqNum);
  synPacket.data[3] = (byte)'S';
  synPacket.data[4] = (byte)'Y';
  synPacket.data[5] = (byte)'N';
  sendBuffer.push_back(synPacket);
}

void setup() {
  Serial.begin(115200);
}

void loop() {
  if (!hasHandshake) {
    while (!doHandshake());
    hasHandshake = true;
  }
  // Assert: hasHandshake == true
  if (Serial.available() > 0) {
    BlePacket currPacket;
    // Block until 1 complete 20-byte packet is received and read into currPacket
    readPacket(recvBuff, currPacket);
    if (getPacketTypeOf(currPacket) == PacketType::HELLO) {
      hasHandshake = false;
      handshakeStatus = STAT_HELLO;
      return;
    } else if (getPacketTypeOf(currPacket) != PacketType::ACK) {
      sendAckPacket(currPacket.seqNum);
    }
  } else if (!sendBuffer.isFull()) {
    // If there's no packet received, send dummy packet
    sendDummyPacket();
  }
  // Send packet from sendBuffer if any exist
  if (!sendBuffer.isEmpty()) {
    BlePacket packetToSend = sendBuffer.get(FIRST_ELEMENT);
    sendPacket(packetToSend);
    sentPacketTime = millis();

    // Only handle HELLO and ACK here, leave the others to the earlier main packet parsing code block
    if (getPacketTypeOf(packetToSend) != PacketType::ACK) {
      // Read response packet from laptop
      BlePacket resultPacket;
      // Block until complete packet received
      readPacket(recvBuff, resultPacket);
      unsigned long recvTime = millis();
      // Ideally we should handle this in the main packet parsing code block, but for quick response we duplicate the logic here too
      if (getPacketTypeOf(resultPacket) == PacketType::HELLO) {
        hasHandshake = false;
        handshakeStatus = STAT_HELLO;
        return;
      }
      if (getPacketTypeOf(resultPacket) == PacketType::ACK &&
        resultPacket.seqNum == packetToSend.seqNum &&
        (recvTime - sentPacketTime) < BLE_TIMEOUT) {
        // Packet received by laptop, remove from sendBuffer
        sendBuffer.pop_front();
        seqNum += 1;
      } /* else if (getPacketTypeOf(resultPacket) != PacketType::ACK) {
        // TODO: Handle actual data from laptop that is not HELLO or ACK
        // BUG: Currently when Beetle sends IMU packet and waits for ACK but instead gets DUMMY packet from laptop, Beetle ACKs DUMMY and ends loop() iteration but doesn't wait for laptop to ACK
        // BUG: This block duplicates with the Serial.available() if block earlier in loop(), think of how to avoid duplicate incoming packet parsing/handling
        sendNackPacket(resultPacket.seqNum);
      } */
    } else {
      // Don't read response from laptop if Beetle just sent an ACK to a laptop's data packet
      // But still remove the packet from buffer
      sendBuffer.pop_front();
    }
  }
}

bool doHandshake() {
  unsigned long mSentTime = millis();
  while (true) {
    if (handshakeStatus == STAT_NONE) {
      /* Either Beetle got powered off accidentally and reconnected, 
       * or Beetle is connecting to laptop for the first time */
      BlePacket mPacket;
      readPacket(recvBuff, mPacket);
      if (getPacketTypeOf(mPacket) == PacketType::HELLO) {
        handshakeStatus = STAT_HELLO;
      }
    } else if (handshakeStatus == STAT_HELLO) {
      BlePacket ackPacket;
      createAckPacket(ackPacket, seqNum);
      sendPacket(ackPacket);
      mSentTime = millis();
      handshakeStatus = STAT_ACK;
    } else if (handshakeStatus == STAT_ACK) {
      BlePacket packet;
      readPacket(recvBuff, packet);
      if ((millis() - mSentTime) > BLE_TIMEOUT) {
        // Timeout, retransmit ACK packet
        handshakeStatus = STAT_HELLO;
        mSentTime = millis();
        continue;
      }
      // Check whether laptop sent SYN+ACK
      if (getPacketTypeOf(packet) == PacketType::ACK) {
        uint16_t laptopSeqNum = INITIAL_SEQ_NUM;
        if (laptopSeqNum < seqNum) {
          // TODO: Verify whether this is sound, will we 'forget' any lost packets?
          seqNum = laptopSeqNum;
        }
        // If seqNum < laptopSeqNum, we assume that laptop will update its internal seqNum count
        handshakeStatus = STAT_SYN;
        // Handshake is now complete
        return true;
      } else if (getPacketTypeOf(packet) == PacketType::HELLO) {
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
