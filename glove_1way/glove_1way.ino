#include "imu.hpp"
#include "packet.hpp"

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

/* Method declarations */
void processIncomingPacket();
void processGivenPacket(BlePacket &packet);
void retransmitLastPacket();
BlePacket sendImuPacket();
void setupImu();

/* Internal comms */
bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
MyQueue<byte> recvBuffer{};
// Zero-initialise lastSentPacket
BlePacket lastSentPacket = {};
unsigned long lastSentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;
bool isWaitingForAck = false;
bool hasReceivedAck = false;
uint8_t numRetries = 0;
uint8_t numInvalidPacketsReceived = 0;

/* IMU variables */
/*float RateCalibrationGyroX, RateCalibrationGyroY, RateCalibrationGyroZ;
float AccX, AccY, AccZ;
float RateRoll, RatePitch, RateYaw; */
// Accelerometer data in LSB per degree
int16_t AccX = 0;
int16_t AccY = 0;
int16_t AccZ = 0;
// Offset error value for accelerometer data
int16_t AccErrorX = 0;
int16_t AccErrorY = 0;
int16_t AccErrorZ = 0;
// Accelerometer data in LSB per degrees/s
int16_t GyroX = 0;
int16_t GyroY = 0;
int16_t GyroZ = 0;
// Offset error value for gyroscope data
int16_t GyroErrorX = 0;
int16_t GyroErrorY = 0;
int16_t GyroErrorZ = 0;

void setup() {
  Serial.begin(BAUDRATE);
  /* Initialise lastSentPacket with invalid metadata
    to ensure it's detected as corrupted if ever
    sent without assigning actual (valid) packet */
  lastSentPacket.metadata = PLACEHOLDER_METADATA;

  // Setup IMU
  delay(500);
  setupImu();
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  }
  if (isWaitingForAck && (millis() - lastSentPacketTime) > BLE_TIMEOUT) {
    retransmitLastPacket();
  }
  if (Serial.available() > 0) {
    // Received some bytes from laptop, process them
    processIncomingPacket();
  } else if (!isWaitingForAck) {
    // No packets received, send IMU packet
    BlePacket imuPacket = sendImuPacket();
    lastSentPacket = imuPacket;
    lastSentPacketTime = millis();
    isWaitingForAck = true;
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

void processGivenPacket(BlePacket &packet) {
  char packetType = getPacketTypeOf(packet);
  switch (packetType) {
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
      if (packet.seqNum > seqNum) {
        BlePacket nackPacket;
        createNackPacket(nackPacket, seqNum);
        // Inform laptop about seq num mismatch by sending a NACK with our current seq num
        sendPacket(nackPacket);
        return;
      } else if (packet.seqNum < seqNum) {
        // If packet.seqNum < seqNum, it's (likely) a delayed ACK packet and we ignore it
        return;
      }
      // Valid ACK received, so stop waiting for incoming ACK
      isWaitingForAck = false;
      // Increment seqNum upon every ACK
      seqNum += 1;
      break;
    case PacketType::NACK:
      if (!isWaitingForAck) {
        // Didn't send a packet, there's nothing to NACK
        // Likely a delayed packet so we just drop it
        return;
      }
      // Sent a packet but received a NACK, attempt to retransmit
      if (packet.seqNum == seqNum) {
        if (isPacketValid(lastSentPacket) && getPacketTypeOf(lastSentPacket) != PacketType::NACK) {
          // Only retransmit if packet is valid
          sendPacket(lastSentPacket);
        }
      }
      break;
    case INVALID_PACKET_ID:
      {
        BlePacket nackPacket;
        createNackPacket(nackPacket, seqNum);
        sendPacket(nackPacket);
      }
      break;
    default:
      BlePacket ackPacket;
      createAckPacket(ackPacket, seqNum);
      sendPacket(ackPacket);
  } // switch (packetType)
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
        delay(BLE_TIMEOUT / 2);
        numInvalidPacketsReceived = 0;
        return;
      }
      BlePacket nackPacket;
      createNackPacket(nackPacket, seqNum);
      // Received invalid packet, request retransmit with NACK
      sendPacket(nackPacket);
    } else {
      numInvalidPacketsReceived = 0;
      processGivenPacket(receivedPacket);
    }
  } // if (recvBuffer.size() >= PACKET_SIZE)
}

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  uint16_t seqNumToSyn = seqNum;
  if (isWaitingForAck && isPacketValid(lastSentPacket)) {
    seqNumToSyn = lastSentPacket.seqNum;
  }
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) (seqNumToSyn >> BITS_PER_BYTE);
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

/* IMU */
void update_imu_data(void) {
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
  int16_t GyroXLSB = Wire.read() << 8 | Wire.read();
  int16_t GyroYLSB = Wire.read() << 8 | Wire.read();
  int16_t GyroZLSB = Wire.read() << 8 | Wire.read();

  /* //Convert the gyroscope and acclerometer readings to physical units 
  //Convert the LSB scale to physical units by dividing by 16384
  AccX = (float)AccXLSB / 16384;
  AccY = (float)AccYLSB / 16384;
  AccZ = (float)AccZLSB / 16384;

  //Convert the LSB scale to physical units by dividing by 131 
  RateRoll = (float)GyroX / 131; 
  RatePitch = (float)GyroY / 131;
  RateYaw = (float)GyroZ / 131; */
  // Update accelerometer data
  AccX = AccXLSB;
  AccY = AccYLSB;
  AccZ = AccZLSB;

  // Update gyroscope data
  GyroX = GyroXLSB;
  GyroY = GyroYLSB;
  GyroZ = GyroZLSB;
}

