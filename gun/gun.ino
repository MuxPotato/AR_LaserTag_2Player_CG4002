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
MyQueue<byte> recvBuffer{};
// Zero-initialise lastSentPacket
BlePacket lastSentPacket = {};
unsigned long lastSentPacketTime = 0;
uint16_t receiverSeqNum = INITIAL_SEQ_NUM;
uint16_t senderSeqNum = INITIAL_SEQ_NUM;
bool isWaitingForAck = false;
uint8_t numRetries = 0;
uint8_t numInvalidPacketsReceived = 0;

/* IR Transmitter */
/* Gun state */
int bulletCount = 6;
unsigned long lastGunfireTime = 0;
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
    isFired = fireGun();
    if (!isWaitingForAck) {
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
  uint16_t seqNumToSyn = senderSeqNum;
  if (isWaitingForAck && isPacketValid(lastSentPacket)) {
    seqNumToSyn = lastSentPacket.seqNum;
  }
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) (seqNumToSyn >> BITS_PER_BYTE);
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, packetData);
}

/* Implement this function in actual Beetles(e.g. process game state packet) */
void handleGamePacket(const BlePacket &gamePacket) {
  // TODO: Implement processing a given gamePacket
  bulletCount = gamePacket.data[0];
  if (bulletCount == 0) {
    reload();
    bulletCount = GUN_MAGAZINE_SIZE;
    visualiseBulletCount();
  }
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
      createNackPacket(nackPacket, receiverSeqNum);
      sendPacket(nackPacket);
  } // switch (receivedPacketType)
}

void processIncomingPacket() {
  // Read incoming bytes into receive buffer
  readIntoRecvBuffer(recvBuffer);
  if (recvBuffer.size() >= PACKET_SIZE) {
    // Complete 20-byte packet received, read 20 bytes from receive buffer as packet
    BlePacket receivedPacket = readPacketFrom(recvBuffer);
    if (!isPacketValid(receivedPacket)) {
      numInvalidPacketsReceived += 1;
      if (numInvalidPacketsReceived == MAX_INVALID_PACKETS_RECEIVED) {
        recvBuffer.clear();
        while (Serial.available() > 0) {
          Serial.read();
        }
        delay(TRANSMIT_DELAY);
        numInvalidPacketsReceived = 0;
        return;
      }
      BlePacket nackPacket;
      createNackPacket(nackPacket, receiverSeqNum);
      // Received invalid packet, request retransmit with NACK
      sendPacket(nackPacket);
    } else {
      processGivenPacket(receivedPacket);
    }
  } // if (recvBuffer.size() >= PACKET_SIZE)
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
    // Update sent time and wait for ACK again
    lastSentPacketTime = millis();
  } else {
    isWaitingForAck = false;
  }
}

BlePacket sendDummyPacket() {
  BlePacket dummyPacket;
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = senderSeqNum;
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

void getPacketDataFor(bool mIsFired, byte packetData[PACKET_DATA_SIZE]) {
  packetData[0] = mIsFired ? 1 : 0;
}

BlePacket sendGunPacket(bool mIsFired) {
  BlePacket gunPacket = {};
  byte packetData[PACKET_DATA_SIZE] = {};
  getPacketDataFor(mIsFired, packetData);
  createPacket(gunPacket, PacketType::P1_IR_TRANS, senderSeqNum, packetData);
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
bool fireGun() {
  unsigned long currentTime = millis();
  if (currentTime - lastGunfireTime > ACTION_INTERVAL) {
    digitalWrite(LED_PIN, HIGH);
    IrSender.sendNEC(IR_ADDRESS, IR_COMMAND, 0);  // the address 0x0102 with the command 0x34 is sent
    bulletCount--;
    visualiseBulletCount();
    tone(BUZZER_PIN, BUZZER_FREQ, BUZZER_DURATION);
    lastGunfireTime = currentTime;
    return true;
  }
  return false;
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
