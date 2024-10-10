#include <Wire.h>
#include "packet.hpp"

void gyro_signals();
void sendImuPacket();

/* Internal Comms variables */
HandshakeStatus handshakeStatus = STAT_NONE;
bool hasHandshake = false;
uint16_t seqNum = INITIAL_SEQ_NUM;
unsigned long sentPacketTime = 0;
unsigned long lastDataTime = 0;
CircularBuffer<char> recvBuff{};
CircularBuffer<BlePacket> sendBuffer{};

/* IMU variables */
float RateRoll, RatePitch, RateYaw;
float RateCalibrationRoll, RateCalibrationPitch, RateCalibrationYaw;
int RateCalibrationNumber;
float AccX, AccY, AccZ;
float AngleRoll, AnglePitch;
float LoopTimer;

void sendDummyPacket() {
  BlePacket dummyPacket;
  // Dummy IMU data
  dummyPacket.metadata = PacketType::P1_IMU;
  dummyPacket.seqNum = seqNum;
  /* Generate 2 sets of 3 random floating point 
   * numbers to represent IMU gyroscope(x1, y1, z1) 
   * and accelerometer(x2, y2, z2) data */
  float x1 = random(0, 100);
  float y1 = random(0, 100);
  float z1 = random(0, 100);
  float x2 = random(0, 100);
  float y2 = random(0, 100);
  float z2 = random(0, 100);
  /* Pack the floating point numbers into the 
   * 16-byte data array */
  floatToData(dummyPacket.data, x1, y1, z1, x2, y2, z2);
  dummyPacket.crc = getCrcOf(dummyPacket);
  sendBuffer.push_back(dummyPacket);
  seqNum += 1;
}

void sendAckPacket(uint16_t givenSeqNum) {
  BlePacket ackPacket;
  createAckPacket(ackPacket, givenSeqNum);
  //sendBuffer.push_back(ackPacket);
  sendPacket(ackPacket);
}

void sendSynPacket(byte givenSeqNum) {
  BlePacket synPacket;
  createAckPacket(synPacket, givenSeqNum);
  synPacket.data[3] = (byte)'S';
  synPacket.data[4] = (byte)'Y';
  synPacket.data[5] = (byte)'N';
  sendBuffer.push_back(synPacket);
}

void setup() {
  Serial.begin(BAUDRATE);
  delay(500);

  BlePacket infoPacket;
  //byte infoData[PACKET_DATA_SIZE] = {'C', 'A', 'L', 'I', 'B', 'R', 'A', 'T', 'I', 'N', 'G'};
  byte infoData[PACKET_DATA_SIZE] = {};
  getDataFrom("CALIBRATING", infoData);
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

  //byte completeData[PACKET_DATA_SIZE] = {'C', 'A', 'L', 'I', 'B', 'R', 'A', 'T', 'E', 'D'};
  byte completeData[PACKET_DATA_SIZE] = {};
  getDataFrom("CALIBRATED", completeData);
  createPacket(infoPacket, PacketType::GAME_STAT, INITIAL_SEQ_NUM, completeData);
  sendPacket(infoPacket);
}

