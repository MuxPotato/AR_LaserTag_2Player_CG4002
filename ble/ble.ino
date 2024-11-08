#include "packet.hpp"

#define ACCEL_UPPER_BOUND 32768
#define GYRO_UPPER_BOUND 32750

void processIncomingPacket();
void retransmitLastPacket();

HandshakeStatus handshakeStatus = STAT_NONE;
// MyQueue<byte> recvBuffer{};
// Zero-initialise lastSentPacket
BlePacket lastSentPacket = {};
unsigned long lastSentPacketTime = 0;
uint16_t receiverSeqNum = INITIAL_SEQ_NUM;
uint16_t senderSeqNum = INITIAL_SEQ_NUM;
bool isWaitingForAck = false;
uint8_t numRetries = 0;
uint8_t numInvalidPacketsReceived = 0;
// Used to maintain (RETRANSMIT_DELAY) ms period of retransmissions
unsigned long lastRetransmitTime = 0;
unsigned long lastReadPacketTime = 0;

void setup() {
  Serial.begin(BAUDRATE);

  // Set up internal comms 
  setupBle();
}

void loop() {
  if (!hasHandshake()) {
    handshakeStatus = doHandshake();
  }
  unsigned long currentTime = millis();
  // Retransmit last sent packet on timeout
  if (isWaitingForAck && (currentTime - lastRetransmitTime) >= RETRANSMIT_DELAY
      && (currentTime - lastSentPacketTime) >= BLE_TIMEOUT) { 
    // Maintain at least RETRANSMIT_DELAY millisecs in between consecutive retransmits
    if (numRetries < MAX_RETRANSMITS) {
      // Retransmit only if numRetries less than max limit
      retransmitLastPacket();
      numRetries += 1;
    } else {
      /* // Max retries reached, stop retransmitting
      isWaitingForAck = false;
      lastSentPacket.metadata = PLACEHOLDER_METADATA; */

      // Clear serial input/output buffers to restart transmission from clean state
      clearSerialInputBuffer();
      Serial.flush();
      // Laptop might have disconnected, re-enter handshake
      handshakeStatus = STAT_NONE;
      numRetries = 0;
    }
  } else if (!isWaitingForAck && (currentTime - lastSentPacketTime) >= TRANSMIT_DELAY
      && hasRawData()) { // Send raw data packets(if any)
    // Only send new packet if previous packet has been ACK-ed and there's new sensor data to send
    //   but maintain TRANSMIT_DELAY millisecs in between sensor data packet transmissions
    // Read sensor data and generate a BlePacket encapsulating that data
    BlePacket mRawDataPacket = createRawDataPacket();
    // Send updated sensor data to laptop
    sendPacket(mRawDataPacket);
    // Update last sent packet to latest sensor data packet
    lastSentPacket = mRawDataPacket;
    // Update last packet sent time to track timeout
    lastSentPacketTime = millis();
    isWaitingForAck = true;
  } else if (!isWaitingForAck && (currentTime - lastSentPacketTime) >= KEEP_ALIVE_INTERVAL) {
    // Keep alive interval has passed since the last sensor/keep alive packet transmission but no sensor data is available to transmit
    // -> Send keep alive packet periodically when no sensor packet is transmitted so laptop knows Beetle is responding
    BlePacket keepAlivePacket = createKeepAlivePacket(senderSeqNum);
    sendPacket(keepAlivePacket);
    // Update lastSentPacket to allow keep alive packet to be retransmitted
    lastSentPacket = keepAlivePacket;
    // Update lastSentPacketTime to support retransmit on timeout and regular keep alive packets
    lastSentPacketTime = millis();
    // Require acknowledgement for keep alive packet
    isWaitingForAck = true;
  } else if ((currentTime - lastReadPacketTime) >= READ_PACKET_DELAY
      && Serial.available() >= PACKET_SIZE) { // Handle incoming packets
    // Received some bytes from laptop, process them wwhile maintaining at least READ_PACKET_DELAY
    //   in between reading of 2 consecutive packets 
    processIncomingPacket();
  }
}

