from collections import deque
from enum import Enum
import random
import struct
import time
from bluepy.btle import DefaultDelegate, Peripheral, BTLEDisconnectError
import anycrc

# Parameters
PACKET_SIZE = 20
BLE_TIMEOUT = 1.0
PACKET_TIMEOUT = 0.2
INITIAL_SEQ_NUM = 0
ERROR_VALUE = -1
BLUNO_MANUFACTURER_ID = "4c000215e2c56db5dffb48d2b060d0f5a71096e000000000c5"
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
    #"F4:B8:5E:42:6D:75",
    #"F4:B8:5E:42:67:6E"
]
## BLE GATT
GATT_SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
GATT_SERIAL_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

# Variables
numFragmented = 0

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

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Delegate
class BlePacketDelegate(DefaultDelegate):
    def __init__(self, serial_char, dataBuffer):
        super().__init__()
        # self.dataBuffer = bytearray()
        self.dataBuffer = dataBuffer
        self.serial_char = serial_char

    # Bluno Beetle uses cHandle 37
    def handleNotification(self, cHandle, data):
        global numFragmented
        try:
            #print("Incoming data: {}".format(data.hex()))
            # Add incoming bytes to receive buffer
            #self.dataBuffer += data
            if len(data) < PACKET_SIZE:
                print("Fragmented packet received")
                numFragmented += 1
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
    packet = struct.pack("=BH16sB", packet_id, seq_num, data, dataCrc)
    return packet

def getPacketFrom(packetBytes):
    packet_id, seq_num, data, dataCrc = struct.unpack("=BH16sB", packetBytes)
    return packet_id, seq_num, data, dataCrc

def connectTo(mac_addr, dataBuffer):
    beetle = None
    """ try:
        print("Connecting to {}".format(mac_addr))
        beetle = Peripheral(deviceAddr = mac_addr)
        serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
        serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
        beetle.setDelegate(BlePacketDelegate(serial_char, dataBuffer))
    except Exception as err:
        print("Unable to connect to Bluno Beetle")
        print(err)
    return beetle """
    print("Connecting to {}".format(mac_addr))
    beetle = Peripheral(deviceAddr = mac_addr)
    serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
    serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
    beetle.setDelegate(BlePacketDelegate(serial_char, dataBuffer))
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
    print("{}New packet: {}{}".format(bcolors.OKGREEN, packetBytes, bcolors.ENDC))
    # packet_id = packetBytes[0]
    packet_id, seq_num, data, dataCrc = getPacketFrom(packetBytes)
    computedCrc = getCrcOf(packet_id, seq_num, data)
    if dataCrc != computedCrc:
        print("CRC8 not match: {} vs {}".format(dataCrc, computedCrc))
    """ # 1/10 chance of considering the packet corrupted
    if random.randrange(1, 11):
        return packet_id, seq_num, bytearray() """
    #print("Packet ID: {}".format(packet_id))
    #if packet_id != PacketType.ACK.value:
        #sendAckPacket(serial_char)
    return packet_id, seq_num, data

# To be implemented
def sendAckPacket(serial_char, seq_num):
    ACK = "ACK............."
    #ack_packet = createPacket(1, 5, bytes(ACK, encoding = 'ascii'))
    ack_packet = createPacket(PacketType.ACK.value, seq_num, bytes(ACK, encoding = 'ascii'))
    serial_char.write(ack_packet)
    print("Sending ACK: {}".format(ack_packet))

def beetleLoop(beetle, serial_char, dataBuffer):
    seq_num = 0
    hasHandshake = False
    hasSentHello = False
    sentTime = 0
    while True:
        if (not hasHandshake) and (not hasSentHello):
            HELLO = "HELLO"
            hello_packet = createPacket(0, INITIAL_SEQ_NUM, bytes(HELLO, encoding = 'ascii'))
            print("{}Sending HELLO: {}{}".format(bcolors.OKBLUE, hello_packet, bcolors.ENDC))
            serial_char.write(hello_packet)
            hasSentHello = True
            sentTime = time.time()
        elif (not hasHandshake) and hasSentHello and (time.time() - sentTime) > 0.2:
            hasSentHello = False
            continue
        if beetle.waitForNotifications(BLE_TIMEOUT):
            recvTime = time.time()
            #print("Received notification")
            packetBytes = checkReceiveBuffer(dataBuffer)
            if hasHandshake:
                packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
                if packet_id != PacketType.ACK.value:
                    sendAckPacket(serial_char, seq_num)
            else:
                # Check whether received packet is ACK
                packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
                #if packet_id == PacketType.ACK.value and seq_num == INITIAL_SEQ_NUM:
                if packet_id == PacketType.ACK.value:
                    SYNACK = "SYNACK"
                    syn_ack_packet = createPacket(PacketType.ACK.value, seq_num, bytes(SYNACK, encoding = "ascii"))
                    serial_char.write(syn_ack_packet)
                    #print("Sent SYN+ACK: {}".format(syn_ack_packet))
                    throughput = 20 / (recvTime - sentTime) / 1024
                    print("Throughput: {} kb/s".format(throughput))
                    hasHandshake = True

def startBeetle(beetle_addr):
    dataBuffer = deque()
    beetle = connectTo(beetle_addr, dataBuffer)
    if beetle:
        serial_char = getSerialChar(beetle)
        beetleLoop(beetle, serial_char, dataBuffer)