void loop() {
  if (!hasHandshake) {
    while (!doHandshake());
    hasHandshake = true;
  }
  // Assert: hasHandshake == true
  if (Serial.available()) {
    BlePacket currPacket;
    readPacket(recvBuff, currPacket);
    if (getPacketTypeOf(currPacket) == PacketType::HELLO) {
      hasHandshake = false;
      handshakeStatus = STAT_HELLO;
      return;
    } else if (getPacketTypeOf(currPacket) != PacketType::ACK) {
      sendAckPacket(currPacket.seqNum);
    }
  } //else if (!sendBuffer.isFull()) {
    else if ((millis() - lastDataTime) > 50) {
      // If there's no packet received, send IMU data
      sendImuPacket();
      lastDataTime = millis();
    }
  //}
  // Send packet from sendBuffer if any exist
  /* if (!sendBuffer.isEmpty()) {
    BlePacket firstPacket = sendBuffer.get(FIRST_ELEMENT);
    sendPacket(firstPacket);

    if (getPacketTypeOf(firstPacket) != PacketType::ACK) {
      // Read response packet from laptop
      BlePacket resultPacket;
      unsigned long sentTime = millis();
      // Block until complete packet received
      readPacket(recvBuff, resultPacket);
      unsigned long recvTime = millis();
      if (getPacketTypeOf(resultPacket) == PacketType::HELLO) {
        hasHandshake = false;
        handshakeStatus = STAT_HELLO;
        return;
      }
      if (getPacketTypeOf(resultPacket) == PacketType::ACK &&
        (recvTime - sentTime) < BLE_TIMEOUT) {
        // Packet received by laptop, remove from sendBuffer
        sendBuffer.pop_front();
        seqNum += 1;
      } else if (getPacketTypeOf(resultPacket) != PacketType::ACK) {
        // TODO: Handle actual data from laptop that is not HELLO or ACK
        sendAckPacket(resultPacket.seqNum);
      }
    } else {
      // Don't read response from laptop if Beetle just sent an ACK to a laptop's data packet
      // But still remove the packet from buffer
      sendBuffer.pop_front();
    }
  } */
}

bool doHandshake() {
  unsigned long mSentTime = millis();
  while (true) {
    if (handshakeStatus == STAT_NONE) {
      /* Either Beetle got powered off accidentally and reconnected, 
       * or Beetle is connecting to laptop for the first time */
      BlePacket mPacket;
      readPacket(recvBuff, mPacket);
      if (getPacketTypeOf(mPacket) == PacketType::HELLO) {
        handshakeStatus = STAT_HELLO;
      }
    } else if (handshakeStatus == STAT_HELLO) {
      BlePacket ackPacket;
      createAckPacket(ackPacket, seqNum);
      sendPacket(ackPacket);
      mSentTime = millis();
      handshakeStatus = STAT_ACK;
    } else if (handshakeStatus == STAT_ACK) {
      BlePacket packet;
      readPacket(recvBuff, packet);
      if ((millis() - mSentTime) > BLE_TIMEOUT) {
        // Timeout, retransmit ACK packet
        handshakeStatus = STAT_HELLO;
        mSentTime = millis();
        continue;
      }
      // Check whether laptop sent SYN+ACK
      if (getPacketTypeOf(packet) == PacketType::ACK) {
        uint16_t laptopSeqNum = INITIAL_SEQ_NUM;
        if (laptopSeqNum < seqNum) {
          // TODO: Verify whether this is sound, will we 'forget' any lost packets?
          seqNum = laptopSeqNum;
        }
        // If seqNum < laptopSeqNum, we assume that laptop will update its internal seqNum count
        handshakeStatus = STAT_SYN;
        // Handshake is now complete
        return true;
      } else if (getPacketTypeOf(packet) == PacketType::HELLO) {
        // HELLO packet again, restart handshake
        handshakeStatus = STAT_HELLO;
      }
    }
  }
  return false;
}

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

void sendImuPacket() {
  gyro_signals();
  RateRoll -= RateCalibrationRoll;
  RatePitch -= RateCalibrationPitch;
  RateYaw -= RateCalibrationYaw;

  BlePacket imuPacket;
  byte imuData[PACKET_DATA_SIZE] = {};
  floatToData(imuData, AccX, AccY, AccZ, RatePitch, RateRoll, RateYaw);
  createPacket(imuPacket, PacketType::P1_IMU, seqNum, imuData);
  //sendBuffer.push_back(imuPacket);
  sendPacket(imuPacket);
}

bool sendPacketFrom(CircularBuffer<BlePacket> &sendBuffer) {
  // Nothing can be done if the buffer is empty!
  if (sendBuffer.isEmpty()) {
    return false;
  }
  // There's 1 or more packets to send
  BlePacket packet = sendBuffer.pop_front();
  sendPacket(packet);
  if (shouldIncSeqNumFor(packet)) {
    seqNum += 1;
  }
  return true;
}
