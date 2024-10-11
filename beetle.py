from collections import deque
import struct
import threading
import time
import traceback
import anycrc
from ble_delegate import BlePacketDelegate
from internal_utils import BITS_PER_BYTE, BLE_TIMEOUT, ERROR_VALUE, GATT_SERIAL_CHARACTERISTIC_UUID, GATT_SERIAL_SERVICE_UUID, INITIAL_SEQ_NUM, MAX_SEQ_NUM, PACKET_DATA_SIZE, PACKET_FORMAT, PACKET_SIZE, PACKET_TYPE_ID_LENGTH, BlePacket, BlePacketType, GunPacket, ImuPacket, VestPacket, bcolors, get_player_id_for, metadata_to_packet_type
import external_utils
from bluepy.btle import BTLEException, Peripheral

class Beetle(threading.Thread):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__()
        self.beetle_mac_addr = beetle_mac_addr
        self.mBeetle = Peripheral()
        self.color = color
        self.terminateEvent = threading.Event()
        # Runtime variables
        self.hasHandshake = False
        ## Receiver variables
        self.mDataBuffer = deque()
        self.mService = None
        self.serial_char = None
        self.start_transmit_time = 0
        ### Sequence number for packets created by Beetle to send to laptop
        self.receiver_seq_num = INITIAL_SEQ_NUM
        self.num_packets_received = 0
        self.outgoing_queue = outgoing_queue
        ## Sender variables
        self.is_waiting_for_ack = False
        self.lastPacketSent = None
        self.lastPacketSentTime = -1
        ### Sequence number for packets created by laptop to send to Beetle
        self.sender_seq_num = INITIAL_SEQ_NUM
        self.incoming_queue = incoming_queue
        # Configure Peripheral
        self.ble_delegate = BlePacketDelegate(self.serial_char, self.mDataBuffer)
        self.mBeetle.withDelegate(self.ble_delegate)

    def connect(self):
        while not self.terminateEvent.is_set():
            try:
                self.mPrint(bcolors.BRIGHT_YELLOW, "Connecting to {}".format(self.beetle_mac_addr))
                self.mBeetle.connect(self.beetle_mac_addr)
                self.mService = self.mBeetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
                self.serial_char = self.mService.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
                break
            except BTLEException as ble_exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in connect() for Beetle: {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(ble_exc))
                self.mPrint2(stacktrace_str)
                self.mDataBuffer.clear()

    def disconnect(self):
        self.mPrint(bcolors.BRIGHT_YELLOW, "Disconnecting {}".format(self.beetle_mac_addr))
        self.mBeetle.disconnect()
        self.mDataBuffer.clear()
        self.hasHandshake = False

    def reconnect(self):
        self.mPrint(bcolors.BRIGHT_YELLOW, "Performing reconnect of {}".format(self.beetle_mac_addr))
        self.disconnect()
        time.sleep(BLE_TIMEOUT)
        self.connect()

    def isConnected(self):
        return self.hasHandshake

    def quit(self):
        end_transmission_time = time.time()
        transmission_speed = self.num_packets_received / end_transmission_time
        self.terminateEvent.set()
        fragmented_packet_count = self.ble_delegate.get_fragmented_packet_count()
        self.mPrint(bcolors.BRIGHT_YELLOW, "{}: {} fragmented packets"
                .format(self.beetle_mac_addr, fragmented_packet_count))
        self.mPrint(bcolors.BRIGHT_YELLOW, 
                f"""{self.beetle_mac_addr}: Transmission speed {transmission_speed} packets/s""")

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
                # At this point, handshake is now completed
                # Only send packets to Beetle if the previous sent packet has been ACK-ed
                if not self.is_waiting_for_ack and not self.incoming_queue.empty():
                    # Send outgoing packet to Beetle
                    ext_packet = self.incoming_queue.get()
                    self.mPrint2(f"""Received packet from external comms: {ext_packet}""")
                    self.handle_ext_packet(ext_packet)
                elif self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                    if len(self.mDataBuffer) < PACKET_SIZE:
                        continue
                    # bytearray for 20-byte packet
                    packetBytes = self.get_packet_from(self.mDataBuffer)
                    if not self.isValidPacket(packetBytes):
                        self.sendNack(self.receiver_seq_num)
                        continue
                    # assert packetBytes is a valid 20-byte packet
                    # Keep track of packets received
                    self.num_packets_received += 1
                    # Parse packet from 20-byte
                    receivedPacket = self.parsePacket(packetBytes)
                    if not receivedPacket.data or (len(receivedPacket.data) == 0):
                        self.mPrint(bcolors.BRIGHT_YELLOW, "Error while parsing packet from {}"
                                .format(self.beetle_mac_addr))
                        continue
                    packet_id = self.getPacketTypeOf(receivedPacket)
                    if packet_id == BlePacketType.NACK.value:
                        if self.receiver_seq_num != receivedPacket.seq_num:
                            self.receiver_seq_num = receivedPacket.seq_num
                        elif metadata_to_packet_type(self.lastPacketSent[0]) != BlePacketType.ACK.value:
                            self.mPrint(bcolors.BRIGHT_YELLOW, "Received NACK with seq_num {} from {}, resending last packet"
                                    .format(receivedPacket.seq_num, self.beetle_mac_addr))
                            self.sendPacket(self.lastPacketSent)
                    elif packet_id != BlePacketType.ACK.value and not self.terminateEvent.is_set():
                        if self.receiver_seq_num > receivedPacket.seq_num:
                            # ACK for earlier packet was lost, synchronise seq num with Beetle
                            self.receiver_seq_num = receivedPacket.seq_num
                            self.mPrint(bcolors.BRIGHT_YELLOW, "ACK for packet num {} lost, synchronising seq num with {}"
                                    .format(receivedPacket.seq_num, self.beetle_mac_addr))
                        """ elif self.receiver_seq_num < receivedPacket.seq_num:
                            self.lastPacketSent = self.sendNack(receivedPacket.seq_num)
                            self.mPrint(bcolors.BRIGHT_YELLOW, "Received packet with seq num {} from {}, expected seq num {}"
                                    .format(receivedPacket.seq_num, self.beetle_mac_addr, self.receiver_seq_num))
                            continue """
                        # ACK the received packet
                        self.sendAck(self.receiver_seq_num)
                        if self.receiver_seq_num == MAX_SEQ_NUM:
                            # On the Beetle, seq num is 16-bit and overflows. So we 'overflow' by
                            #   resetting to 0 to synchronise with the Beetle
                            self.receiver_seq_num = 0
                        else:
                            # Increment seq_num since received packet is valid
                            self.receiver_seq_num += 1
                        # TODO: Insert data into outgoing ext comms queue
                        self.handle_beetle_packet(receivedPacket)
            except BTLEException as ble_exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in connect() for Beetle: {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(ble_exc))
                self.mPrint2(stacktrace_str)
                self.reconnect()
            except Exception as exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in main() of {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(exc))
                self.mPrint2(stacktrace_str)
        self.disconnect()

    def handle_beetle_packet(self, beetle_packet):
        pass

    def handle_ext_packet(self, ext_packet):
        pass

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
                            continue
                        # bytearray for 20-byte packet
                        packetBytes = self.get_packet_from(self.mDataBuffer)
                        if not self.isValidPacket(packetBytes):
                            # Restart handshake since Beetle sent invalid packet
                            mLastPacketSent = self.sendNack(mSeqNum)
                            self.mPrint(bcolors.BRIGHT_YELLOW, inputString = "Invalid packet received from {}, expected ACK"
                                    .format(self.beetle_mac_addr))
                            continue
                        # assert packetBytes is a valid 20-byte packet
                        # Parse packet
                        receivedPacket = self.parsePacket(packetBytes)
                        packet_id = self.getPacketTypeOf(receivedPacket)
                        if packet_id == BlePacketType.ACK.value:
                            # Beetle has ACKed the HELLO
                            mSeqNum += 1
                            receivedPacket = self.parsePacket(packetBytes)
                            beetle_seq_num = receivedPacket.data[0] + (receivedPacket.data[1] << BITS_PER_BYTE)
                            self.receiver_seq_num = beetle_seq_num
                            # Send a SYN+ACK back to Beetle
                            mLastPacketSent = self.sendSynAck(mSeqNum, beetle_seq_num)
                            mSynTime = time.time()
                            hasAck = True
                        elif packet_id == BlePacketType.NACK.value:
                            self.sendPacket(mLastPacketSent)
                # Just in case Beetle NACK the SYN+ACK, we want to retransmit
                while (time.time() - mSynTime) < BLE_TIMEOUT:
                    # Wait for incoming packets
                    if self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                        if len(self.mDataBuffer) < PACKET_SIZE:
                            continue
                        # bytearray for 20-byte packet
                        packetBytes = self.get_packet_from(self.mDataBuffer)
                        if not self.isValidPacket(packetBytes):
                            # Inform Beetle that incoming packet is corrupted
                            self.mPrint(bcolors.BRIGHT_YELLOW, "Invalid packet received from {}"
                                    .format(self.beetle_mac_addr))
                            mLastPacketSent = self.sendNack(self.getSeqNumFrom(packetBytes))
                            continue
                        # Parse packet
                        receivedPacket = self.parsePacket(packetBytes)
                        packet_id = self.getPacketTypeOf(receivedPacket)
                        if packet_id == BlePacketType.NACK.value:
                            # SYN+ACK not received by Beetle, resend a SYN+ACK
                            self.mPrint(bcolors.BRIGHT_YELLOW, "Received NACK from {}, resending SYN+ACK"
                                    .format(self.beetle_mac_addr))
                            self.sendPacket(mLastPacketSent)
                            # Update mSynTime to wait for any potential NACK from Beetle again
                            mSynTime = time.time()
                # No NACK during timeout period, Beetle is assumed to have received SYN+ACK
                if self.start_transmit_time == 0:
                    # Set the time of 1st completion of 3-way handshake so we can compute transmission speed
                    self.start_transmit_time = time.time()
                self.hasHandshake = True
                self.mPrint2(inputString = "Handshake completed with {}".format(self.beetle_mac_addr))

    def run(self):
        self.connect()
        self.main()

    def addPaddingBytes(self, data, target_len):
        num_padding_bytes = target_len - len(data)
        result = bytearray(data)
        for i in range(0, num_padding_bytes):
            result.append(num_padding_bytes)
        return num_padding_bytes, result

    """
        receivedBuffer assumed to have a valid 20-byte packet if it has at least 20 bytes
    """
    def get_packet_from(self, receiveBuffer):
        if len(receiveBuffer) >= PACKET_SIZE:
            # bytearray for 20-byte packet
            packet = bytearray()
            # Read 20 bytes from input buffer
            for i in range(0, PACKET_SIZE):
                packet.append(receiveBuffer.popleft())
            self.mPrint2("{} has new packet: {}".format(self.beetle_mac_addr, packet))
            return packet
        else:
            return bytearray()
        
    def createPacket(self, packet_id, seq_num, data):
        data_length = PACKET_DATA_SIZE
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
    
    def getPacketTypeOf(self, blePacket):
        return metadata_to_packet_type(blePacket.metadata)
    
    def getSeqNumFrom(self, packetBytes):
        seq_num = packetBytes[1] + (packetBytes[2] << BITS_PER_BYTE)
        return seq_num
    
    def isValidPacket(self, given_packet):
        metadata, seq_num, data, received_crc = self.unpack_packet_bytes(given_packet)
        packet_type = metadata_to_packet_type(metadata)
        if self.isValidPacketType(packet_type):
            # Packet type is valid, now check CRC next
            computed_crc = self.getCrcOf(metadata, seq_num, data)
            if computed_crc == received_crc:
                # CRC is valid, packet is not corrupted
                return True
            # computed_crc != received_crc
            print("CRC8 not match: received {} but expected {} for packet {}".format(received_crc, computed_crc, given_packet))
            return False
        # Invalid packet type received
        self.mPrint(bcolors.BRIGHT_YELLOW, 
                inputString = "Invalid packet type ID received: {}".format(
                    self.getPacketTypeIdOf(given_packet)))
        return False
    
    def isValidPacketType(self, packet_type_id):
        return packet_type_id <= BlePacketType.GAME_STAT.value and packet_type_id >= BlePacketType.HELLO.value
    
    def parseData(self, byte1, byte2):
        return (byte1 + (byte2 << BITS_PER_BYTE)) / 100.0
        
    """
        packetBytes assumed to be a valid 20-byte packet
    """
    def parsePacket(self, packetBytes):
        # Check for NULL packet or incomplete packet
        if not packetBytes or len(packetBytes) < PACKET_SIZE:
            return BlePacket(ERROR_VALUE, ERROR_VALUE, None, ERROR_VALUE)
        metadata, seq_num, data, dataCrc = self.unpack_packet_bytes(packetBytes)
        packet = BlePacket(metadata, seq_num, data, dataCrc)
        return packet

    def sendHello(self, seq_num):
        HELLO = "HELLO"
        hello_packet = self.createPacket(BlePacketType.HELLO.value, seq_num, bytes(HELLO, encoding = 'ascii'))
        self.mPrint2("Sending HELLO to {}".format(self.beetle_mac_addr))
        self.sendPacket(hello_packet)
        return hello_packet

    def sendAck(self, seq_num):
        ACK = "SYNACK"
        ack_packet = self.createPacket(BlePacketType.ACK.value, seq_num, bytes(ACK, encoding = "ascii"))
        self.sendPacket(ack_packet)
        return ack_packet

    def sendNack(self, seq_num):
        NACK = "NACK"
        nack_packet = self.createPacket(BlePacketType.NACK.value, seq_num, bytes(NACK, encoding = "ascii"))
        self.sendPacket(nack_packet)
        return nack_packet
    
    def sendSynAck(self, my_seq_num, seq_num):
        SYNACK = "SYNACK"
        synack_packet = self.createPacket(BlePacketType.ACK.value, my_seq_num, seq_num.to_bytes(2, byteorder='little') + bytes(SYNACK, encoding = "ascii"))
        self.sendPacket(synack_packet)
        return synack_packet

    def sendPacket(self, packet):
        self.serial_char.write(packet)
    
    def unpack_packet_bytes(self, packetBytes):
        metadata, seq_num, data, data_crc = struct.unpack(PACKET_FORMAT, packetBytes)
        return metadata, seq_num, data, data_crc
   
class GloveBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_beetle_packet(self, beetle_packet):
        x1, y1, z1, x2, y2, z2 = self.getDataFrom(beetle_packet.data)
        internal_imu_packet = ImuPacket(self.beetle_mac_addr, [x1, y1, z1], [x2, y2, z2])
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_imu_packet = external_utils.ImuPacket(player_id, [x1, y1, z1], [x2, y2, z2])
        self.outgoing_queue.put(external_imu_packet)
        # TODO: Stop printing debug line below
        self.mPrint2("Received IMU data from {}: [{}, {}, {}, {}, {}, {}]"
                .format(self.beetle_mac_addr, x1, y1, z1, x2, y2, z2))

class GunBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_beetle_packet(self, beetle_packet):
        gun_boolean = beetle_packet.data[0] == 1
        internal_gun_packet = GunPacket(self.beetle_mac_addr, gun_boolean)
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_gun_packet = external_utils.GunPacket(player_id, gun_boolean)
        self.outgoing_queue.put(external_gun_packet)
        self.mPrint2("Received gun packet from {}: {}".format(self.beetle_mac_addr, internal_gun_packet))

class VestBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_beetle_packet(self, beetle_packet):
        vest_boolean = beetle_packet.data[0] == 1
        internal_vest_packet = VestPacket(self.beetle_mac_addr, vest_boolean)
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_vest_packet = external_utils.VestPacket(player_id, vest_boolean)
        self.outgoing_queue.put(external_vest_packet)
        self.mPrint2("Received vest packet from {}: {}".format(self.beetle_mac_addr, internal_vest_packet))
