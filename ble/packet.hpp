#define PACKET_SIZE 20
#define BITS_PER_BYTE 8
#define MAX_BUFFER_SIZE 30
#define LOWER_4BIT_MASK 0x0F
#define BLE_TIMEOUT 200

struct BlePacket {
	/* Start packet header */
	// Highest 4 bits: packet type ID, lowest 4 bits: number of padding bytes
	byte metadata;
	uint16_t seqNum;
	/* End packet header */
	/* Start packet body */
	// 16-bytes of data, e.g. accelerometer data
	byte data[16];
	/* End packet body */
	/* Start footer */
	byte checksum;
	/* End footer */
};

enum PacketType {
	HELLO = 0,
	ACK = 1,
	P1_IMU = 2,
	P1_IR_RECV = 3,
	P1_IR_TRANS = 4,
	P2_IMU = 5,
	P2_IR_RECV = 6,
	P2_IR_TRANS = 7,
	GAME_STAT = 8
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
BlePacket createAckPacket(uint16_t givenSeqNum);
bool sendPacketFrom(CircularBuffer<BlePacket> &sendBuffer);
void ackHelloPacket();
bool parseSynAck(BlePacket &packet, uint16_t expectedSeqNum);

bool isHeadByte(byte currByte) {
  byte packetId = currByte & LOWER_4BIT_MASK;
  return packetId >= PacketType::HELLO && packetId <= PacketType::GAME_STAT;
}

bool isPacketValid(BlePacket &packet) {
  // TODO: Implement actual checks
  return true;
}

bool shouldIncSeqNumFor(const BlePacket &packet) {
  byte packetTypeId = packet.metadata & LOWER_4BIT_MASK;
  return packetTypeId != PacketType::ACK;
}

void convertBytesToPacket(String &dataBuffer, BlePacket &packet) {
  packet.metadata = dataBuffer.charAt(0);
  packet.seqNum = dataBuffer.charAt(1) + (dataBuffer.charAt(2) << BITS_PER_BYTE);
  byte index = 3;
  for (auto &dataByte : packet.data) {
    dataByte = dataBuffer.charAt(index);
    index += 1;
  }
  packet.checksum = dataBuffer.charAt(PACKET_SIZE - 1);
}

void readPacket(BlePacket &packet) {
  packet.metadata = -1;
  String receiveBuffer = "";
  byte count = 0;
  while (Serial.available() && count < PACKET_SIZE) {
    char nextByte = Serial.read();
    // TODO: Implement robust packet parsing from buffer
    /* if (!isHeadByte(nextByte)) {
      continue;
    } */
    receiveBuffer += nextByte;
    if (receiveBuffer.length() == PACKET_SIZE) {
      // We have received one complete packet, stop reading BLE data
      String packetBytes = receiveBuffer.substring(0, PACKET_SIZE);
      convertBytesToPacket(packetBytes, packet);
    }
    count += 1;
  }
}
