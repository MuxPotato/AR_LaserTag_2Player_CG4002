#include "gun.hpp"
#include "packet.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

/* Internal comms */
void processIncomingPacket();
void retransmitLastPacket();

bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
//MyQueue<byte> recvBuffer{};
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

/* IR Transmitter */
/* Gun state */
uint8_t bulletCount = 6;
bool isReloading = false;
bool isFiring = false;
bool isFired = false;

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise sentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  lastSentPacket.metadata = PLACEHOLDER_METADATA;
  // TODO: Uncomment line below
  gunSetup();
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  }
  if (getIsFired()) {
    isFired = true;
    if (!isWaitingForAck) {
      fireGun();
      // Only send new packet if previous packet has already been ACK-ed
      unsigned long transmitPeriod = millis() - lastSentPacketTime;
      if (transmitPeriod < TRANSMIT_DELAY) {
        // Maintain at least (TRANSMIT_DELAY) ms delay between transmissions to avoid overwhelming the Beetle
        delay(TRANSMIT_DELAY - transmitPeriod);
      }
      lastSentPacket = sendGunPacket(isFired);
      lastSentPacketTime = millis();
      isWaitingForAck = true;
    }
  } else if (isWaitingForAck && (millis() - lastSentPacketTime) > BLE_TIMEOUT) {
    //if (numRetries < MAX_RETRANSMITS) {
      retransmitLastPacket();
      /* numRetries += 1;
    } else {
      // Max retries reached, stop retransmitting
      isWaitingForAck = false;
      lastSentPacket.metadata = PLACEHOLDER_METADATA;
      numRetries = 0;
    } */
  }
  if (Serial.available() > 0) {
    // Received some bytes from laptop, process them
    processIncomingPacket();
  }
}

bool doHandshake() {
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
            createNackPacket(nackPacket, mSeqNum);
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
          if (mIsWaitingForAck && (millis() - mLastPacketSentTime) >= BLE_TIMEOUT && isPacketValid(mLastSentPacket)) {
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
          if (!isPacketValid(receivedPacket) || receivedPacket.seqNum != mSeqNum) {
            // TODO: Add retransmit delay like in main loop()
            BlePacket nackPacket;
            createNackPacket(nackPacket, mSeqNum);
            sendPacket(nackPacket);
          } else if (getPacketTypeOf(receivedPacket) == PacketType::ACK) {
            if (receivedPacket.seqNum > mSeqNum) {
              // TODO: Add retransmit delay like in main loop()
              BlePacket nackPacket;
              // Use existing seqNum for NACK packet to indicate current packet is not received
              createNackPacket(nackPacket, mSeqNum);
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
            return true;
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO) {
            handshakeStatus = STAT_HELLO;
            mSeqNum = INITIAL_SEQ_NUM;
          } else if (getPacketTypeOf(receivedPacket) == PacketType::NACK &&
              receivedPacket.seqNum == mSeqNum && isPacketValid(mLastSentPacket)) {
            /* TODO: Consider if this block is ever entered, since we only accept NACK
               for our ACK to a HELLO, which means receivedPacket.seqNum = 0 and mSeqNum = 1 */
            // TODO: Add retransmit delay like in main loop()
            sendPacket(mLastSentPacket);
            mIsWaitingForAck = true;
          }
        }
    }
  }
  return false;
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

uint8_t getBulletCountFrom(const BlePacket &gamePacket) {
  return gamePacket.data[0];
}

/*
 * Update internal variables based on the new game state received
 */
void handleGamePacket(const BlePacket &gamePacket) {
  uint8_t newBulletCount = getBulletCountFrom(gamePacket);
  if (bulletCount == 0 && newBulletCount > bulletCount) {
    reload();
  }
  bulletCount = GUN_MAGAZINE_SIZE;
  visualiseBulletCount();
}

void processGivenPacket(const BlePacket &packet) {
  char givenPacketType = getPacketTypeOf(packet);
  switch (givenPacketType) {
    case PacketType::HELLO:
      hasHandshake = false;
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
        createNackPacket(nackPacket, senderSeqNum);
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
      isFired = false;
      // numRetries = 0;
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
        if (numInvalidPacketsReceived > 0) {
          numInvalidPacketsReceived = 0;
        }
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
      createNackPacket(nackPacket, receiverSeqNum);
      sendPacket(nackPacket);
  } // switch (receivedPacketType)
}

