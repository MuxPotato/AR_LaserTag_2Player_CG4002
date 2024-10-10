#include "packet.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

enum SenderState {
  IDLE,
  WAITING_FOR_ACK,
};

bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
MyQueue<byte> recvBuffer{};
// Zero-initialise lastSentPacket
BlePacket lastSentPacket = {};
unsigned long lastSentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;
bool shouldResendAfterHandshake = false;
SenderState senderState = IDLE;
bool isWaitingForAck = false;
bool hasReceivedAck = false;
uint8_t numRetries = 0;

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise lastSentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  lastSentPacket.metadata = PLACEHOLDER_METADATA;
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  }
  if (Serial.available() > 0) {
    readIntoRecvBuffer(recvBuffer);
    if (recvBuffer.size() >= PACKET_SIZE) {
      BlePacket receivedPacket = readPacketFrom(recvBuffer);
      if (!isPacketValid(receivedPacket)) {
        BlePacket nackPacket;
        createNackPacket(nackPacket, seqNum);
        sendPacket(nackPacket);
        // TODO: Consider if we want to update lastSentPacket so that even corrupted NACK packets are retransmitted to laptop?
        return;
      }
      // assert isPacketValid(newPacket) = true
      char receivedPacketType = getPacketTypeOf(receivedPacket);
      switch (receivedPacketType) {
        case PacketType::HELLO:
          hasHandshake = false;
          handshakeStatus = STAT_HELLO;
          break;
        case PacketType::ACK:
          // TODO: Plan how to handle retransmission
          break;
        case PacketType::NACK:
          // Update packet CRC just in case it got corrupted like it sometimes happens on the Beetle
          fixPacketCrc(lastSentPacket);
          // Only retransmit if packet is valid
          if (isPacketValid(lastSentPacket) && getPacketTypeOf(lastSentPacket) != PacketType::NACK) {
            sendPacket(lastSentPacket);
          }
          break;
        case INVALID_PACKET_ID:
          BlePacket nackPacket;
          createNackPacket(nackPacket, seqNum);
          sendPacket(nackPacket);
          break;
        default:
          BlePacket ackPacket;
          createAckPacket(ackPacket, seqNum);
          sendPacket(ackPacket);
          lastSentPacket = ackPacket;
      } // switch (receivedPacketType)
    } // if (recvBuffer.size() >= PACKET_SIZE)
  } else {
    // TODO: Send sensor data
    if (shouldResendAfterHandshake && isPacketValid(lastSentPacket)) {
      sendPacket(lastSentPacket);
      if (getPacketTypeOf(lastSentPacket) == PacketType::NACK) {
        // Don't wait for ACK when we retransmit a NACK
        return;
      }
    } else {
      lastSentPacket = sendDummyPacket();
    }
    lastSentPacketTime = millis();
    bool mHasAck = false;
    while (!mHasAck) {
      if ((millis() - lastSentPacketTime) < BLE_TIMEOUT) {
        // Read incoming bytes
        readIntoRecvBuffer(recvBuffer);
        if (recvBuffer.size() >= PACKET_SIZE) {
          // Read incoming bytes as packet
          BlePacket receivedPacket = readPacketFrom(recvBuffer);
          if (!isPacketValid(receivedPacket)) {
            BlePacket nackPacket;
            createNackPacket(nackPacket, seqNum);
            // Received invalid packet, request retransmit with NACK
            sendPacket(nackPacket);
          } else {
            char receivedPacketType = getPacketTypeOf(receivedPacket);
            if (receivedPacketType == PacketType::ACK) {
              if (receivedPacket.seqNum > seqNum) {
                BlePacket nackPacket;
                createNackPacket(nackPacket, seqNum);
                // Received invalid packet, request retransmit with NACK
                sendPacket(nackPacket);
                continue;
              }
              // If receivedPacket.seqNum < seqNum, it's (likely) a delayed ACK packet and we ignore it
              // ACK received, so stop waiting for incoming ACK
              mHasAck = true;
              // Increment seqNum upon every ACK
              seqNum += 1;
              if (shouldResendAfterHandshake) {
                // Interrupted packet has been resent and ACK, stop trying to resend anymore
                shouldResendAfterHandshake = false;
              }
            } else if (receivedPacketType == PacketType::NACK && receivedPacket.seqNum == seqNum) {
              // Update packet CRC just in case it got corrupted like it sometimes happens on the Beetle
              fixPacketCrc(lastSentPacket);
              // Only retransmit if packet is valid
              if (isPacketValid(lastSentPacket)) {
                // Received NACK, retransmit now
                sendPacket(lastSentPacket);
              }
            } else if (receivedPacketType == PacketType::HELLO) {
              shouldResendAfterHandshake = true;
              hasHandshake = false;
              handshakeStatus = STAT_HELLO;
              // Break while loop and perform doHandshake() again
              break;
            }
          }
        } // if (recvBuffer.size() >= PACKET_SIZE)
      } else {
        /* BUG: Somehow the Beetle gets stuck here trying to retransmit when the laptop gets disconnected */
        // Packet has timed out, retransmit
        sendPacket(lastSentPacket);
        // Update sent time and wait for ACK again
        lastSentPacketTime = millis();
      }
    } // while (!mHasAck)
  }
}

