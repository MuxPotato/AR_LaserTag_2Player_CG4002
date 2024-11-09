#include "vest.hpp"

/* Internal comms */
void handleGamePacket(const BlePacket &gamePacket);
void processIncomingPacket();
void retransmitLastPacket();

HandshakeStatus handshakeStatus = STAT_NONE;
// MyQueue<byte> recvBuffer{};
// Zero-initialise sentPacket
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

// Vest game state
bool isHit = false;
uint8_t playerHp = 100;
Adafruit_NeoPixel pixels(NUM_HP_LED, LED_STRIP_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  
  // Setup IR receiver-specific logic
  irReceiverSetup();

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
            // Drop duplicate SYN+ACK packets received from laptop so transmission logic 
            //   in loop() doesn't process leftover SYN+ACK packets from handshake
            clearSerialInputBuffer();
            // Break switch block since handshake process is complete
            //   This would also terminate the outer while() loop since handshake status is now STAT_SYN
            break;
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
  BlePacket vestPacket = {};
  byte packetData[PACKET_DATA_SIZE] = {};
  createVestPacketData(isHit, packetData);
  createPacket(vestPacket, PacketType::IR_RECV, senderSeqNum, packetData);
  return vestPacket;
}

bool getIsHitFrom(const BlePacket &gamePacket) {
  return gamePacket.data[0] == 1;
}

uint8_t getPlayerHpFrom(const BlePacket &gamePacket) {
  return gamePacket.data[1];
}

/* 
 * Update internal variables based on the new game state received
 */
void handleGamePacket(const BlePacket &gamePacket) {
  bool newIsHit = getIsHitFrom(gamePacket);
  uint8_t newPlayerHp = getPlayerHpFrom(gamePacket);
  if (newIsHit) {
    doGunshotHit();
  }
  if (newPlayerHp != INVALID_HP && newPlayerHp != playerHp) {
    updateHpLed(newPlayerHp);
    if (newPlayerHp > playerHp) {
      doRespawn();
    } else if (newPlayerHp < playerHp) {
      doDamage();
    }
  }
  isHit = newIsHit;
  playerHp = newPlayerHp;
}

bool hasHandshake() {
  return handshakeStatus == HandshakeStatus::STAT_SYN;
}

/**
 * Checks whether the connected sensors of this Beetle has raw data to send to laptop.
 * -Override this in device-specific Beetles to return true only when there's raw data to transmit(e.g. gun fire)
 */
bool hasRawData() {
  // Check whether vest was hit by gunshot
  if (getIsHitFromIr()) {
    // Gunshot detected
    isHit = true;
    // Indicate that there's sensor data to send to laptop
    return true;
  }
  // No gunshot detected, nothing to send to laptop
  return false;
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
      // Reset isHit state so next gunshot can be registered
      isHit = false;
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
        if (receiverSeqNum == packet.seqNum) {
          // Process the packet to handle specific game logic(e.g. updating Beetle's internal game state)
          handleGamePacket(packet);
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
        if (numInvalidPacketsReceived > 0) {
          numInvalidPacketsReceived = 0;
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

BlePacket sendVestPacket() {
  BlePacket vestPacket = {};
  byte packetData[PACKET_DATA_SIZE] = {};
  createVestPacketData(isHit, packetData);
  createPacket(vestPacket, PacketType::IR_RECV, senderSeqNum, packetData);
  sendPacket(vestPacket);
  return vestPacket;
}

/* IR Code */
void irReceiverSetup() {
  pinMode(BUZZER_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  IrReceiver.begin(IR_RECV_PIN);  // Start IR receiver on pin 5
  pixels.begin();
  pixels.setBrightness(60);
  updateHpLed(PLAYER_FULL_HP);
  TimerFreeTone(BUZZER_PIN, 400, 500);
}

bool getIsHitFromIr() {
  bool mIsHit = false;
  // Check if an IR signal is received
  if (IrReceiver.decode()) {  
    // Only detect signals from our own IR address and command
    if (IrReceiver.decodedIRData.protocol == NEC && 
        IrReceiver.decodedIRData.address == GET_OUR_IR_ADDRESS() &&
        IrReceiver.decodedIRData.command == IR_COMMAND) {
      // Turn on the LED if address matches
      digitalWrite(LED_PIN, HIGH);  
      mIsHit = true;
    }
    // Clear the IR receiver buffer to receive the next IR signal
    IrReceiver.resume();  
  }
  return mIsHit;
}

void doDamage() {
  // TODO: Implement visualisation/feedback when actions are triggered
  TimerFreeTone(BUZZER_PIN, GUNSHOT_HIT_BUZZER_FREQ, 200);
}

void doGunshotHit() {
  // TODO: Implement visualisation/feedback when vest is shot
  TimerFreeTone(BUZZER_PIN, GUNSHOT_HIT_BUZZER_FREQ, 200);
}

void doRespawn() {
  // TODO: Implement visualisation/feedback when player respawns
}

void updateHpLed(uint8_t givenPlayerHp) {
  switch (givenPlayerHp) {
    case 100:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 10);
      break;
    case 95:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(9,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 9);
      break;
    case 90:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 9);
      break;
    case 85:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(8,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 8);
      break;
    case 80:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 8);
      break;
    case 75:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(7,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 7);
      break;
    case 70:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 7);
      break;
    case 65:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(6,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 6);
      break;
    case 60:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 6);
      break;
    case 55:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(5,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 5);
      break;
    case 50:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 5);
      break;
    case 45:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(4,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 4);
      break;
    case 40:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 4);
      break;
    case 35:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(3,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 3);
      break;
    case 30:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 3);
      break;
    case 25:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(2,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 2);
      break;
    case 20:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 2);
      break;
    case 15:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(1,pixels.Color(255,0,0));
      pixels.fill(pixels.Color(0, 255, 0), 0, 1);
      break;
    case 10:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.fill(pixels.Color(0, 255, 0), 0, 1);
      break;
    case 5:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.setPixelColor(0,pixels.Color(255,0,0));
      break;
    case 0:
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      break;
  }
  pixels.show();
}
