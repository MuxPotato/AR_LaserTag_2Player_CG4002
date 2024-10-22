#include "imu.hpp"
#include "packet.hpp"

#define SETUP_DELAY 5000

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum);

/* Internal comms */
bool hasHandshake = false;
HandshakeStatus handshakeStatus = STAT_NONE;
// unsigned long lastSentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;

/* IMU variables */
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
  
  // Setup IMU
  delay(SETUP_DELAY);
  setupImu();
}

void loop() {
  if (!hasHandshake) {
    hasHandshake = doHandshake();
  } else {
    if (Serial.available() >= PACKET_SIZE) {
      processIncomingPacket();
    } else {
      BlePacket imuPacket = sendImuPacket();
      // lastSentPacketTime = millis();
      seqNum += 1;
    }
  }
  delay(LOOP_DELAY);
}

bool doHandshake() {
  unsigned long mPacketSentTime = millis();
  byte mSeqNum = INITIAL_SEQ_NUM;
  while (handshakeStatus != STAT_SYN) { 
    switch (handshakeStatus) {
      case STAT_NONE:
        {
          while (Serial.available() < PACKET_SIZE);
          BlePacket receivedPacket = readPacket();
          if (!isPacketValid(receivedPacket) || receivedPacket.seqNum != mSeqNum) {
            BlePacket nackPacket;
            createNackPacket(nackPacket, mSeqNum);
            sendPacket(nackPacket);
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO) {
            handshakeStatus = STAT_HELLO;
          }
          break;
        }
      case STAT_HELLO:
        {
          // Reset mSeqNum to initial value so it's not incremented too many times when we retransmit the ACK
          mSeqNum = INITIAL_SEQ_NUM;
          BlePacket ackPacket;
          createHandshakeAckPacket(ackPacket, mSeqNum);  
          sendPacket(ackPacket);
          mSeqNum += 1;
          mPacketSentTime = millis();
          handshakeStatus = STAT_ACK;
          break;
        }
      case STAT_ACK:
        {
          bool hasReceivedPacket = false;
          while ((millis() - mPacketSentTime) < BLE_TIMEOUT) {
            while (Serial.available() < PACKET_SIZE);
            /* BUG: This if block is still getting triggered after the laptop sends SYN+ACK */
            BlePacket receivedPacket = readPacket();
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
    }
  } // while (handshakeStatus != STAT_SYN)
  return false;
}

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  uint16_t seqNumToSyn = seqNum;
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) (seqNumToSyn >> BITS_PER_BYTE);
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, packetData);
}

void getPacketData(byte packetData[PACKET_DATA_SIZE]) {
  for (size_t i = 0; i < PACKET_DATA_SIZE; ++i) {
    packetData[i] = (byte) Serial.read();
  }
}

void processGivenPacket(BlePacket &packet) {
  char packetType = getPacketTypeOf(packet);
  switch (packetType) {
    case PacketType::HELLO:
      hasHandshake = false;
      handshakeStatus = STAT_HELLO;
      break;
  }
}

void processIncomingPacket() {
  BlePacket receivedPacket = readPacket();
  if (isPacketValid(receivedPacket)) {
    processGivenPacket(receivedPacket);
  }
  // Unreliable communication, so drop packet if incoming packet is invalid
}

BlePacket readPacket() {
  BlePacket newPacket = {};
  if (Serial.available() < PACKET_SIZE) {
    return newPacket;
  }
  newPacket.metadata = (byte) Serial.read();
  uint16_t seqNumLowByte = (uint16_t) Serial.read();
  uint16_t seqNumHighByte = (uint16_t) Serial.read();
  newPacket.seqNum = seqNumLowByte + (seqNumHighByte << BITS_PER_BYTE);
  getPacketData(newPacket.data);
  newPacket.crc = (byte) Serial.read();
  return newPacket;
}

void sendPacket(BlePacket &packetToSend) {
  Serial.write((byte *) &packetToSend, sizeof(packetToSend));
}

/* IMU */
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
    AccErrorZ += (AccZ - ACC_LSB);
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
