from collections import deque
from enum import Enum
import struct
import threading
import time
import traceback
from typing import NamedTuple
from bluepy.btle import BTLEDisconnectError, DefaultDelegate, Peripheral
import anycrc

# Constants
INITIAL_SEQ_NUM = 0
ERROR_VALUE = -1
BLE_TIMEOUT = 0.25
PACKET_SIZE = 20
PACKET_TYPE_ID_LENGTH = 4
PACKET_FORMAT = "=BH16sB"
BITS_PER_BYTE = 8
LOWER_4BITS_MASK = 0x0f
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
    "F4:B8:5E:42:6D:75",
    "F4:B8:5E:42:67:6E",
    "B4:99:4C:89:1B:FD"
]
## BLE GATT
GATT_SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
GATT_SERIAL_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

# Packet Type ID
class PacketType(Enum):
    HELLO = 0
    ACK = 1
    NACK = 2
    P1_IMU = 3
    P1_IR_RECV = 4
    P1_IR_TRANS = 5
    P2_IMU = 6
    P2_IR_RECV = 7
    P2_IR_TRANS = 8
    GAME_STAT = 9

class BlePacket(NamedTuple):
    metadata: int
    seq_num: int
    data: bytearray
    crc: int

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
                print("{}Fragmented packet received{}".format(bcolors.WARNING, bcolors.ENDC))
            for dataByte in data:
                if self.isHeaderByte(dataByte) or len(self.dataBuffer) > 0:
                    self.dataBuffer.append(dataByte)
                else:
                    print("Dropping byte {}".format(dataByte))
        except Exception as exc:
            traceback.print_exception(exc)
    
    def isHeaderByte(self, dataByte):
        packet_id = dataByte & LOWER_4BITS_MASK
        return packet_id <= PacketType.GAME_STAT.value and packet_id >= PacketType.HELLO.value