/* Begin 'More important functions' section */
HandshakeStatus doHandshake() {
  unsigned long mLastPacketSentTime = millis();
  BlePacket mLastSentPacket;
  byte mSeqNum = INITIAL_SEQ_NUM;
  bool mIsWaitingForAck = false;
  while (handshakeStatus != STAT_SYN) {
    // No packet sent yet or not yet timed out or last packet sent is invalid
    switch (handshakeStatus) {
      case HandshakeStatus::STAT_NONE:
        {
          if (Serial.available() < PACKET_SIZE) {
            // Skip this iteration since we haven't received a full 20-byte packet
            continue;
          }
          // TODO: Add read packet delay like in main loop()
          // At least 1 20-byte packet in serial input buffer, read it
          BlePacket receivedPacket = readPacket();
          if (!isPacketValid(receivedPacket) || receivedPacket.seqNum != mSeqNum) {
            // TODO: Add retransmit delay like in main loop()
            BlePacket nackPacket;
            createNackPacket(nackPacket, mSeqNum, "Invalid/seqNum");
            sendPacket(nackPacket);
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO) {
            handshakeStatus = STAT_HELLO;
          }
          break;
        }
      case HandshakeStatus::STAT_HELLO:
        {
          unsigned long mTransmitPeriod = millis() - mLastPacketSentTime;
          if (mTransmitPeriod < TRANSMIT_DELAY) {
            // Maintain at least (TRANSMIT_DELAY) ms delay between transmissions to avoid overwhelming the Beetle
            delay(TRANSMIT_DELAY - mTransmitPeriod);
          }
          BlePacket ackPacket;
          createHandshakeAckPacket(ackPacket, mSeqNum);  
          sendPacket(ackPacket);
          mLastSentPacket = ackPacket;
          mLastPacketSentTime = millis();
          mSeqNum += 1;
          handshakeStatus = HandshakeStatus::STAT_ACK;
          mIsWaitingForAck = true;
          break;
        }
      case HandshakeStatus::STAT_ACK:
        {
          unsigned long mCurrentTime = millis();
          if (mIsWaitingForAck && (mCurrentTime - mLastPacketSentTime) >= BLE_TIMEOUT) {
            handshakeStatus = STAT_HELLO;
            mSeqNum = INITIAL_SEQ_NUM;
            // TODO: Consider if there's a need to clear serial input buffer here(after retransmitting)
            continue;
          }
          if (Serial.available() < PACKET_SIZE) {
            // Skip this iteration since we haven't received a full 20-byte packet
            continue;
          }
          // TODO: Add read packet delay like in main loop()
          BlePacket receivedPacket = readPacket();
          if (!isPacketValid(receivedPacket)) {
            // TODO: Add retransmit delay like in main loop()
            BlePacket nackPacket;
            createNackPacket(nackPacket, mSeqNum, "Corrupted");
            sendPacket(nackPacket);
          } else if (getPacketTypeOf(receivedPacket) == PacketType::ACK) {
            if (receivedPacket.seqNum > mSeqNum) {
              // TODO: Add retransmit delay like in main loop()
              BlePacket nackPacket;
              // Use existing seqNum for NACK packet to indicate current packet is not received
              createNackPacket(nackPacket, mSeqNum, "Over seqNum");
              sendPacket(nackPacket);
              continue;
            }
            if (receivedPacket.seqNum < mSeqNum) {
              // Likely a delayed ACK packet, drop it
              continue;
            }
            // TODO: Handle seq num update if laptop seq num != beetle seq num
            handshakeStatus = HandshakeStatus::STAT_SYN;
            mSeqNum += 1;
            mIsWaitingForAck = false;
            // Return from doHandshake() since handshake process is complete
            return HandshakeStatus::STAT_SYN;
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO &&
              (mCurrentTime - mLastPacketSentTime) >= BLE_TIMEOUT) {
            // Return to HELLO state only if we sent ACK a sufficiently long time ago(handshake has restarted or timeout occurred)
            handshakeStatus = STAT_HELLO;
            mSeqNum = INITIAL_SEQ_NUM;
            // Drop the HELLO packet if we just sent an ACK to avoid cycling between HELLO and ACK states
            //   This should clear the Serial input buffer of duplicate HELLO packets
          } else if (getPacketTypeOf(receivedPacket) == PacketType::NACK &&
              receivedPacket.seqNum == (mSeqNum - 1) && isPacketValid(mLastSentPacket)) {
            /* TODO: Consider if this block is ever entered, since we only accept NACK
               for our ACK to a HELLO, which means receivedPacket.seqNum = 0 and mSeqNum = 1 */
            // TODO: Add retransmit delay like in main loop()
            sendPacket(mLastSentPacket);
            mIsWaitingForAck = true;
          }
        }
    }
  }
  return handshakeStatus;
}

