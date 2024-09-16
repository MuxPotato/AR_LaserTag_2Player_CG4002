from collections import deque
from enum import Enum
import struct
from bluepy.btle import DefaultDelegate, Peripheral
import anycrc

# Parameters
PACKET_SIZE = 20
BLE_TIMEOUT = 1.0
INITIAL_SEQ_NUM = 0
ERROR_VALUE = -1
BLUNO_MANUFACTURER_ID = "4c000215e2c56db5dffb48d2b060d0f5a71096e000000000c5"
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
]
## BLE GATT
GATT_SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
GATT_SERIAL_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

# Variables

# Packet Type ID
class PacketType(Enum):
    HELLO = 0
    ACK = 1
    P1_IMU = 2
    P1_IR_RECV = 3
    P1_IR_TRANS = 4
    P2_IMU = 5
    P2_IR_RECV = 6
    P2_IR_TRANS = 7
    GAME_STAT = 8

# Delegate
class BlePacketDelegate(DefaultDelegate):
    def __init__(self, serial_char, dataBuffer):
        super().__init__()
        # self.dataBuffer = bytearray()
        self.dataBuffer = dataBuffer
        self.serial_char = serial_char

    # Bluno Beetle uses cHandle 37
    def handleNotification(self, cHandle, data):
        try:
            #print("Incoming data: {}".format(data.hex()))
            # Add incoming bytes to receive buffer
            #self.dataBuffer += data
            for dataByte in data:
                if isHeaderByte(dataByte) or len(self.dataBuffer) > 0:
                    self.dataBuffer.append(dataByte)
                else:
                    print("Dropping byte {}".format(dataByte))
            """ if len(self.dataBuffer) >= 20:
                # Fetch 1 20-byte packet from the buffer
                dataPacket = self.dataBuffer[0:20]
                # Remove the packet from the buffer
                #del self.dataBuffer[0:20]
                self.dataBuffer = self.dataBuffer[20:]
                print("New packet: {}".format(dataPacket))
                packetId = dataPacket[0]
                print("Packet ID: {}".format(packetId))
                if packetId != 1:
                    self.sendAckPacket() """
        except Exception as err:
            print(err)

    # To be implemented
    def sendAckPacket(self):
        ACK = "ACK............."
        ack_packet = createPacket(1, 5, bytes(ACK, encoding = 'ascii'))
        # TODO: Delete line below
        #print("ACK packet: {}".format(ack_packet))
        self.serial_char.write(ack_packet)

# Connect
def getSerialChar(beetle):
    serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
    serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
    return serial_char

def getCrcOf(packet_id, seq_num, data):
    crc8 = anycrc.Model('CRC8-SMBUS')
    crc8.update(packet_id.to_bytes())
    crc8.update(seq_num.to_bytes(length = 2, byteorder = 'little'))
    dataCrc = crc8.update(data)
    return dataCrc

def createPacket(packet_id, seq_num, data):
    dataCrc = getCrcOf(packet_id, seq_num, data)
    packet = struct.pack("BH16sB", packet_id, seq_num, data, dataCrc)
    return packet

def getPacketFrom(packetBytes):
    packet_id, seq_num, data, dataCrc = struct.unpack("=BH16sB", packetBytes)
    return packet_id, seq_num, data, dataCrc

def connectTo(mac_addr, dataBuffer):
    beetle = None
    try:
        print("Connecting to {}".format(mac_addr))
        beetle = Peripheral(deviceAddr = mac_addr)
        serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
        serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
        beetle.setDelegate(BlePacketDelegate(serial_char, dataBuffer))
    except Exception as err:
        print("Unable to connect to Bluno Beetle")
        print(err)
    return beetle

def isHeaderByte(dataByte):
    return dataByte <= 8 and dataByte >= 0

def isValidPacket(dataPacket):
    return True

def checkReceiveBuffer(receiveBuffer):
    if len(receiveBuffer) >= PACKET_SIZE:
        # Fetch 1 20-byte packet from the buffer
        dataPacket = bytearray([receiveBuffer.popleft()])
        # Remove the packet from the buffer
        #del self.dataBuffer[0:20]
        #receiveBuffer = receiveBuffer[20:]
        count = 0
        while not isHeaderByte(dataPacket[0]) and count < PACKET_SIZE:
            dataPacket.append(receiveBuffer.popleft())
            count += 1
        if count == PACKET_SIZE:
            if isValidPacket(dataPacket):
                return dataPacket
            return bytearray()
        for i in range(PACKET_SIZE - 1):
            dataByte = receiveBuffer.popleft()
            # Do we need this check below?
            """ if isHeaderByte(dataByte):
                break """
            dataPacket.append(dataByte)
        if not isValidPacket(dataPacket):
            return bytearray()
        return dataPacket
    else:
        return bytearray()

def parsePacket(serial_char, packetBytes):
    # Check for NULL packet
    if not packetBytes:
        return ERROR_VALUE, ERROR_VALUE, None
    print("New packet: {}".format(packetBytes))
    # packet_id = packetBytes[0]
    packet_id, seq_num, data, dataCrc = getPacketFrom(packetBytes)
    computedCrc = getCrcOf(packet_id, seq_num, data)
    if dataCrc != computedCrc:
        print("CRC8 not match: {} vs {}".format(dataCrc, computedCrc))
    #print("Packet ID: {}".format(packet_id))
    if packetBytes != 1:
        sendAckPacket(serial_char)
    return packet_id, seq_num, data

# To be implemented
def sendAckPacket(serial_char):
    ACK = "ACK............."
    ack_packet = createPacket(1, 5, bytes(ACK, encoding = 'ascii'))
    serial_char.write(ack_packet)

# Main
dataBuffer = deque()
seq_num = 0
hasHandshake = False
hasSentHello = False
## Receiving packets from the Beetle works ok now. my custom struct on the Beetle in packet.h is sent intact-ly
for beetle_addr in BLUNO_MAC_ADDR_LIST:
    beetle = connectTo(beetle_addr, dataBuffer)
    if beetle:
        try:
            serial_char = getSerialChar(beetle)
            # TODO: Delete line below
            # serial_char.write(bytes("HELLOxxxxxxxxxxxxxxx", encoding = 'ascii'))
            HELLO = "HELLO"
            hello_packet = createPacket(0, INITIAL_SEQ_NUM, bytes(HELLO, encoding = 'ascii'))
            serial_char.write(hello_packet)
            while True:
                """ if (not hasHandshake) and (not hasSentHello):
                    HELLO = "HELLO"
                    hello_packet = createPacket(0, INITIAL_SEQ_NUM, bytes(HELLO, encoding = 'ascii'))
                    serial_char.write(hello_packet)
                    hasSentHello = True
                if beetle.waitForNotifications(BLE_TIMEOUT):
                    # print("Received notification")
                    packetBytes = checkReceiveBuffer(dataBuffer)
                    if hasHandshake:
                        parsePacket(serial_char, packetBytes)
                    else:
                        # Check whether received packet is ACK
                        packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
                        if packet_id == PacketType.ACK and seq_num == INITIAL_SEQ_NUM:
                            hasHandshake = True """

                if beetle.waitForNotifications(BLE_TIMEOUT):
                    print("Received notification")
                    dataPacket = checkReceiveBuffer(dataBuffer)
                    parsePacket(serial_char, dataPacket)
        except KeyboardInterrupt as key:
            print("Keyboard interrupt")
        except Exception as err:
            print(err)
        finally:
            if beetle:
                print("Disconnecting {}".format(beetle.addr))
            beetle.disconnect()