# Main
dataBuffer = deque()
seq_num = 0
hasHandshake = False
hasSentHello = False
## Receiving packets from the Beetle works ok now. my custom struct on the Beetle in packet.h is sent intact-ly
for beetle_addr in BLUNO_MAC_ADDR_LIST:
    while True:
        beetle = connectTo(beetle_addr, dataBuffer)
        if beetle:
            try:
                while True:
                    serial_char = getSerialChar(beetle)
                    sentTime = 0
                
                    if (not hasHandshake) and (not hasSentHello):
                        HELLO = "HELLO"
                        hello_packet = createPacket(0, INITIAL_SEQ_NUM, bytes(HELLO, encoding = 'ascii'))
                        print("Sending HELLO: {}".format(hello_packet))
                        serial_char.write(hello_packet)
                        hasSentHello = True
                        sentTime = time.time()
                    elif (not hasHandshake) and hasSentHello and (time.time() - sentTime) > 0.2:
                        hasSentHello = False
                        continue
                    if beetle.waitForNotifications(BLE_TIMEOUT):
                        recvTime = time.time()
                        #print("Received notification")
                        packetBytes = checkReceiveBuffer(dataBuffer)
                        if hasHandshake:
                            """ if (random.randrange(1, 11) == 1):
                                # 1/10 chance to drop the packet
                                print("    Packet dropped")
                                continue """
                            packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
                            if not data or len(data) == 0:
                                continue
                            if packet_id != PacketType.ACK.value:
                                sendAckPacket(serial_char, seq_num)
                        else:
                            # Check whether received packet is ACK
                            packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
                            if not data or len(data) == 0:
                                continue
                            #if packet_id == PacketType.ACK.value and seq_num == INITIAL_SEQ_NUM:
                            if packet_id == PacketType.ACK.value:
                                SYNACK = "SYNACK"
                                syn_ack_packet = createPacket(PacketType.ACK.value, seq_num, bytes(SYNACK, encoding = "ascii"))
                                serial_char.write(syn_ack_packet)
                                #print("Sent SYN+ACK: {}".format(syn_ack_packet))
                                throughput = 20 / (recvTime - sentTime) / 1024
                                print("Throughput: {} kb/s".format(throughput))
                                hasHandshake = True

            except BTLEDisconnectError as bleErr:
                print("{}Device disconnected{}".format(bcolors.WARNING, bcolors.ENDC))
                while True:
                    if beetle:
                        print("{}Attempting to connect{}".format(bcolors.WARNING, bcolors.ENDC))
                        try:
                            beetle.connect(beetle_addr)
                        except KeyboardInterrupt as key:
                            print("Keyboard interrupt")
                            break
                    time.sleep(0.25)
            except KeyboardInterrupt as key:
                print("Keyboard interrupt")
                break
            except Exception as err:
                print(err)
                continue
        time.sleep(0.5)

    if beetle:
        print("{}Disconnecting {}{}".format(bcolors.WARNING, beetle.addr, bcolors.ENDC))
        print("{} fragmented packets".format(numFragmented))
        beetle.disconnect()
        """ finally:
            if beetle:
                print("Disconnecting {}".format(beetle.addr))
                print("{} fragmented packets".format(numFragmented))
            beetle.disconnect() """

""" for beetle_addr in BLUNO_MAC_ADDR_LIST:
    while True:
        try:
            startBeetle(beetle_addr)
        except KeyboardInterrupt as key:
            print("Caught keyboard interrupt")

        except Exception as err:
            print(err)
            continue """

""" Planning
-Connect to Beetle using MAC
-Loop:
--> Handshake if not already handshaken
--> Send ACK if incoming packet received
-Disconnect Beetle gracefully if keyboard interrupt
"""
def sendHello(seq_num, serial_char):
    HELLO = "HELLO"
    hello_packet = createPacket(PacketType.HELLO.value, seq_num, bytes(HELLO, encoding = 'ascii'))
    print("Sending HELLO: {}".format(hello_packet))
    serial_char.write(hello_packet)
def sendAck(seq_num, serial_char):
    SYNACK = "SYNACK"
    syn_ack_packet = createPacket(PacketType.ACK.value, seq_num, bytes(SYNACK, encoding = "ascii"))
    serial_char.write(syn_ack_packet)
mBeetle = Peripheral()
# Runtime variables
mDataBuffer = deque()
hasHandshake = False
hasSentHello = False
seq_num = 0
sendHelloTime = 0
mRecvTime = 0
# Connect to Beetle
try:
    mBeetle.connect(beetle_mac_addr)
except BTLEDisconnectError as disconnectErr:
    print(disconnectErr)
mSerialChar = getSerialChar(mBeetle)
while True:
    # Send HELLO
    if (not hasHandshake) and (not hasSentHello):
        sendHelloTime = time.time()
        sendHello(INITIAL_SEQ_NUM, mSerialChar)
        hasSentHello = True
    # Handle HELLO timeout
    elif (not hasHandshake) and hasSentHello and (time.time() - sendHelloTime) >= BLE_TIMEOUT:
        hasSentHello = False
        continue
    # Check for ACK to HELLO
    if mBeetle.waitForNotifications(BLE_TIMEOUT):
        mRecvTime = time.time()
        # bytearray for 20-byte packet
        packetBytes = checkReceiveBuffer(mDataBuffer)
        # Parse packet from 20-byte
        packet_id, seq_num, data = parsePacket(serial_char, packetBytes)
        if data and (len(data) > 0):
            if not hasHandshake:
                # Send SYN+ACK
                if packet_id == PacketType.ACK.value:
                    sendAck(seq_num, serial_char)
                    hasHandshake = True
            else:
                if packet_id != PacketType.ACK.value:
                    sendAck(seq_num, serial_char)