class Beetle(threading.Thread):
    def __init__(self, beetle_mac_addr, color = bcolors.OKGREEN):
        super().__init__()
        self.beetle_mac_addr = beetle_mac_addr
        self.mBeetle = Peripheral()
        self.color = color
        # Runtime variables
        self.mDataBuffer = deque()
        self.hasHandshake = False
        self.seq_num = 0
        self.sendHelloTime = 0
        self.mRecvTime = 0
        self.fragmentedCount = 0
        self.lastPacketSent = None
        self.terminateEvent = threading.Event()
        self.mService = None
        self.serial_char = None
        # Configure Peripheral
        self.mBeetle.withDelegate(BlePacketDelegate(self.serial_char, self.mDataBuffer))

    def connect(self):
        if not self.terminateEvent.is_set():
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
                if not self.hasHandshake:
                    # Perform 3-way handshake
                    self.doHandshake()
                # Handshake already completed
                elif self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                    mRecvTime = time.time()
                    if len(self.mDataBuffer) < PACKET_SIZE:
                        self.fragmentedCount += 1
                        continue
                    # bytearray for 20-byte packet
                    packetBytes = self.checkReceiveBuffer(self.mDataBuffer)
                    if not self.isValidPacket(packetBytes):
                        # TODO: Figure out what seq num to send
                        self.lastPacketSent = self.sendNack(self.seq_num)
                        continue
                    # assert packetBytes is a valid 20-byte packet
                    # Parse packet from 20-byte
                    packet_id, seq_num, data = self.parsePacket(packetBytes)
                    if data and (len(data) > 0):
                        # Packet is valid
                        if packet_id == PacketType.NACK.value:
                            self.mPrint2("Received NACK from {}, resending last packet".format(self.beetle_mac_addr))
                            self.sendPacket(self.lastPacketSent)
                        elif packet_id != PacketType.ACK.value:
                            # Packet is not ACK, so we ACK the packet
                            self.lastPacketSent = self.sendAck(self.seq_num)
                        else:
                            # Received ACK packet, increment seq num
                            self.seq_num += 1
            
            except Exception as exc:
                traceback.print_exception(exc)
                self.reconnect()
                self.main()
        self.disconnect()

    def doHandshake(self):
        mHasSentHello = False
        mSentHelloTime = time.time()
        mSynTime = time.time()
        mSeqNum = INITIAL_SEQ_NUM
        mLastPacketSent = None
        while not self.hasHandshake:
            # Send HELLO
            if not mHasSentHello:
                mLastPacketSent = self.sendHello(mSeqNum)
                mSentHelloTime = time.time()
                mHasSentHello = True
            else:
                hasAck = False
                # Wait for Beetle to ACK
                while not hasAck:
                    if (time.time() - mSentHelloTime) >= BLE_TIMEOUT:
                        # Handle BLE timeout for HELLO
                        mLastPacketSent = self.sendHello(mSeqNum)
                        mSentHelloTime = time.time()
                    # Has not timed out yet, wait for ACK from Beetle
                    if self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                        if len(self.mDataBuffer) < PACKET_SIZE:
                            self.fragmentedCount += 1
                            continue
                        # bytearray for 20-byte packet
                        packetBytes = self.checkReceiveBuffer(self.mDataBuffer)
                        if not self.isValidPacket(packetBytes):
                            # Restart handshake since Beetle sent invalid packet
                            mLastPacketSent = self.sendNack(mSeqNum)
                            self.mPrint2(inputString = "Invalid packet received from {}, expected ACK".format(self.beetle_mac_addr))
                            continue
                        # assert packetBytes is a valid 20-byte packet
                        # Parse packet
                        packet_id, beetle_seq_num, data = self.parsePacket(packetBytes)
                        if packet_id == PacketType.ACK.value:
                            # Beetle has ACKed the HELLO
                            mSeqNum += 1
                            # TODO: Implement using SYN+ACK to synchronise seq num with Beetle
                            # Send a SYN+ACK back to Beetle
                            self.mPrint2("Sending SYN+ACK to {}".format(self.beetle_mac_addr))
                            mLastPacketSent = self.sendAck(mSeqNum)
                            mSynTime = time.time()
                            hasAck = True
                        elif packet_id == PacketType.NACK.value:
                            self.sendPacket(mLastPacketSent)
                # Just in case Beetle NACK the SYN+ACK, we want to retransmit
                while (time.time() - mSynTime) < BLE_TIMEOUT:
                    # Wait for incoming packets
                    if self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                        if len(self.mDataBuffer) < PACKET_SIZE:
                            self.fragmentedCount += 1
                            continue
                        # bytearray for 20-byte packet
                        packetBytes = self.checkReceiveBuffer(self.mDataBuffer)
                        if not self.isValidPacket(packetBytes):
                            # Inform Beetle that incoming packet is corrupted
                            self.mPrint2("Invalid packet received from {}".format(self.beetle_mac_addr))
                            mLastPacketSent = self.sendNack(self.getSeqNumFrom(packetBytes))
                            continue
                        # Parse packet
                        packet_id, beetle_seq_num, data = self.parsePacket(packetBytes)
                        if packet_id == PacketType.NACK.value:
                            # SYN+ACK not received by Beetle, resend a SYN+ACK
                            self.mPrint2("Received NACK from {}, resending SYN+ACK".format(self.beetle_mac_addr))
                            #mLastPacketSent = self.sendAck(mSeqNum)
                            self.sendPacket(mLastPacketSent)
                            # Update mSynTime to wait for any potential NACK from Beetle again
                            mSynTime = time.time()
                # No NACK during timeout period, Beetle is assumed to have received SYN+ACK
                self.hasHandshake = True
                self.mPrint2(inputString = "Handshake completed with {}".format(self.beetle_mac_addr))

    def run(self):
        self.connect()
        self.main()

    def checkReceiveBuffer(self, receiveBuffer):
        if len(receiveBuffer) >= PACKET_SIZE:
            # bytearray for 20-byte packet
            dataPacket = bytearray()
            # Read 20 bytes from input buffer
            for i in range(0, PACKET_SIZE):
                dataPacket.append(receiveBuffer.popleft())
            if self.isValidPacket(dataPacket):
                return dataPacket
            return bytearray()
        else:
            return bytearray()
        
    def createPacket(self, packet_id, seq_num, data):
        # TODO: Avoid hardcoding this value
        data_length = 16
        num_padding_bytes = 0
        if (len(data) < data_length):
            num_padding_bytes, data = self.addPaddingBytes(data, data_length)
        metadata = packet_id + (num_padding_bytes << PACKET_TYPE_ID_LENGTH)
        dataCrc = self.getCrcOf(metadata, seq_num, data)
        packet = struct.pack(PACKET_FORMAT, metadata, seq_num, data, dataCrc)
        return packet

    def getCrcOf(self, metadata, seq_num, data):
        crc8 = anycrc.Model('CRC8-SMBUS')
        crc8.update(metadata.to_bytes())
        crc8.update(seq_num.to_bytes(length = 2, byteorder = 'little'))
        dataCrc = crc8.update(data)
        return dataCrc

    def getDataFrom(self, dataBytes):
        x1 = self.parseData(dataBytes[0], dataBytes[1])
        y1 = self.parseData(dataBytes[2], dataBytes[3])
        z1 = self.parseData(dataBytes[4], dataBytes[5])
        x2 = self.parseData(dataBytes[6], dataBytes[7])
        y2 = self.parseData(dataBytes[8], dataBytes[9])
        z2 = self.parseData(dataBytes[10], dataBytes[11])
        return x1, y1, z1, x2, y2, z2
    
    def getPacketFrom(self, packetBytes):
        metadata, seq_num, data, dataCrc = struct.unpack(PACKET_FORMAT, packetBytes)
        return metadata, seq_num, data, dataCrc
    
    def getSeqNumFrom(self, packetBytes):
        seq_num = packetBytes[1] + (packetBytes[2] << BITS_PER_BYTE)
        return seq_num
    
    def isHeaderByte(self, dataByte):
        return dataByte <= PacketType.GAME_STAT.value and dataByte >= PacketType.HELLO.value
    
    def isValidPacket(self, given_packet):
        if self.hasValidPacketType(given_packet):
            # Packet type is valid, now check CRC next
            metadata, seq_num, data, received_crc = self.getPacketFrom(given_packet)
            computed_crc = self.getCrcOf(metadata, seq_num, data)
            if computed_crc == received_crc:
                # CRC is valid, packet is not corrupted
                return True
            else:
                print("CRC8 not match: received {} but expected {} for packet {}".format(received_crc, computed_crc, given_packet))
        else:
            # Invalid packet type received
            self.mPrint(bcolors.WARNING, 
                        inputString = "Invalid packet type ID received: {}".format(
                            self.getPacketTypeIdOf(given_packet)))
        return False
    
    def parseData(self, byte1, byte2):
        return (byte1 + (byte2 << BITS_PER_BYTE)) / 100.0
        
    def parsePacket(self, packetBytes):
        # Check for NULL packet or incomplete packet
        if not packetBytes or len(packetBytes) < PACKET_SIZE:
            return ERROR_VALUE, ERROR_VALUE, None
        self.mPrint2(inputString = "{} has new packet: {}".format(self.beetle_mac_addr, packetBytes))
        if not self.isValidPacket(packetBytes):
            return ERROR_VALUE, ERROR_VALUE, None
        metadata, seq_num, data, dataCrc = self.getPacketFrom(packetBytes)
        packet_id = self.metadataToPacketType(metadata)
        return packet_id, seq_num, data

    def sendHello(self, seq_num):
        HELLO = "HELLO"
        hello_packet = self.createPacket(PacketType.HELLO.value, seq_num, bytes(HELLO, encoding = 'ascii'))
        self.mPrint2("Sending HELLO to {}".format(self.beetle_mac_addr))
        self.sendPacket(hello_packet)
        return hello_packet

    def sendAck(self, seq_num):
        ACK = "SYNACK"
        ack_packet = self.createPacket(PacketType.ACK.value, seq_num, bytes(ACK, encoding = "ascii"))
        self.sendPacket(ack_packet)
        return ack_packet

    def sendNack(self, seq_num):
        NACK = "NACK"
        nack_packet = self.createPacket(PacketType.NACK.value, seq_num, bytes(NACK, encoding = "ascii"))
        self.sendPacket(nack_packet)
        return nack_packet

    def sendPacket(self, packet):
        self.serial_char.write(packet)

    def addPaddingBytes(self, data, target_len):
        num_padding_bytes = target_len - len(data)
        result = bytearray(data)
        for i in range(0, num_padding_bytes):
            result.append(num_padding_bytes)
        return num_padding_bytes, result
    
    def getPacketTypeIdOf(self, packet):
        packet_id = packet[0] & LOWER_4BITS_MASK
        return packet_id

    def metadataToPacketType(self, metadata):
        return metadata & LOWER_4BITS_MASK
    
    def isValidPacketType(self, packet_type_id):
        return packet_type_id <= PacketType.GAME_STAT.value and packet_type_id >= PacketType.HELLO.value

    def hasValidPacketType(self, packet):
        return self.isValidPacketType(self.getPacketTypeIdOf(packet))

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
    except KeyboardInterrupt:
        for mBeetle in beetles:
            mBeetle.quit()