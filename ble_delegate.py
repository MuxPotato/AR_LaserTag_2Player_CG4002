import traceback
from bluepy.btle import DefaultDelegate

from utils import LOWER_4BITS_MASK, PACKET_SIZE, BlePacketType, bcolors, is_metadata_byte

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
                print("{}Fragmented packet received{}".format(bcolors.BRIGHT_YELLOW, bcolors.ENDC))
            for dataByte in data:
                if is_metadata_byte(dataByte) or len(self.dataBuffer) > 0:
                    self.dataBuffer.append(dataByte)
                else:
                    print("Dropping byte {}".format(dataByte))
        except Exception as exc:
            traceback.print_exception(exc)
    
    def isHeaderByte(self, dataByte):
        packet_id = dataByte & LOWER_4BITS_MASK
        return packet_id <= BlePacketType.GAME_STAT.value and packet_id >= BlePacketType.HELLO.value