BlePacket sendImuPacket() {
  update_acc_data();
  update_gyro_data();
  AccX -= AccErrorX;
  AccY -= AccErrorY;
  AccZ -= AccErrorZ;
  GyroX -= GyroErrorX;
  GyroY -= GyroErrorY;
  GyroZ -= GyroErrorZ;

  BlePacket imuPacket;
  byte imuData[PACKET_DATA_SIZE] = {};
  getBytesFrom(imuData, AccX, AccY, AccZ, GyroX, GyroY, GyroZ);
  createPacket(imuPacket, PacketType::IMU, seqNum, imuData);
  sendPacket(imuPacket);
  return imuPacket;
}

void update_acc_data() {
  // Set low pass filter bandwidth to 10Hz
  // Consider 5Hz for filter bandwidth, given by value "6"
  Wire.beginTransmission(0x68); //default value of MPU register
  Wire.write(0x1A); //writing to the low pass filter register
  Wire.write(0x05); //value of "5" turns on 10Hz
  Wire.endTransmission();

  // Prepare to get accelerometer readings from accelerometer register
  Wire.beginTransmission(0x68);
  Wire.write(0x3B); //register to access accelerometer readings
  Wire.endTransmission();

  Wire.requestFrom(0x68, 6); //request 6 bytes from the MPU (each measurement takes 2 bytes)
  AccX = Wire.read() << 8 | Wire.read();
  AccY = Wire.read() << 8 | Wire.read();
  AccZ = Wire.read() << 8 | Wire.read();
}

void update_gyro_data() {
  // Set low pass filter bandwidth to 10Hz
  // Consider 5Hz for filter bandwidth, given by value "6"
  Wire.beginTransmission(0x68); //default value of MPU register
  Wire.write(0x1A); //writing to the low pass filter register
  Wire.write(0x05); //value of "5" turns on 10Hz
  Wire.endTransmission();

  // Prepare to get gyroscope readings from gyroscope register
  Wire.beginTransmission(0x68);
  Wire.write(0x43); //register to access gyroscope readings
  Wire.endTransmission();

  Wire.requestFrom(0x68, 6);
  GyroX = Wire.read() << 8 | Wire.read();
  GyroY = Wire.read() << 8 | Wire.read();
  GyroZ = Wire.read() << 8 | Wire.read();
}

void setupImu() {
  BlePacket infoPacket;
  byte infoData[PACKET_DATA_SIZE] = {};
  createDataFrom("CALIBRATING", infoData);
  createPacket(infoPacket, PacketType::INFO, INITIAL_SEQ_NUM, infoData);
  sendPacket(infoPacket);

  delay(250);
  
  // Initialise IMU
  Wire.begin();
  Wire.setClock(400000);

  // Reset IMU
  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission();

  // Configure accelerometer of IMU to use sensitivity range of +-2 degrees
  Wire.beginTransmission(0x68); 
  Wire.write(0x1C); // write to accelerometer configuration register
  Wire.write(0x0); // value of "0" gives +-2g
  Wire.endTransmission();

  // Configure gyroscope of IMU to set sensitivity range to +-250 degrees/s
  Wire.beginTransmission(0x68);
  Wire.write(0x1B); //write to gyroscope configuration register
  Wire.write(0x0); //value of "0" gives +- 250 deg
  Wire.endTransmission();
  delay(20);

  // Hold steady to calibrate accelerometer of IMU 
  for (size_t accCalibrationRound = 0; accCalibrationRound < NUM_CALIBRATION_ROUNDS; ++accCalibrationRound) {
    update_acc_data();
    AccErrorX += AccX;
    AccErrorY += AccY;
    AccErrorZ += (AccZ - 1.0);
    delay(1);
  }
  AccErrorX /= NUM_CALIBRATION_ROUNDS;
  AccErrorY /= NUM_CALIBRATION_ROUNDS;
  AccErrorZ /= NUM_CALIBRATION_ROUNDS;

  // Hold steady to calibrate gyroscope of IMU 
  for (size_t gyroCalibrationNumber = 0; gyroCalibrationNumber < NUM_CALIBRATION_ROUNDS; ++gyroCalibrationNumber) {
    update_gyro_data();
    GyroErrorX += GyroX;
    GyroErrorY += GyroY;
    GyroErrorZ += GyroZ;
    delay(1);
  }
  GyroErrorX /= NUM_CALIBRATION_ROUNDS;
  GyroErrorY /= NUM_CALIBRATION_ROUNDS;
  GyroErrorZ /= NUM_CALIBRATION_ROUNDS;

  delay(20);

  byte completeData[PACKET_DATA_SIZE] = {};
  createDataFrom("CALIBRATED", completeData);
  createPacket(infoPacket, PacketType::INFO, INITIAL_SEQ_NUM, completeData);
  sendPacket(infoPacket);
}