/* Old handshake function, obsolete(relies on my custom Queue as input buffer)
bool oldDoHandshake() {
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
            // BUG: This if block is still getting triggered after the laptop sends SYN+ACK
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
        // At this point, either timeout while waiting for incoming packet(no packet received at all), 
        //  or incoming packet was corrupted and timeout occurred before valid packet was received,
        //  or HELLO/NACK packet received before timeout occurred
        //
        if (!hasReceivedPacket) {
          // Timed out waiting for incoming packet, send ACK for HELLO again
          handshakeStatus = STAT_HELLO;
        }
    }
  } // while (handshakeStatus != STAT_SYN)
  return false;
}
*/

/**
 * Setup for the BLE internal communications-related logic and variables
 */
void setupBle() {
  // Clear the serial output buffer
  //   WARNING: This sends out all existing data in the output buffer over BLE though
  Serial.flush();

  // Clear the serial input buffer
  clearSerialInputBuffer();

  /* Initialise lastSentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  lastSentPacket.metadata = PLACEHOLDER_METADATA;
}
/* End 'More important functions' section */

/* Begin 'All other functions' section */
void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  uint16_t seqNumToSyn = senderSeqNum;
  if (isWaitingForAck && isPacketValid(lastSentPacket)) {
    seqNumToSyn = lastSentPacket.seqNum;
  }
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) (seqNumToSyn >> BITS_PER_BYTE);
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, packetData);
}

/**
 * Reads raw data from connected sensors and returns a BlePacket encapsulating the data
 * -Override this in device-specific Beetles to create device-specific data packets
 */
BlePacket createRawDataPacket() {
  BlePacket dummyPacket;
  byte dummyData[PACKET_DATA_SIZE] = {};
  int16_t x1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t y1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t z1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t x2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  int16_t y2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  int16_t z2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  getBytesFrom(dummyData, x1, y1, z1, x2, y2, z2);
  createPacket(dummyPacket, PacketType::IMU, senderSeqNum, dummyData);
  return dummyPacket;
}

/* Implement this function in actual Beetles(e.g. process game state packet) */
void handleGamePacket(const BlePacket &gamePacket) {
  // TODO: Implement processing a given gamePacket
}

bool hasHandshake() {
  return handshakeStatus == HandshakeStatus::STAT_SYN;
}

/**
 * Checks whether the connected sensors of this Beetle has raw data to send to laptop.
 * -Override this in device-specific Beetles to return true only when there's raw data to transmit(e.g. gun fire)
 */
bool hasRawData() {
  return true;
}

void processGivenPacket(const BlePacket &packet) {
  char givenPacketType = getPacketTypeOf(packet);
  switch (givenPacketType) {
    case PacketType::HELLO:
      handshakeStatus = STAT_HELLO;
      break;
    case PacketType::ACK:
      if (!isWaitingForAck) {
        // Not expecting an ACK, so this ACK is likely delayed and we drop it
        return;
      }
      // Have been waiting for an ACK and we received it
      if (packet.seqNum > senderSeqNum) {
        BlePacket nackPacket;
        createNackPacket(nackPacket, senderSeqNum, "seqNum too high");
        // Inform laptop about seq num mismatch by sending a NACK with our current seq num
        sendPacket(nackPacket);
        return;
      } else if (packet.seqNum < senderSeqNum) {
        // If packet.seqNum < senderSeqNum, it's (likely) a delayed ACK packet and we ignore it
        return;
      }
      // Valid ACK received, so stop waiting for incoming ACK
      isWaitingForAck = false;
      // Increment senderSeqNum upon every ACK
      senderSeqNum += 1;
      // Reset retry count on ACK
      numRetries = 0;
      break;
    case PacketType::NACK:
      if (!isWaitingForAck) {
        // Didn't send a packet, there's nothing to NACK
        // Likely a delayed packet so we just drop it
        return;
      }
      // Sent a packet but received a NACK, attempt to retransmit
      if (packet.seqNum == senderSeqNum) {
        if (isPacketValid(lastSentPacket) && getPacketTypeOf(lastSentPacket) != PacketType::NACK) {
          // Only retransmit if packet is valid
          sendPacket(lastSentPacket);
        }
        // No else{}: Don't retransmit a corrupted packet or another NACK packet
      }/*  else if (packet.seqNum > senderSeqNum) {
        // TODO: Enter 3-way handshake again to synchronise seq nums
      } */
      // If packet.seqNum < senderSeqNum, NACK packet is likely delayed and we drop it
      break;
    case GAME_STAT:
      {
        uint16_t seqNumToAck = receiverSeqNum;
        bool shouldHandlePacket = false;
        if (receiverSeqNum == packet.seqNum) {
          shouldHandlePacket = true;
          receiverSeqNum += 1;
        } else if (receiverSeqNum > packet.seqNum) {
          /* If receiverSeqNum > packet.seqNum, I incremented receiverSeqNum after sending ACK 
              but sender did not receive ACK and thus retransmitted packet
            */
          // ACK the packet but don't decrement my sequence number
          seqNumToAck = packet.seqNum;
          // Don't process the same packet again
        }
        // TODO: Consider what to do if receiverSeqNum < packet.seqNum?
        BlePacket ackPacket;
        createAckPacket(ackPacket, seqNumToAck);
        sendPacket(ackPacket);
        if (shouldHandlePacket) {
          // Process the packet to handle specific game logic(e.g. updating Beetle's internal game state)
          handleGamePacket(packet);
        }
        break;
      }
    case INVALID_PACKET_ID:
    default:
      // All other packet types are unsupported, inform sender that packet is rejected
      BlePacket nackPacket;
      createNackPacket(nackPacket, receiverSeqNum, "Invalid type");
      sendPacket(nackPacket);
  } // switch (receivedPacketType)
}

