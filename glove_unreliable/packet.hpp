#include <CRC8.h>

#define BAUDRATE 115200
#define BITS_PER_BYTE 8
#define BLE_TIMEOUT 250
#define INITIAL_SEQ_NUM 0
#define INVALID_PACKET_ID -1
#define LOOP_DELAY 25
#define LOWER_4BIT_MASK 0x0F
#define PACKET_SIZE 20
#define PACKET_DATA_SIZE 16
#define READ_PACKET_DELAY 15
#define TRANSMIT_DELAY 50

struct BlePacket {
	/* Start packet header */
	/* Lowest 4 bits: packet type ID, 
   * highest 4 bits: number of padding bytes */
	byte metadata;
	uint16_t seqNum;
	/* End packet header */
	/* Start packet body */
	// 16-bytes of data, e.g. accelerometer data
	byte data[PACKET_DATA_SIZE];
	/* End packet body */
	/* Start footer */
	byte crc;
	/* End footer */
};

enum PacketType {
  HELLO = 0,
  ACK = 1,
  NACK = 2,
  IMU = 3,
  IR_RECV = 4,
  IR_TRANS = 5,
  GAME_STAT = 6,
  GAME_ACTION = 7,
  INFO = 8
};

void createPacket(BlePacket &packet, byte packetType, uint16_t givenSeqNum, byte data[PACKET_DATA_SIZE]);
uint8_t getCrcOf(const BlePacket &packet);
bool isHeadByte(byte currByte);
byte parsePacketTypeFrom(byte metadata);
void serialiseImuData(int16_t givenDataValue, byte imuData[PACKET_DATA_SIZE], int offset);

uint8_t clearSerialInputBuffer() {
  uint8_t numBytesRemoved = 0;
  while (Serial.available()) {
    byte nextByte = (byte) Serial.read();
    numBytesRemoved += 1;
  }
  return numBytesRemoved;
}

void createDataFrom(String givenStr, byte packetData[PACKET_DATA_SIZE]) {
  const size_t MAX_SIZE = givenStr.length() > PACKET_DATA_SIZE ? PACKET_DATA_SIZE : givenStr.length();
  const char *stringChar = givenStr.c_str();
  for (size_t i = 0; i < MAX_SIZE; ++i) {
    packetData[i] = (byte) *(stringChar + i);
  }
  for (size_t i = MAX_SIZE; i < PACKET_DATA_SIZE; ++i) {
    packetData[i] = 0;
  }
}

void createNackPacket(BlePacket &nackPacket, uint16_t givenSeqNum) {
  byte packetData[PACKET_DATA_SIZE] = {};
  createDataFrom("NACK", packetData);
  createPacket(nackPacket, PacketType::NACK, givenSeqNum, packetData);
}

void createPacket(BlePacket &packet, byte packetType, uint16_t givenSeqNum, byte data[PACKET_DATA_SIZE]) {
  packet.metadata = packetType;
  packet.seqNum = givenSeqNum;
  for (byte i = 0; i < PACKET_DATA_SIZE; i += 1) {
    packet.data[i] = data[i];
  }
  packet.crc = getCrcOf(packet);
}

void getBytesFrom(byte imuData[PACKET_DATA_SIZE], int16_t accX, int16_t accY, int16_t accZ, 
      int16_t gyroX, int16_t gyroY, int16_t gyroZ) {
  serialiseImuData(accX, imuData, 0);
  serialiseImuData(accY, imuData, 2);
  serialiseImuData(accZ, imuData, 4);
  serialiseImuData(gyroX, imuData, 6);
  serialiseImuData(gyroY, imuData, 8);
  serialiseImuData(gyroZ, imuData, 10);
  for (size_t i = 12; i < PACKET_DATA_SIZE; ++i) {
    imuData[i] = PACKET_DATA_SIZE - 12;
  }
}

uint8_t getCrcOf(const BlePacket &packet) {
  CRC8 crcGen;
  crcGen.add((uint8_t) packet.metadata);
  crcGen.add((uint8_t) packet.seqNum);
  crcGen.add((uint8_t) (packet.seqNum >> BITS_PER_BYTE));
  for (size_t i = 0; i < PACKET_DATA_SIZE; ++i) {
    uint8_t dataByte = (uint8_t) packet.data[i];
    crcGen.add(dataByte);
  }
  uint8_t crcValue = crcGen.calc();
  return crcValue;
}

void getPacketData(byte packetData[PACKET_DATA_SIZE]) {
  for (size_t i = 0; i < PACKET_DATA_SIZE; ++i) {
    packetData[i] = (byte) Serial.read();
  }
}

char getPacketTypeOf(const BlePacket &packet) {
  if (!isHeadByte(packet.metadata)) {
    return INVALID_PACKET_ID;
  }
  char packetTypeId = (char) parsePacketTypeFrom(packet.metadata);
  return packetTypeId;
}

bool isHeadByte(byte currByte) {
  byte packetId = parsePacketTypeFrom(currByte);
  return packetId >= PacketType::HELLO && packetId <= PacketType::INFO;
}

bool isPacketValid(BlePacket &packet) {
  if (!isHeadByte(packet.metadata)) {
    return false;
  }
  uint8_t computedCrc = getCrcOf(packet);
  if (computedCrc != packet.crc) {
    return false;
  }
  return true;
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

void serialiseImuData(int16_t givenDataValue, byte imuData[PACKET_DATA_SIZE], int offset) {
  if (offset >= PACKET_DATA_SIZE || offset < 0) {
    return;
  }
  imuData[offset] = (byte) givenDataValue;
  imuData[offset + 1] = (byte) (givenDataValue >> BITS_PER_BYTE);
}

byte parsePacketTypeFrom(byte metadata) {
  return metadata & LOWER_4BIT_MASK;
}
