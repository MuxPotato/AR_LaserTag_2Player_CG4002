#include "CRC8.h"

#define BITS_PER_BYTE 8
#define BLE_TIMEOUT 200
#define FIRST_ELEMENT 0
#define INVALID_PACKET_ID -1
#define INITIAL_SEQ_NUM 0
#define LOWER_4BIT_MASK 0x0F
#define MAX_BUFFER_SIZE 40
#define PACKET_SIZE 20
#define PACKET_DATA_SIZE 16
#define PACKET_TYPE_SIZE 4

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
	P1_IMU = 3,
	P1_IR_RECV = 4,
	P1_IR_TRANS = 5,
	P2_IMU = 6,
	P2_IR_RECV = 7,
	P2_IR_TRANS = 8,
	GAME_STAT = 9
};

enum HandshakeStatus {
  STAT_NONE = 0,
  STAT_HELLO = 1,
  STAT_ACK = 2,
  STAT_SYN = 3
};

template <typename T> class CircularBuffer {
private:
  T elements[MAX_BUFFER_SIZE];
  int head;
  int tail;
  int length;

  int getLength() {
    return this->length;
  }

  void setLength(int length) {
    this->length = length;
  }

public:
  CircularBuffer() {
    this->length = 0;
    this->head = 0;
    this->tail = 0;
  }

  void clear() {
    this->head = 0;
    this->tail = 0;
    this->setLength(0);
  }

  T get(int index) {
    if (index < this->size()) {
      return this->elements[this->head + index];
    }
    return T();
  }

  bool push_back(T element) {
    if (isFull()) {
      return false;
    }
    this->elements[this->tail] = element;
    this->tail = (this->tail + 1) % MAX_BUFFER_SIZE;
    this->setLength(this->getLength() + 1);
    return true;
  }

  T pop_front() {
    if (isEmpty()) {
      return T();
    }
    T current = this->elements[this->head];
    this->head = (this->head + 1) % MAX_BUFFER_SIZE;
    //this->elements[this->head] = T();
    this->setLength(this->getLength() - 1);
    return current;
  }

  bool isEmpty() {
    return this->getLength() == 0;
  }

  bool isFull() {
    return this->getLength() == MAX_BUFFER_SIZE;
  }

  int size() {
    return this->getLength();
  }
};

bool doHandshake();
uint8_t getCrcOf(const BlePacket &packet);
bool sendPacketFrom(CircularBuffer<BlePacket> &sendBuffer);

void convertBytesToPacket(CircularBuffer<char> &dataBuffer, BlePacket &packet) {
  packet.metadata = dataBuffer.pop_front();
  packet.seqNum = dataBuffer.pop_front() + (dataBuffer.pop_front() << BITS_PER_BYTE);
  for (auto &dataByte : packet.data) {
    dataByte = dataBuffer.pop_front();
  }
  packet.crc = dataBuffer.pop_front();
}

void createPacket(BlePacket &packet, byte packetType, short givenSeqNum, byte data[PACKET_DATA_SIZE]) {
  packet.metadata = packetType;
  packet.seqNum = givenSeqNum;
  for (byte i = 0; i < PACKET_DATA_SIZE; i += 1) {
    packet.data[i] = data[i];
  }
  packet.crc = getCrcOf(packet);
}

void createAckPacket(BlePacket &ackPacket, uint16_t givenSeqNum) {
  byte data[PACKET_DATA_SIZE] = {'A', 'C', 'K'};
  createPacket(ackPacket, PacketType::ACK, givenSeqNum, data);
}

void floatToData(char data[PACKET_DATA_SIZE], float x1, float y1, float z1, float x2, float y2, float z2) {
  short x1s = (short) (x1 * 100);
  data[0] = (char) x1s;
  data[1] = (char) x1s >> BITS_PER_BYTE;
  short y1s = (short) (y1 * 100);
  data[2] = (char) y1s;
  data[3] = (char) y1s >> BITS_PER_BYTE;
  short z1s = (short) (z1 * 100);
  data[4] = (char) z1s;
  data[5] = (char) z1s >> BITS_PER_BYTE;
  short x2s = (short) (x2 * 100);
  data[6] = (char) x2s;
  data[7] = (char) x2s >> BITS_PER_BYTE;
  short y2s = (short) (y2 * 100);
  data[8] = (char) y2s;
  data[9] = (char) y2s >> BITS_PER_BYTE;
  short z2s = (short) (z2 * 100);
  data[10] = (char) z2s;
  data[11] = (char) z2s >> BITS_PER_BYTE;
  // Padding bytes
  for (size_t i = 12; i < PACKET_DATA_SIZE; i += 1) {
    data[i] = 0;
  }
}

uint8_t getCrcOf(const BlePacket &packet) {
  CRC8 crcGen;
  crcGen.add((uint8_t) packet.metadata);
  crcGen.add((uint8_t) packet.seqNum);
  crcGen.add((uint8_t) packet.seqNum >> BITS_PER_BYTE);
  for (auto c : packet.data) {
    crcGen.add((uint8_t) c);
  }
  uint8_t crcValue = crcGen.calc();
  return crcValue;
}

byte getPacketTypeOf(const BlePacket &packet) {
  if (!isHeadByte(packet.metadata)) {
    return INVALID_PACKET_ID;
  }
  byte packetTypeId = parsePacketTypeFrom(packet.metadata);
  return packetTypeId;
}

byte getNumOfPaddingBytes(const BlePacket &packet) {
  byte numPaddingBytes = packet.metadata >> PACKET_TYPE_SIZE;
  return numPaddingBytes;
}

bool isHeadByte(byte currByte) {
  byte packetId = parsePacketTypeFrom(currByte);
  return packetId >= PacketType::HELLO && packetId <= PacketType::GAME_STAT;
}

bool isPacketValid(BlePacket &packet) {
  if (!isHeadByte(packet.metadata)) {
    return false;
  }
  uint8_t computedCrc = getCrcOf(packet);
  uint8_t receivedCrc = packet.crc;
  if (computedCrc != receivedCrc) {
    return false;
  }
  byte numPaddingBytes = getNumOfPaddingBytes(packet);
  for (size_t i = 1; i <= numPaddingBytes; i += 1) {
    if (packet.data[PACKET_DATA_SIZE - i] != numPaddingBytes) {
      return false;
    }
  }
  return true;
}

byte parsePacketTypeFrom(byte metadata) {
  return metadata & LOWER_4BIT_MASK;
}

// Accept BlePacket to be returned as a parameter passed by reference for efficiency
void readPacket(CircularBuffer<char> &recvBuff, BlePacket &packet) {
  while (recvBuff.size() < PACKET_SIZE) {
    if (!Serial.available()) {
      continue;
    }
    char newByte = Serial.read();
    if (isHeadByte(recvBuff.get(FIRST_ELEMENT)) || recvBuff.size() > 0) {
      // Append new byte to receive buffer
      recvBuff.push_back(newByte);
    }
  }
  // receiveBuffer.length() >= PACKET_SIZE
  convertBytesToPacket(recvBuff, packet);
  return packet;
}

void sendPacket(const BlePacket &packet) {
  Serial.write((byte *) &packet, sizeof(packet));
}

bool shouldIncSeqNumFor(const BlePacket &packet) {
  byte packetTypeId = packet.metadata & LOWER_4BIT_MASK;
  return packetTypeId != PacketType::ACK;
}
