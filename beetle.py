from collections import deque
import struct
import threading
import time
import traceback
import anycrc
from ble_delegate import BlePacketDelegate
from internal_utils import ACC_LSB_SCALE, BITS_PER_BYTE, BLE_TIMEOUT, BLE_WAIT_TIMEOUT, ERROR_VALUE, GATT_SERIAL_CHARACTERISTIC_UUID, GATT_SERIAL_SERVICE_UUID, GYRO_LSB_SCALE, INITIAL_SEQ_NUM, MAX_RETRANSMITS, MAX_SEQ_NUM, PACKET_DATA_SIZE, PACKET_FORMAT, PACKET_SIZE, PACKET_TYPE_ID_LENGTH, BlePacket, BlePacketType, GunPacket, GunUpdatePacket, ImuPacket, VestPacket, VestUpdatePacket, bcolors, get_player_id_for, metadata_to_packet_type
import external_utils
from bluepy.btle import BTLEException, Peripheral

class Beetle(threading.Thread):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__()
        self.beetle_mac_addr = beetle_mac_addr
        self.mBeetle: Peripheral = Peripheral()
        self.color = color
        self.terminateEvent = threading.Event()
        # Runtime variables
        self.hasHandshake = False
        ## Receiver variables
        self.mDataBuffer = deque()
        self.mService = None
        self.serial_char = None
        self.start_transmit_time = 0
        self.num_invalid_packets_received = 0
        ### Sequence number for packets created by Beetle to send to laptop
        self.receiver_seq_num = INITIAL_SEQ_NUM
        self.num_packets_received = 0
        self.outgoing_queue = outgoing_queue
        ## Sender variables
        self.is_waiting_for_ack = False
        self.lastPacketSent = None
        self.lastPacketSentTime = -1
        self.num_retransmits = 0
        ### Sequence number for packets created by laptop to send to Beetle
        self.sender_seq_num = INITIAL_SEQ_NUM
        self.incoming_queue = incoming_queue
        # Configure Peripheral
        self.ble_delegate = BlePacketDelegate(self.mDataBuffer)
        self.mBeetle.withDelegate(self.ble_delegate)
        # Verbose printing
        self.is_verbose_printing = False

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
            except KeyboardInterrupt as exc:
                # Catch and rethrow the exception so that caller can handle CTRL+C
                raise exc

    def disconnect(self):
        self.mPrint(bcolors.BRIGHT_YELLOW, "Disconnecting {}".format(self.beetle_mac_addr))
        self.mBeetle.disconnect()
        # self.clear_state()
        self.mDataBuffer.clear()
        self.hasHandshake = False
        self.num_retransmits = 0
        self.num_invalid_packets_received = 0

    def reconnect(self):
        self.mPrint(bcolors.BRIGHT_YELLOW, "Performing reconnect of {}".format(self.beetle_mac_addr))
        self.disconnect()
        time.sleep(BLE_TIMEOUT)
        self.connect()

    def isConnected(self):
        return self.hasHandshake

    def quit(self):
        end_transmission_time = time.time()
        total_transmission_time = end_transmission_time - self.start_transmit_time
        transmission_speed = self.num_packets_received / total_transmission_time
        self.terminateEvent.set()
        fragmented_packet_count = self.ble_delegate.get_fragmented_packet_count()
        self.mPrint(bcolors.BRIGHT_YELLOW, "{}: {} fragmented packets"
                .format(self.beetle_mac_addr, fragmented_packet_count))
        self.mPrint(bcolors.BRIGHT_YELLOW, 
                f"""{self.beetle_mac_addr}: Transmission speed {transmission_speed} packets/s""")
        self.mPrint(bcolors.BRIGHT_YELLOW, f"""{self.beetle_mac_addr}: {total_transmission_time}s of duration""")

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
                    packet_to_send = self.handle_ext_packet(ext_packet)
                    if packet_to_send is not None:
                        self.sendPacket(packet_to_send)
                        self.lastPacketSentTime = time.time()
                        self.lastPacketSent = packet_to_send
                        self.is_waiting_for_ack = True
                elif self.is_waiting_for_ack and (time.time() - self.lastPacketSentTime) >= BLE_TIMEOUT:
                    if self.num_retransmits == MAX_RETRANSMITS:
                        # Max retransmits reached, stop trying to retransmit
                        self.mPrint(bcolors.BRIGHT_YELLOW, 
                                f"""Max retransmits reached for {self.beetle_mac_addr}, dropping packet""")
                        self.is_waiting_for_ack = False
                        self.lastPacketSent = None
                        self.num_retransmits = 0
                    else:
                        # Timeout occurred, retransmit last sent packet
                        self.mPrint(bcolors.BRIGHT_YELLOW, 
                                f"""Timeout on {self.beetle_mac_addr}, retransmitting last packet sent""")
                        self.sendPacket(self.lastPacketSent)
                        self.lastPacketSentTime = time.time()  
                        self.num_retransmits += 1  
                elif self.mBeetle.waitForNotifications(BLE_WAIT_TIMEOUT):
                    if len(self.mDataBuffer) < PACKET_SIZE:
                        continue
                    # bytearray for 20-byte packet
                    packetBytes = self.get_packet_from(self.mDataBuffer)
                    if not self.isValidPacket(packetBytes):
                        self.mPrint(bcolors.BRIGHT_YELLOW, 
                                "Invalid packet received from {}, requesting retransmission".format(self.beetle_mac_addr))
                        self.num_invalid_packets_received += 1
                        if (self.num_invalid_packets_received == MAX_RETRANSMITS):
                            self.num_invalid_packets_received = 0
                            self.mPrint(bcolors.BRIGHT_YELLOW, 
                                    f"""ERROR: Max retransmits reached for {self.beetle_mac_addr}, resetting""")
                            self.reconnect()
                            continue
                        self.sendNack(self.receiver_seq_num)
                        continue
                    # assert packetBytes is a valid 20-byte packet
                    # Keep track of packets received
                    self.num_packets_received += 1
                    # Parse packet from 20-byte
                    receivedPacket = self.parsePacket(packetBytes)
                    self.handle_beetle_packet(receivedPacket)
            except BTLEException as ble_exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Bluetooth exception in main() for Beetle: {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(ble_exc))
                self.mPrint2(stacktrace_str)
                self.reconnect()
            except KeyboardInterrupt as exc:
                # Catch and rethrow the exception so that caller can handle CTRL+C
                raise exc
            except Exception as exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in main() of {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(exc))
                self.mPrint2(stacktrace_str)
        self.disconnect()

    def handle_beetle_packet(self, incoming_packet):
        packet_id = self.getPacketTypeOf(incoming_packet)
        if packet_id == BlePacketType.NACK.value:
            if not self.is_waiting_for_ack:
                # Didn't send any packet, so it's likely a delayed NACK. Drop it
                return
            if self.sender_seq_num < incoming_packet.seq_num:
                # TODO: Implement informing receiver to SYN seq num
                pass
            elif self.sender_seq_num > incoming_packet.seq_num:
                # When sender_seq_num > incoming_packet.seq_num, NACK packet is likely delayed and we ignore it
                return
            elif (self.isValidPacket(self.lastPacketSent) and
                   self.getPacketTypeOfBytes(self.lastPacketSent) != BlePacketType.ACK.value):
                self.mPrint(bcolors.BRIGHT_YELLOW, "Received NACK with seq_num {} from {}, resending last packet"
                        .format(incoming_packet.seq_num, self.beetle_mac_addr))
                self.sendPacket(self.lastPacketSent)
        elif packet_id == BlePacketType.ACK.value:
            if not self.is_waiting_for_ack:
                # ACK received but we're not waiting for ACK, so it's likely a delayed packet and we ignore it
                return
            # We were waiting for an ACK, and now we received it. Process it
            if incoming_packet.seq_num > self.sender_seq_num:
                # Inform Beetle that ACK seq num is invalid
                self.sendNack(self.sender_seq_num)
                return
            if incoming_packet.seq_num < self.sender_seq_num:
                # ACK for earlier packet, likely a delayed packet so we ignore it
                return
            # incoming_packet.seq_num == self.sender_seq_num
            # Valid ACK received, stop waiting for ACK and increment sender seq_num
            self.sender_seq_num += 1
            self.is_waiting_for_ack = False
            self.lastPacketSent = None
            self.num_retransmits = 0
        elif packet_id != BlePacketType.ACK.value:
            seq_num_to_ack = self.receiver_seq_num
            if self.receiver_seq_num > incoming_packet.seq_num:
                # ACK for earlier packet was lost
                seq_num_to_ack = incoming_packet.seq_num
                self.mPrint(bcolors.BRIGHT_YELLOW, "ACK for packet num {} lost, expected seq num {}, synchronising seq num with {}"
                        .format(incoming_packet.seq_num, self.receiver_seq_num, self.beetle_mac_addr))
                # Don't handle raw data packet again since we've already done that
            elif self.receiver_seq_num < incoming_packet.seq_num:
                # TODO: Remove line below and perform SYN of seq num(via handshake?) instead
                seq_num_to_ack = incoming_packet.seq_num
                self.mPrint(bcolors.BRIGHT_YELLOW, "Received packet with seq num {} from {}, expected seq num {}"
                        .format(incoming_packet.seq_num, self.beetle_mac_addr, self.receiver_seq_num))
                """self.receiver_seq_num = incoming_packet.seq_num
                self.lastPacketSent = self.sendNack(incoming_packet.seq_num)
                continue """
            elif self.receiver_seq_num == incoming_packet.seq_num:
                self.handle_raw_data_packet(incoming_packet)
                # Increment receiver seq num
                if self.receiver_seq_num == MAX_SEQ_NUM:
                    # On the Beetle, seq num is 16-bit and overflows. So we 'overflow' by
                    #   resetting to 0 to synchronise with the Beetle
                    self.receiver_seq_num = 0
                else:
                    # Increment seq_num since received packet is valid
                    self.receiver_seq_num += 1
                if self.num_invalid_packets_received > 0:
                    self.num_invalid_packets_received = 0
            # ACK the received packet
            self.sendAck(seq_num_to_ack)

    def handle_raw_data_packet(self, raw_data_packet):
        pass

    def handle_ext_packet(self, ext_packet):
        pass

    def doHandshake(self):
        # Clear input buffer so transmissions after handshake begin in a clean state
        self.mDataBuffer.clear()
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
                    if self.mBeetle.waitForNotifications(BLE_WAIT_TIMEOUT):
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
                            if self.is_verbose_printing:
                                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Sending SYN+ACK {mLastPacketSent} to {self.beetle_mac_addr}""")
                            mSynTime = time.time()
                            hasAck = True
                        elif packet_id == BlePacketType.NACK.value:
                            self.sendPacket(mLastPacketSent)
                # Just in case Beetle NACK the SYN+ACK, we want to retransmit
                while (time.time() - mSynTime) < BLE_TIMEOUT:
                    # Wait for incoming packets
                    if self.mBeetle.waitForNotifications(BLE_WAIT_TIMEOUT):
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
                        if (packet_id == BlePacketType.NACK.value or 
                                    (packet_id == BlePacketType.ACK.value and 
                                            self.getSeqNumFrom(packetBytes) < mSeqNum)):
                            # SYN+ACK not received by Beetle, resend a SYN+ACK
                            if packet_id == BlePacketType.NACK.value:
                                self.mPrint(bcolors.BRIGHT_YELLOW, "Received NACK from {}, resending SYN+ACK"
                                        .format(self.beetle_mac_addr))
                            else:
                                self.mPrint(bcolors.BRIGHT_YELLOW, "Duplicate handshake ACK from {}, resending SYN+ACK"
                                        .format(self.beetle_mac_addr))
                            self.sendPacket(mLastPacketSent)
                            # Update mSynTime to wait for any potential NACK from Beetle again
                            mSynTime = time.time()
                        elif packet_id != BlePacketType.NACK.value and packet_id != BlePacketType.ACK.value:
                            # Beetle has started transmitting raw data, so it received SYN+ACK
                            break
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
    
    def clear_state(self):
        # self.mBeetle = None
        self.mDataBuffer.clear()
        self.hasHandshake = False
        self.num_retransmits = 0
        self.num_invalid_packets_received = 0
        self.is_waiting_for_ack = False
        self.lastPacketSent = None
        self.lastPacketSentTime = -1
        self.num_retransmits = 0

    def init_state(self):
        self.mBeetle = Peripheral()
        self.mBeetle.withDelegate(self.ble_delegate)
        self.hasHandshake = False
        self.num_retransmits = 0
        self.num_invalid_packets_received = 0
        self.is_waiting_for_ack = False
        self.lastPacketSent = None
        self.lastPacketSentTime = -1
        self.num_retransmits = 0

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
            if self.is_verbose_printing:
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
        # Accelerometer data
        x1 = self.parseImuData(dataBytes, 0) / ACC_LSB_SCALE
        y1 = self.parseImuData(dataBytes, 2) / ACC_LSB_SCALE
        z1 = self.parseImuData(dataBytes, 4) / ACC_LSB_SCALE
        # Gyroscope data
        x2 = self.parseImuData(dataBytes, 6) / GYRO_LSB_SCALE
        y2 = self.parseImuData(dataBytes, 8) / GYRO_LSB_SCALE
        z2 = self.parseImuData(dataBytes, 10) / GYRO_LSB_SCALE
        return x1, y1, z1, x2, y2, z2
    
    def getPacketTypeOf(self, blePacket):
        return metadata_to_packet_type(blePacket.metadata)
    
    def getPacketTypeOfBytes(self, packet_bytes):
        if packet_bytes is None or len(packet_bytes) < PACKET_SIZE:
            return ERROR_VALUE
        return metadata_to_packet_type(packet_bytes[0])
    
    def getSeqNumFrom(self, packetBytes):
        seq_num = packetBytes[1] + (packetBytes[2] << BITS_PER_BYTE)
        return seq_num
    
    def isValidPacket(self, given_packet):
        # Check for NULL packet or incomplete packet
        if given_packet is None or len(given_packet) < PACKET_SIZE:
            return False
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
                    packet_type))
        return False
    
    def isValidPacketType(self, packet_type_id):
        return packet_type_id <= BlePacketType.INFO.value and packet_type_id >= BlePacketType.HELLO.value
    
    def parseImuData(self, packetBytes, offset):
        # Get 2-byte signed integer containing 1 IMU data value from packetBytes
        ## Get only the first index since unpack_from() always returns a tuple
        imu_data_value = struct.unpack_from('<h', packetBytes, offset)[0]
        return imu_data_value

    """
        packetBytes assumed to be a valid 20-byte packet
    """
    def parsePacket(self, packetBytes):
        # Check for NULL packet or incomplete packet
        if packetBytes is None or len(packetBytes) < PACKET_SIZE:
            return BlePacket(ERROR_VALUE, ERROR_VALUE, bytearray(), ERROR_VALUE)
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
        if self.serial_char is not None:
            self.serial_char.write(packet)
        else:
            self.mPrint(bcolors.BRIGHT_YELLOW, 
                    f"""FATAL: Beetle {self.beetle_mac_addr} serial characteristic is None, cannot send packet""")
    
    def unpack_packet_bytes(self, packetBytes):
        metadata, seq_num, data, data_crc = struct.unpack(PACKET_FORMAT, packetBytes)
        return metadata, seq_num, data, data_crc
   
class ImuBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_raw_data_packet(self, raw_data_packet):
        x1, y1, z1, x2, y2, z2 = self.getDataFrom(raw_data_packet.data)
        internal_imu_packet = ImuPacket(self.beetle_mac_addr, [x1, y1, z1], [x2, y2, z2])
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_imu_packet = external_utils.ImuPacket(player_id, [x1, y1, z1], [x2, y2, z2])
        self.outgoing_queue.put(external_imu_packet)
        if self.is_verbose_printing:
            # TODO: Stop printing debug line below
            self.mPrint2("Received IMU data from {}: [{}, {}, {}, {}, {}, {}]"
                    .format(self.beetle_mac_addr, x1, y1, z1, x2, y2, z2))
        
class ImuUnreliableBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def main(self):
        while not self.terminateEvent.is_set():
            try:
                if not self.hasHandshake:
                    # Perform 3-way handshake
                    self.doHandshake()
                # Handshake already completed
                elif self.mBeetle.waitForNotifications(BLE_TIMEOUT):
                    if len(self.mDataBuffer) < PACKET_SIZE:
                        continue
                    # bytearray for 20-byte packet
                    packetBytes = self.get_packet_from(self.mDataBuffer)
                    if not self.isValidPacket(packetBytes):
                        self.num_invalid_packets_received += 1
                        if (self.num_invalid_packets_received == MAX_RETRANSMITS):
                            self.num_invalid_packets_received = 0
                            self.reconnect()
                            continue
                        # Just drop the packet, unreliable transmission here
                        continue
                    # assert packetBytes is a valid 20-byte packet
                    # Keep track of packets received
                    self.num_packets_received += 1
                    # Parse packet from 20-byte
                    receivedPacket = self.parsePacket(packetBytes)
                    self.handle_beetle_packet(receivedPacket)
            except BTLEException as ble_exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in connect() for Beetle: {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(ble_exc))
                self.mPrint2(stacktrace_str)
                self.reconnect()
            except KeyboardInterrupt as exc:
                # Catch and rethrow the exception so that caller can handle CTRL+C
                raise exc
            except Exception as exc:
                self.mPrint(bcolors.BRIGHT_YELLOW, f"""Exception in main() of {self.beetle_mac_addr}""")
                stacktrace_str = f"""{self.beetle_mac_addr} """ + ''.join(traceback.format_exception(exc))
                self.mPrint2(stacktrace_str)
        self.disconnect()

    def handle_beetle_packet(self, incoming_packet):
        # Given packet is assumed valid, so reset number of invalid packets
        self.num_invalid_packets_received = 0
        packet_id = self.getPacketTypeOf(incoming_packet)
        if packet_id == BlePacketType.IMU.value:
            self.handle_raw_data_packet(incoming_packet)
            if self.receiver_seq_num != incoming_packet.seq_num:
                self.mPrint(bcolors.BRIGHT_YELLOW, 
                        f"""Packet received has seq num {incoming_packet.seq_num} but expected {self.receiver_seq_num}""")
                self.receiver_seq_num = incoming_packet.seq_num
            # Increment receiver seq num
            if self.receiver_seq_num == MAX_SEQ_NUM:
                # On the Beetle, seq num is 16-bit and overflows. So we 'overflow' by
                #   resetting to 0 to synchronise with the Beetle
                self.receiver_seq_num = 0
            else:
                # Increment seq_num since received packet is valid
                self.receiver_seq_num += 1

    def handle_raw_data_packet(self, raw_data_packet):
        x1, y1, z1, x2, y2, z2 = self.getDataFrom(raw_data_packet.data)
        internal_imu_packet = ImuPacket(self.beetle_mac_addr, [x1, y1, z1], [x2, y2, z2])
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_imu_packet = external_utils.ImuPacket(player_id, [x1, y1, z1], [x2, y2, z2])
        self.outgoing_queue.put(external_imu_packet)
        if self.is_verbose_printing:
            # TODO: Stop printing debug line below
            self.mPrint2("Received IMU data from {}: [{}, {}, {}, {}, {}, {}]"
                    .format(self.beetle_mac_addr, x1, y1, z1, x2, y2, z2))

class GunBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_raw_data_packet(self, raw_data_packet):
        is_fired = self.get_gun_data_from(raw_data_packet)
        internal_gun_packet = GunPacket(self.beetle_mac_addr, is_fired)
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_gun_packet = external_utils.GunPacket(player_id, is_fired)
        self.outgoing_queue.put(external_gun_packet)
        if self.is_verbose_printing:
            self.mPrint2("Received gun data from {}: [isFired: {}]".format(self.beetle_mac_addr, is_fired))
    
    def get_gun_data_from(self, gun_packet):
        return gun_packet.data[0] == 1
    
    def handle_ext_packet(self, ext_packet): # type: ignore
        if isinstance(ext_packet, GunUpdatePacket):
            gun_packet_to_send = self.create_gun_packet(ext_packet.bullets)
            if self.is_verbose_printing:
                self.mPrint2(f"""Updating gun state with: {gun_packet_to_send}""")
            return gun_packet_to_send
        return None
    
    def create_gun_packet(self, bullets: int):
        gun_packet_to_send = self.createPacket(BlePacketType.GAME_STAT, 
                self.sender_seq_num, self.get_gun_data_from(bullets))
        return gun_packet_to_send
    
    def create_gun_packet_data(self, bullets: int):
        return bytearray([bullets])

class VestBeetle(Beetle):
    def __init__(self, beetle_mac_addr, outgoing_queue, incoming_queue, color = bcolors.BRIGHT_WHITE):
        super().__init__(beetle_mac_addr, outgoing_queue, incoming_queue, color)

    def handle_raw_data_packet(self, raw_data_packet):
        is_hit = self.get_vest_data_from(raw_data_packet)
        internal_vest_packet = VestPacket(self.beetle_mac_addr, is_hit)
        player_id = get_player_id_for(self.beetle_mac_addr)
        external_vest_packet = external_utils.VestPacket(player_id, is_hit)
        self.outgoing_queue.put(external_vest_packet)
        if self.is_verbose_printing:
            self.mPrint2("Received vest data from {}: [isHit: {}]".format(self.beetle_mac_addr, is_hit))

    def get_vest_data_from(self, vest_packet):
        return vest_packet.data[0] == 1

    def handle_ext_packet(self, ext_packet): # type: ignore
        if isinstance(ext_packet, VestUpdatePacket):
            vest_packet_to_send = self.create_vest_packet(ext_packet.is_hit, ext_packet.player_hp)
            if self.is_verbose_printing:
                self.mPrint2(f"""Updating vest state with: {vest_packet_to_send}""")
            return vest_packet_to_send
        return None
    
    def create_vest_packet(self, is_hit: bool, player_hp: int):
        vest_packet_to_send = self.createPacket(BlePacketType.GAME_STAT, self.sender_seq_num, 
                self.create_vest_data_from(is_hit, player_hp))
        return vest_packet_to_send
    
    def create_vest_data_from(self, is_hit: bool, player_hp: int):
        is_hit_int = 1 if is_hit else 0
        return bytearray([is_hit_int, player_hp])
    