bool doHandshake() {
  unsigned long mPacketSentTime = millis();
  byte mSeqNum = INITIAL_SEQ_NUM;
  while (handshakeStatus != STAT_SYN) { 
    switch (handshakeStatus) {
      case STAT_NONE:
        while (Serial.available() <= 0 && recvBuffer.size() < PACKET_SIZE);
        readIntoRecvBuffer(recvBuffer);
        if (recvBuffer.size() >= PACKET_SIZE) {
          BlePacket receivedPacket = readPacketFrom(recvBuffer);
          if (!isPacketValid(receivedPacket) || receivedPacket.seqNum != mSeqNum) {
            BlePacket nackPacket;
            createNackPacket(nackPacket, mSeqNum);
            sendPacket(nackPacket);
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO) {
            handshakeStatus = STAT_HELLO;
          }
        }
        break;
      case STAT_HELLO:
        // Reset mSeqNum to initial value so it's not incremented too many times when we retransmit the ACK
        mSeqNum = INITIAL_SEQ_NUM;
        BlePacket ackPacket;
        createHandshakeAckPacket(ackPacket, mSeqNum);  
        sendPacket(ackPacket);
        mSeqNum += 1;
        mPacketSentTime = millis();
        handshakeStatus = STAT_ACK;
        break;
      case STAT_ACK:
        bool hasReceivedPacket = false;
        while ((millis() - mPacketSentTime) < BLE_TIMEOUT) {
          readIntoRecvBuffer(recvBuffer);
          if (recvBuffer.size() >= PACKET_SIZE) {
            /* BUG: This if block is still getting triggered after the laptop sends SYN+ACK */
            BlePacket receivedPacket = readPacketFrom(recvBuffer);
            if (!isPacketValid(receivedPacket)) {
              BlePacket nackPacket;
              // Use existing seqNum for NACK packet to indicate current packet is not received
              createNackPacket(nackPacket, mSeqNum);
              sendPacket(nackPacket);
              // Restart the loop and wait for SYN+ACK again
            } else if (getPacketTypeOf(receivedPacket) == PacketType::ACK) {
              if (receivedPacket.seqNum != mSeqNum) {
                BlePacket nackPacket;
                // Use existing seqNum for NACK packet to indicate current packet is not received
                createNackPacket(nackPacket, mSeqNum);
                sendPacket(nackPacket);
                continue;
              }
              // TODO: Handle seq num update if laptop seq num != beetle seq num
              handshakeStatus = STAT_SYN;
              mSeqNum += 1;
              // Return from doHandshake() since handshake process is complete
              return true;
            } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO ||
                (getPacketTypeOf(receivedPacket) == PacketType::NACK && receivedPacket.seqNum == mSeqNum)) {
              handshakeStatus = STAT_HELLO;
              hasReceivedPacket = true;
              // Break out of while() loop and go back to STAT_HELLO switch case(retransmit ACK packet)
              break;
            }
          }
        } // while ((millis() - mPacketSentTime) < BLE_TIMEOUT)
        /* At this point, either timeout while waiting for incoming packet(no packet received at all), 
          or incoming packet was corrupted and timeout occurred before valid packet was received,
          or HELLO/NACK packet received before timeout occurred
        */
        if (!hasReceivedPacket) {
          // Timed out waiting for incoming packet, send ACK for HELLO again
          handshakeStatus = STAT_HELLO;
        }
    }
  } // while (handshakeStatus != STAT_SYN)
  return false;
}

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  uint16_t seqNumToSyn = seqNum;
  if (shouldResendAfterHandshake && isPacketValid(lastSentPacket)) {
    seqNumToSyn = lastSentPacket.seqNum;
  }
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) seqNumToSyn >> BITS_PER_BYTE;
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, packetData);
}

int readIntoRecvBuffer(MyQueue<byte> &mRecvBuffer) {
  int numOfBytesRead = 0;
  while (Serial.available() > 0) {
    byte nextByte = (byte) Serial.read();
    if (isHeadByte(nextByte) || !mRecvBuffer.isEmpty()) {
      mRecvBuffer.push_back(nextByte);
      numOfBytesRead += 1;
    }
  }
  return numOfBytesRead;
}

BlePacket sendDummyPacket() {
  BlePacket dummyPacket;
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = seqNum;
  float x1 = random(0, 100);
  float y1 = random(0, 100);
  float z1 = random(0, 100);
  float x2 = random(0, 100);
  float y2 = random(0, 100);
  float z2 = random(0, 100);
  floatToData(dummyPacket.data, x1, y1, z1, x2, y2, z2);
  dummyPacket.crc = getCrcOf(dummyPacket);
  sendPacket(dummyPacket);
  return dummyPacket;
}

void sendPacket(BlePacket &packetToSend) {
  if ((millis() - lastSentPacketTime) < TRANSMIT_DELAY) {
    delay(TRANSMIT_DELAY);
  }
  Serial.write((byte *) &packetToSend, sizeof(packetToSend));
}
