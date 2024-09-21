from collections import deque
from enum import Enum
import struct
import threading
import time
from bluepy.btle import BTLEDisconnectError, DefaultDelegate, Peripheral
import anycrc

# Constants
INITIAL_SEQ_NUM = 0
ERROR_VALUE = -1
BLE_TIMEOUT = 0.25
PACKET_SIZE = 20
PACKET_FORMAT = "=BH16sB"
BITS_PER_BYTE = 8
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
    "F4:B8:5E:42:6D:75",
    "F4:B8:5E:42:67:6E"
]
## BLE GATT
GATT_SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
GATT_SERIAL_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

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
        self.dataBuffer = dataBuffer
        self.serial_char = serial_char

    # Bluno Beetle uses cHandle 37
    def handleNotification(self, cHandle, data):
        try:
            # Add incoming bytes to receive buffer
            if len(data) < PACKET_SIZE:
                self.mPrint(bcolors.WARNING, "Fragmented packet received")
            for dataByte in data:
                if self.isHeaderByte(dataByte) or len(self.dataBuffer) > 0:
                    self.dataBuffer.append(dataByte)
                else:
                    print("Dropping byte {}".format(dataByte))
        except Exception as err:
            print(err)
    
    def isHeaderByte(self, dataByte):
        return dataByte <= PacketType.GAME_STAT.value and dataByte >= PacketType.HELLO.value