void processIncomingPacket() {
  if (Serial.available() < PACKET_DATA_SIZE) {
    // Don't read from serial input buffer unless 1 complete packet is received
    return;
  }
  // Complete 20-byte packet received, read 20 bytes from receive buffer as packet
  BlePacket receivedPacket = readPacket();
  if (!isPacketValid(receivedPacket)) {
    numInvalidPacketsReceived += 1;
    if (numInvalidPacketsReceived == MAX_INVALID_PACKETS_RECEIVED) {
      clearSerialInputBuffer();
      delay(BLE_TIMEOUT);
      numInvalidPacketsReceived = 0;
      return;
    }
    BlePacket nackPacket;
    createNackPacket(nackPacket, receiverSeqNum, "Corrupted");
    // Received invalid packet, request retransmit with NACK
    sendPacket(nackPacket);
  } else {
    if (numInvalidPacketsReceived > 0) {
      numInvalidPacketsReceived = 0;
    }
    processGivenPacket(receivedPacket);
  }
}

void processIncomingPacket(MyQueue<byte>& mRecvBuffer) {
  // Read incoming bytes into receive buffer
  readIntoRecvBuffer(mRecvBuffer);
  if (mRecvBuffer.size() >= PACKET_SIZE) {
    // Complete 20-byte packet received, read 20 bytes from receive buffer as packet
    BlePacket receivedPacket = readPacketFrom(mRecvBuffer);
    if (!isPacketValid(receivedPacket)) {
      numInvalidPacketsReceived += 1;
      if (numInvalidPacketsReceived == MAX_INVALID_PACKETS_RECEIVED) {
        mRecvBuffer.clear();
        while (Serial.available() > 0) {
          Serial.read();
        }
        delay(TRANSMIT_DELAY);
        numInvalidPacketsReceived = 0;
        return;
      }
      BlePacket nackPacket;
      createNackPacket(nackPacket, receiverSeqNum, "Corrupted");
      // Received invalid packet, request retransmit with NACK
      sendPacket(nackPacket);
    } else {
      if (numInvalidPacketsReceived > 0) {
        numInvalidPacketsReceived = 0;
      }
      processGivenPacket(receivedPacket);
    }
  } // if (mRecvBuffer.size() >= PACKET_SIZE)
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

void retransmitLastPacket() {
  if (isPacketValid(lastSentPacket)) {
    sendPacket(lastSentPacket);
    lastRetransmitTime = millis();
    // Update sent time and wait for ACK again
    lastSentPacketTime = millis();
  } else {
    isWaitingForAck = false;
  }
}

BlePacket sendDummyPacket() {
  BlePacket dummyPacket;
  byte dummyData[PACKET_DATA_SIZE] = {};
  int16_t x1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t y1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t z1 = random(-ACCEL_UPPER_BOUND, ACCEL_UPPER_BOUND);
  int16_t x2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  int16_t y2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  int16_t z2 = random(-GYRO_UPPER_BOUND, GYRO_UPPER_BOUND);
  getBytesFrom(dummyData, x1, y1, z1, x2, y2, z2);
  createPacket(dummyPacket, PacketType::IMU, senderSeqNum, dummyData);
  sendPacket(dummyPacket);
  return dummyPacket;
}