void processIncomingPacket() {
  if (Serial.available() < PACKET_DATA_SIZE) {
    // Don't read from serial input buffer unless 1 complete packet is received
    return;
  }
  unsigned long readPacketPeriod = millis() - lastReadPacketTime;
  if (readPacketPeriod < READ_PACKET_DELAY) {
    delay(READ_PACKET_DELAY - readPacketPeriod);
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
    createNackPacket(nackPacket, receiverSeqNum);
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
    unsigned long retransmitPeriod = millis() - lastRetransmitTime;
    if (retransmitPeriod < RETRANSMIT_DELAY) {
      // Maintain at least (RETRANSMIT_DELAY) ms delay between retransmissions to avoid overwhelming the Beetle
      delay(RETRANSMIT_DELAY - retransmitPeriod);
    }
    sendPacket(lastSentPacket);
    lastRetransmitTime = millis();
    // Update sent time and wait for ACK again
    lastSentPacketTime = millis();
  } else {
    isWaitingForAck = false;
  }
}

void getPacketDataFor(bool mIsFired, byte packetData[PACKET_DATA_SIZE]) {
  packetData[0] = mIsFired ? 1 : 0;
}

BlePacket sendGunPacket(bool mIsFired) {
  BlePacket gunPacket = {};
  byte packetData[PACKET_DATA_SIZE] = {};
  getPacketDataFor(mIsFired, packetData);
  createPacket(gunPacket, PacketType::IR_TRANS, senderSeqNum, packetData);
  sendPacket(gunPacket);
  return gunPacket;
}

/* IR Transmitter */
void gunSetup() {
  pinMode(BUTTON_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  IrSender.begin(IR_TRN_PIN);
  pixels.begin();
  pixels.setBrightness(PIXEL_BRIGHTNESS);
  visualiseBulletCount();
}

// Checks bulletCount and then displays the corresponding number of LEDs
void visualiseBulletCount() {
  isReloading = true; 
  switch (bulletCount) {
    case 0:
      pixels.fill(pixels.Color(0, 0, 0), 0, 6);
      break;
    case 1:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
    case 2:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
    case 3:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
    case 4:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
    case 5:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
    case 6:
      pixels.fill(pixels.Color(255, 0, 0), 0, bulletCount);
      pixels.fill(pixels.Color(0, 0, 0), bulletCount, GUN_MAGAZINE_SIZE - bulletCount);
      break;
  }
  pixels.show();
  isReloading = false;
}

byte getButtonState() {
  byte newButtonState = (byte) digitalRead(BUTTON_PIN);
  return newButtonState;
}

bool getIsFired() {
  byte befButtonState = getButtonState();
  delay(BUTTON_DEBOUNCE_DELAY);
  byte aftButtonState = getButtonState();
  return befButtonState == LOW && aftButtonState == HIGH && !isReloading;
}

/*
 * Attempts to trigger a gun fire.
 * @returns boolean indicating whether or not gun is successfully fired
 */
void fireGun() {
  IrSender.sendNEC(IR_ADDRESS, IR_COMMAND, 0);  // the address 0x0102 with the command 0x34 is sent
  if (bulletCount > 0) {
    bulletCount -= 1;
  }
  visualiseBulletCount();
  tone(BUZZER_PIN, BUZZER_FREQ, BUZZER_DURATION);
}

void reload() {
  TimerFreeTone(BUZZER_PIN, RELOAD_BUZZER_FREQ, RELOAD_BUZZER_DURATION);
  pixels.fill(pixels.Color(255, 0, 0), 0, 6);
  pixels.show();
  pixels.fill(pixels.Color(0, 0, 0), 0, 6);
  pixels.show();
  TimerFreeTone(BUZZER_PIN, RELOAD_BUZZER_FREQ, RELOAD_BUZZER_DURATION);
  pixels.fill(pixels.Color(255, 0, 0), 0, 6);
  pixels.show();
  pixels.fill(pixels.Color(0, 0, 0), 0, 6);
  pixels.show();
  TimerFreeTone(BUZZER_PIN, RELOAD_BUZZER_FREQ, RELOAD_BUZZER_DURATION);
  pixels.fill(pixels.Color(255, 0, 0), 0, 6);
  pixels.show();
  pixels.fill(pixels.Color(0, 0, 0), 0, 6);
  pixels.show();
}