class Beetle(threading.Thread):
    def __init__(self, beetle_mac_addr, color = bcolors.OKGREEN):
        super().__init__()
        self.beetle_mac_addr = beetle_mac_addr
        self.mBeetle = Peripheral()
        self.color = color
        # Runtime variables
        self.mDataBuffer = deque()
        self.hasHandshake = False
        self.hasSentHello = False
        self.seq_num = 0
        self.sendHelloTime = 0
        self.mRecvTime = 0
        self.fragmentedCount = 0
        self.terminateEvent = threading.Event()
        self.mService = None
        self.serial_char = None
        # Configure Peripheral
        self.mBeetle.withDelegate(BlePacketDelegate(self.serial_char, self.mDataBuffer))

    def connect(self):
        # Connect to Beetle
        try:
            self.mPrint(bcolors.WARNING, "Connecting to {}".format(self.beetle_mac_addr))
            self.mBeetle.connect(self.beetle_mac_addr)
            self.mService = self.mBeetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
            self.serial_char = self.mService.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
        except BTLEDisconnectError as disconnectErr:
            print(disconnectErr)
            self.mDataBuffer.clear()
            # Keep trying to connect again
            self.connect()

    def disconnect(self):
        self.mPrint(bcolors.WARNING, "Disconnecting {}".format(self.beetle_mac_addr))
        self.mBeetle.disconnect()
        self.mDataBuffer.clear()
        self.hasHandshake = False

    def reconnect(self):
        self.mPrint(bcolors.WARNING, "Performing reconnect of {}".format(self.beetle_mac_addr))
        self.disconnect()
        time.sleep(BLE_TIMEOUT)
        self.connect()

    def isConnected(self):
        return self.hasHandshake

    def quit(self):
        self.mPrint(bcolors.WARNING, "Quitting {}".format(self.beetle_mac_addr))
        self.mPrint(bcolors.OKCYAN, "{}: {} fragmented packets".format(self.beetle_mac_addr, self.fragmentedCount))
        self.terminateEvent.set()

    def mPrint2(self, inputString):
        self.mPrint(self.color, inputString)

    def mPrint(self, color, inputString):
        print("{}{}{}".format(color, inputString, bcolors.ENDC))

    def main(self):
        while not self.terminateEvent.is_set():
            try:
                # Send HELLO
                if (not self.hasHandshake) and (not self.hasSentHello):
                    self.sendHelloTime = time.time()
                    self.sendHello(INITIAL_SEQ_NUM, self.serial_char)
                    self.hasSentHello = True
                # Handle HELLO timeout
                elif (not self.hasHandshake) and self.hasSentHello and (time.time() - self.sendHelloTime) >= BLE_TIMEOUT:
                    self.hasSentHello = False
                    continue
                # Check for ACK to HELLO
                if self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                    if len(self.mDataBuffer) < PACKET_SIZE:
                        self.fragmentedCount += 1
                    mRecvTime = time.time()
                    # bytearray for 20-byte packet
                    packetBytes = self.checkReceiveBuffer(self.mDataBuffer)
                    # Parse packet from 20-byte
                    packet_id, seq_num, data = self.parsePacket(packetBytes)
                    if data and (len(data) > 0):
                        if not self.hasHandshake:
                            # Send SYN+ACK
                            if packet_id == PacketType.ACK.value:
                                self.sendAck(seq_num, self.serial_char)
                                self.hasHandshake = True
                        else:
                            if packet_id != PacketType.ACK.value:
                                self.sendAck(seq_num, self.serial_char)
            
            except Exception as err:
                print(err)
                self.reconnect()
                self.main()
        self.disconnect()

    def run(self):
        self.connect()
        self.main()

    def isHeaderByte(self, dataByte):
        return dataByte <= PacketType.GAME_STAT.value and dataByte >= PacketType.HELLO.value
    
    def isValidPacket(self, dataPacket):
        return True

    def checkReceiveBuffer(self, receiveBuffer):
        if len(receiveBuffer) >= PACKET_SIZE:
            # Fetch 1 20-byte packet from the buffer
            dataPacket = bytearray([receiveBuffer.popleft()])
            # Remove the packet from the buffer
            count = 0
            while not self.isHeaderByte(dataPacket[0]) and count < PACKET_SIZE:
                dataPacket.append(receiveBuffer.popleft())
                count += 1
            if count == PACKET_SIZE:
                if self.isValidPacket(dataPacket):
                    return dataPacket
                return bytearray()
            for i in range(PACKET_SIZE - 1):
                dataByte = receiveBuffer.popleft()
                # Do we need this check below?
                """ if isHeaderByte(dataByte):
                    break """
                dataPacket.append(dataByte)
            if not self.isValidPacket(dataPacket):
                return bytearray()
            return dataPacket
        else:
            return bytearray()
        
    def createPacket(self, packet_id, seq_num, data):
        dataCrc = self.getCrcOf(packet_id, seq_num, data)
        packet = struct.pack(PACKET_FORMAT, packet_id, seq_num, data, dataCrc)
        return packet

    def getCrcOf(self, packet_id, seq_num, data):
        crc8 = anycrc.Model('CRC8-SMBUS')
        crc8.update(packet_id.to_bytes())
        crc8.update(seq_num.to_bytes(length = 2, byteorder = 'little'))
        dataCrc = crc8.update(data)
        return dataCrc
    
    def getPacketFrom(self, packetBytes):
        packet_id, seq_num, data, dataCrc = struct.unpack(PACKET_FORMAT, packetBytes)
        return packet_id, seq_num, data, dataCrc
    
    def parseData(self, byte1, byte2):
        return int.from_bytes(byte1, byteorder='little') + (int.from_bytes(byte2, byteorder='little') << BITS_PER_BYTE) / 100.0

    def getDataFrom(self, dataBytes):
        x1 = self.parseData(dataBytes[0], dataBytes[1])
        y1 = self.parseData(dataBytes[2], dataBytes[3])
        z1 = self.parseData(dataBytes[4], dataBytes[5])
        x2 = self.parseData(dataBytes[6], dataBytes[7])
        y2 = self.parseData(dataBytes[8], dataBytes[9])
        z2 = self.parseData(dataBytes[10], dataBytes[11])
        return x1, y1, z1, x2, y2, z2
        
    def parsePacket(self, packetBytes):
        # Check for NULL packet
        if not packetBytes:
            return ERROR_VALUE, ERROR_VALUE, None
        #print("{}{} has New packet: {}{}".format(bcolors.OKGREEN, self.beetle_mac_addr, packetBytes, bcolors.ENDC))
        self.mPrint2(inputString = "{} has new packet: {}".format(self.beetle_mac_addr, packetBytes))
        # packet_id = packetBytes[0]
        packet_id, seq_num, data, dataCrc = self.getPacketFrom(packetBytes)
        computedCrc = self.getCrcOf(packet_id, seq_num, data)
        if dataCrc != computedCrc:
            print("CRC8 not match: {} vs {}".format(dataCrc, computedCrc))
        """ if packet_id == PacketType.P1_IMU.value or packet_id == PacketType.P2_IMU.value:
            #self.mPrint(bcolors.OKGREEN, "IMU data: [{}, {}, {}], [{}, {}, {}]".format(data[0:1]))
            print(struct.unpack('H', bytearray(data[0:1])))
        else:
            self.mPrint(bcolors.OKGREEN, "New packet: {}".format(packetBytes)) """
        return packet_id, seq_num, data

    def sendHello(self, seq_num, serial_char):
        HELLO = "HELLO"
        hello_packet = self.createPacket(PacketType.HELLO.value, seq_num, bytes(HELLO, encoding = 'ascii'))
        print("Sending HELLO: {}".format(hello_packet))
        serial_char.write(hello_packet)

    def sendAck(self, seq_num, serial_char):
        SYNACK = "SYNACK"
        syn_ack_packet = self.createPacket(PacketType.ACK.value, seq_num, bytes(SYNACK, encoding = "ascii"))
        serial_char.write(syn_ack_packet)

if __name__=="__main__":
    beetles = []
    colors = [bcolors.OKGREEN, bcolors.OKCYAN, bcolors.FAIL]
    try:
        index = 0
        for beetle_addr in BLUNO_MAC_ADDR_LIST:
            thisBeetle = Beetle(beetle_addr, colors[index])
            thisBeetle.start()
            beetles.append(thisBeetle)
            index += 1
        for thisBeetle in beetles:
            thisBeetle.join()
    except KeyboardInterrupt as err:
        for mBeetle in beetles:
            mBeetle.quit()
