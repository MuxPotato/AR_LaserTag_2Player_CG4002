#include "packet.hpp"
#include "vest.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
MyQueue<byte> recvBuffer{};
// Zero-initialise sentPacket
BlePacket sentPacket = {};
unsigned long sentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;
bool shouldResendAfterHandshake = false;

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise sentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  sentPacket.metadata = PLACEHOLDER_METADATA;
  // TODO: Uncomment line below
  // irReceiverSetup();
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
        // TODO: Consider if we want to update sentPacket so that even corrupted NACK packets are retransmitted to laptop?
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
          fixPacketCrc(sentPacket);
          // Only retransmit if packet is valid
          if (isPacketValid(sentPacket) && getPacketTypeOf(sentPacket) != PacketType::NACK) {
            sendPacket(sentPacket);
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
          sentPacket = ackPacket;
      } // switch (receivedPacketType)
    } // if (recvBuffer.size() >= PACKET_SIZE)
  } else {
    // TODO: Send sensor data
    if (shouldResendAfterHandshake && isPacketValid(sentPacket)) {
      sendPacket(sentPacket);
      if (getPacketTypeOf(sentPacket) == PacketType::NACK) {
        // Don't wait for ACK when we retransmit a NACK
        return;
      }
    } else {
      /*
      bool hasDataToSend = checkIrReceiver();
      if (hasDataToSend) {
        sentPacket = sendIrRecvPacket();
      }
       */
      // TODO: Uncomment the above lines and delete line below
      sentPacket = sendDummyPacket();
    }
    sentPacketTime = millis();
    bool mHasAck = false;
    while (!mHasAck) {
      if ((millis() - sentPacketTime) < BLE_TIMEOUT) {
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
              fixPacketCrc(sentPacket);
              // Only retransmit if packet is valid
              if (isPacketValid(sentPacket)) {
                // Received NACK, retransmit now
                sendPacket(sentPacket);
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
        sendPacket(sentPacket);
        // Update sent time and wait for ACK again
        sentPacketTime = millis();
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
  if (shouldResendAfterHandshake && isPacketValid(sentPacket)) {
    seqNumToSyn = sentPacket.seqNum;
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
  BlePacket dummyPacket = {};
  dummyPacket.metadata = PacketType::P1_IR_RECV;
  dummyPacket.seqNum = seqNum;
  // Generate random value(either 0 or 1) to indicate isHit = false or true, respectively
  dummyPacket.data[0] = random(2);
  dummyPacket.crc = getCrcOf(dummyPacket);
  sendPacket(dummyPacket);
  return dummyPacket;
}

BlePacket sendIrRecvPacket() {
  BlePacket irRecvPacket = {};
  irRecvPacket.metadata = PacketType::P1_IR_RECV;
  irRecvPacket.seqNum = seqNum;
  // Set to '1' to indicate that isHit = true
  irRecvPacket.data[0] = 1;
  irRecvPacket.crc = getCrcOf(irRecvPacket);
  sendPacket(irRecvPacket);
  return irRecvPacket;
}

void sendPacket(BlePacket &packetToSend) {
  // TODO: Adjust TRANSMIT_DELAY in packet.hpp
  if ((millis() - sentPacketTime) < TRANSMIT_DELAY) {
    delay(TRANSMIT_DELAY);
  }
  Serial.write((byte *) &packetToSend, sizeof(packetToSend));
}

/* IR Code */
bool checkIrReceiver() {
  if (IrReceiver.decode()) {  // Check if an IR signal is received
    if (IrReceiver.decodedIRData.address == EXPECTED_IR_ADDRESS) {  // Compare with expected address
      digitalWrite(LED_PIN, HIGH);  // Turn on the LED if address matches
      return true;
    }
    IrReceiver.resume();  // Clear the buffer for the next IR signal
  }
}

void irReceiverSetup() {
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  IrReceiver.begin(IR_RECV_PIN);  // Start IR receiver on pin 5
}
