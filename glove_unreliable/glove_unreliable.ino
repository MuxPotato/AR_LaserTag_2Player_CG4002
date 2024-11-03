#include "imu.hpp"
#include "packet.hpp"

#define SETUP_DELAY 5000

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum);

/* Internal comms */
HandshakeStatus handshakeStatus = STAT_NONE;
unsigned long lastSentPacketTime = 0;
uint16_t seqNum = INITIAL_SEQ_NUM;
unsigned long lastReadPacketTime = 0;

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

  // Set built-in LED to OUTPUT so it can be turned on
  pinMode(LED_BUILTIN, OUTPUT);

  // Set up internal comms 
  setupBle();
  
  // Setup IMU
  delay(SETUP_DELAY);
  setupImu();
}

void loop() {
  if (!hasHandshake()) {
    handshakeStatus = doHandshake();
  } else {
    if (Serial.available() >= PACKET_SIZE) {
      processIncomingPacket();
    } else {
      unsigned long transmitPeriod = millis() - lastSentPacketTime;
      if (transmitPeriod < TRANSMIT_DELAY) {
        // Maintain at least (TRANSMIT_DELAY) ms delay between transmissions to avoid overwhelming the Beetle
        delay(TRANSMIT_DELAY - transmitPeriod);
      }
      BlePacket imuPacket = sendImuPacket();
      lastSentPacketTime = millis();
      seqNum += 1;
    }
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
            return HandshakeStatus::STAT_SYN;
          } else if (getPacketTypeOf(receivedPacket) == PacketType::HELLO) {
            handshakeStatus = STAT_HELLO;
            mSeqNum = INITIAL_SEQ_NUM;
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
  // Clear the serial input buffer
  clearSerialInputBuffer();
  // Clear the serial output buffer
  //   WARNING: This sends out all existing data in the output buffer over BLE though
  Serial.flush();
}

void createHandshakeAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  uint16_t seqNumToSyn = seqNum;
  packetData[0] = (byte) seqNumToSyn;
  packetData[1] = (byte) (seqNumToSyn >> BITS_PER_BYTE);
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, packetData);
}

bool hasHandshake() {
  return handshakeStatus == HandshakeStatus::STAT_SYN;
}

void processGivenPacket(BlePacket &packet) {
  char packetType = getPacketTypeOf(packet);
  switch (packetType) {
    case PacketType::HELLO:
      handshakeStatus = STAT_HELLO;
      break;
  }
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
  if (isPacketValid(receivedPacket)) {
    processGivenPacket(receivedPacket);
  }
  // Unreliable communication, so drop packet if incoming packet is invalid
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

  // Turn on LED to indicate start of calibration
  digitalWrite(LED_BUILTIN, HIGH);

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

  // Turn off LED to indicate that claibration is complete
  digitalWrite(LED_BUILTIN, LOW);

  delay(20);

  byte completeData[PACKET_DATA_SIZE] = {};
  createDataFrom("CALIBRATED", completeData);
  createPacket(infoPacket, PacketType::INFO, INITIAL_SEQ_NUM, completeData);
  sendPacket(infoPacket);
}
