#include "packet.hpp"
#include "vest.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

void processIncomingPacket();
void retransmitLastPacket();

bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
MyQueue<byte> recvBuffer{};
// Zero-initialise sentPacket
BlePacket lastSentPacket = {};
unsigned long lastSentPacketTime = 0;
uint16_t receiverSeqNum = INITIAL_SEQ_NUM;
uint16_t senderSeqNum = INITIAL_SEQ_NUM;
bool isWaitingForAck = false;
uint8_t numRetries = 0;
uint8_t numInvalidPacketsReceived = 0;

// Vest game state
bool isShot = false;
size_t health = 100;
Adafruit_NeoPixel pixels(PIXEL_COUNT, LED_STRIP_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise sentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  lastSentPacket.metadata = PLACEHOLDER_METADATA;
  // TODO: Uncomment line below
  irReceiverSetup();
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  }
  if (checkIrReceiver()) {
    // Gunshot detected
    isShot = true;
    if (!isWaitingForAck) {
      // Send out isShot state to game engine
      lastSentPacket = sendVestPacket();
      // Update last packet sent time to track timeout
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
      // Reset isShot state so next gunshot can be registered
      isShot = false;
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

void sendPacket(BlePacket &packetToSend) {
  if ((millis() - lastSentPacketTime) < TRANSMIT_DELAY) {
    delay(TRANSMIT_DELAY);
  }
  Serial.write((byte *) &packetToSend, sizeof(packetToSend));
}

void createVestPacketData(bool mIsShot, byte packetData[PACKET_DATA_SIZE]) {
  packetData[0] = mIsShot ? 1 : 0;
}

BlePacket sendVestPacket() {
  BlePacket vestPacket = {};
  byte packetData[PACKET_DATA_SIZE] = {};
  createVestPacketData(isShot, packetData);
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
  giveLife();
}

bool checkIrReceiver() {
  bool mIsShot = false;
  if (IrReceiver.decode()) {  // Check if an IR signal is received
    if (IrReceiver.decodedIRData.address == EXPECTED_IR_ADDRESS) {  // Compare with expected address
      digitalWrite(LED_PIN, HIGH);  // Turn on the LED if address matches
      mIsShot = true;
    }
    IrReceiver.resume();  // Clear the buffer for the next IR signal
  }
  return mIsShot;
}

void checkHealth() {
  if (IrReceiver.isIdle()) {
    switch (health) {
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
}

void giveLife() {
  health = 100;
  if (IrReceiver.isIdle()) {
    for (int i = 0; i <= 10; i++) {
      pixels.fill(pixels.Color(0, 255, 0), 0, i);
      pixels.show();
      TimerFreeTone(BUZZER_PIN, 400, 500);
      delay(500);
      pixels.fill(pixels.Color(0, 0, 0), 0, 10);
      pixels.show();
      delay(500);
    }
    pixels.fill(pixels.Color(0, 255, 0), 0, 10);
    pixels.show();
  }
}
