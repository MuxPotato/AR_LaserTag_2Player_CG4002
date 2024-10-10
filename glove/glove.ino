#include "packet.hpp"
#include "imu.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

/* Internal comms */
bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
MyQueue<byte> recvBuffer{};
// Zero-initialise sentPacket
BlePacket sentPacket = {};
unsigned long sentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;
bool shouldResendAfterHandshake = false;

/* IMU variables */
float RateRoll, RatePitch, RateYaw;
float RateCalibrationRoll, RateCalibrationPitch, RateCalibrationYaw;
int RateCalibrationNumber;
float AccX, AccY, AccZ;
float AngleRoll, AnglePitch;
float LoopTimer;

/* Method declarations */
BlePacket sendImuPacket();
void setupImu();

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise sentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  sentPacket.metadata = PLACEHOLDER_METADATA;

  // Setup IMU
  delay(500);
  setupImu();
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
      sentPacket = sendImuPacket();
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

/* Internal comms */
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

BlePacket sendImuPacket() {
  gyro_signals();
  RateRoll -= RateCalibrationRoll;
  RatePitch -= RateCalibrationPitch;
  RateYaw -= RateCalibrationYaw;

  BlePacket imuPacket;
  byte imuData[PACKET_DATA_SIZE] = {};
  floatToData(imuData, AccX, AccY, AccZ, RatePitch, RateRoll, RateYaw);
  createPacket(imuPacket, PacketType::P1_IMU, seqNum, imuData);
  sendPacket(imuPacket);
  return imuPacket;
}

void sendPacket(BlePacket &packetToSend) {
  if ((millis() - sentPacketTime) < TRANSMIT_DELAY) {
    delay(TRANSMIT_DELAY);
  }
  Serial.write((byte *) &packetToSend, sizeof(packetToSend));
}

/* IMU */
void gyro_signals(void) {
  // Set low pass filter bandwidth to 10Hz
  // Consider 5Hz for filter bandwidth, given by value "6"
  Wire.beginTransmission(0x68); //default value of MPU register
  Wire.write(0x1A); //writing to the low pass filter register
  Wire.write(0x05); //value of "5" turns on 10Hz
  Wire.endTransmission();

  // Set accelerometer range to +-2g
  Wire.beginTransmission(0x68); 
  Wire.write(0x1C); // write to accelerometer configuration register
  Wire.write(0x0); // value of "0" gives +-2g
  Wire.endTransmission();

  // Prepare to get accelerometer readings from accelerometer register
  Wire.beginTransmission(0x68);
  Wire.write(0x3B); //register to access accelerometer readings
  Wire.endTransmission();

  Wire.requestFrom(0x68, 6); //request 6 bytes from the MPU (each measurement takes 2 bytes)
  int16_t AccXLSB = Wire.read() << 8 | Wire.read();
  int16_t AccYLSB = Wire.read() << 8 | Wire.read();
  int16_t AccZLSB = Wire.read() << 8 | Wire.read();

  // Set gyroscope range to +-250 degs
  Wire.beginTransmission(0x68);
  Wire.write(0x1B); //write to gyroscope configuration register
  Wire.write(0x0); //value of "0" gives +- 250 deg
  Wire.endTransmission();

  // Prepare to get gyroscope readings from gyroscope register
  Wire.beginTransmission(0x68);
  Wire.write(0x43); //register to access gyroscope readings
  Wire.endTransmission();

  Wire.requestFrom(0x68, 6);
  int16_t GyroX = Wire.read() << 8 | Wire.read();
  int16_t GyroY = Wire.read() << 8 | Wire.read();
  int16_t GyroZ = Wire.read() << 8 | Wire.read();

  //Convert the gyroscope and acclerometer readings to physical units 
  //Convert the LSB scale to physical units by dividing by 16384
  AccX = (float)AccXLSB / 16384;
  AccY = (float)AccYLSB / 16384;
  AccZ = (float)AccZLSB / 16384;

  //Convert the LSB scale to physical units by dividing by 131 
  RateRoll = (float)GyroX / 131; 
  RatePitch = (float)GyroY / 131;
  RateYaw = (float)GyroZ / 131;
}

void setupImu() {
  BlePacket infoPacket;
  byte infoData[PACKET_DATA_SIZE] = {};
  createDataFrom("CALIBRATING", infoData);
  createPacket(infoPacket, PacketType::GAME_STAT, INITIAL_SEQ_NUM, infoData);
  sendPacket(infoPacket);

  Wire.setClock(400000);
  
  Wire.begin();
  delay(250);
  
  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission();

  //Hold steady to calibrate IMU 
  for (RateCalibrationNumber = 0; RateCalibrationNumber < 2000; RateCalibrationNumber ++) {
    gyro_signals();
    RateCalibrationRoll += RateRoll;
    RateCalibrationPitch += RatePitch;
    RateCalibrationYaw += RateYaw;
    delay(1);
  }
  RateCalibrationRoll /= 2000;
  RateCalibrationPitch /= 2000;
  RateCalibrationYaw /= 2000;

  byte completeData[PACKET_DATA_SIZE] = {};
  createDataFrom("CALIBRATED", completeData);
  createPacket(infoPacket, PacketType::GAME_STAT, INITIAL_SEQ_NUM, completeData);
  sendPacket(infoPacket);
}
