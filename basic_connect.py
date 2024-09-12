import struct
from bluepy.btle import Scanner, DefaultDelegate, Peripheral

# Parameters
PACKET_SIZE = 20
BLUNO_MANUFACTURER_ID = "4c000215e2c56db5dffb48d2b060d0f5a71096e000000000c5"
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
]
## BLE GATT
GATT_SERIAL_SERVICE_UUID = "0000dfb0-0000-1000-8000-00805f9b34fb"
GATT_SERIAL_CHARACTERISTIC_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"

# Variables

# Delegate
class BlePacketDelegate(DefaultDelegate):
    def __init__(self, serial_char):
        super().__init__()
        self.dataBuffer = bytearray()
        self.serial_char = serial_char

    # Bluno Beetle uses cHandle 37
    def handleNotification(self, cHandle, data):
        try:
            print("Incoming data: {}".format(data.hex()))
            # Add incoming bytes to receive buffer
            self.dataBuffer += data
            if len(self.dataBuffer) >= 20:
                # Fetch 1 20-byte packet from the buffer
                dataPacket = self.dataBuffer[0:20]
                # Remove the packet from the buffer
                #del self.dataBuffer[0:20]
                self.dataBuffer = self.dataBuffer[20:]
                print("New packet: {}".format(dataPacket))
                packetId = dataPacket[0]
                print("Packet ID: {}".format(packetId))
        except Exception as err:
            print(err)

    # To be implemented
    def sendAckPacket():
        self.serial_char.write()

# Connect
def getSerialChar(beetle):
    serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
    serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
    return serial_char

def createPacket(packet_id, seq_num, data):
    # TODO: Implement actual checksum
    checksum = 1
    packet = struct.pack("BH16sB", packet_id, seq_num, data, checksum)
    return packet

def connectTo(mac_addr):
    beetle = None
    try:
        print("Connecting to {}".format(mac_addr))
        beetle = Peripheral(deviceAddr = mac_addr)
        serial_service = beetle.getServiceByUUID(GATT_SERIAL_SERVICE_UUID)
        serial_char = serial_service.getCharacteristics(GATT_SERIAL_CHARACTERISTIC_UUID)[0]
        beetle.setDelegate(BlePacketDelegate(serial_char))
    except Exception as err:
        print("Unable to connect to Bluno Beetle")
        print(err)
    return beetle

# Main
## Receiving packets from the Beetle works ok now. my custom struct on the Beetle in packet.h is sent intact-ly
for beetle_addr in BLUNO_MAC_ADDR_LIST:
    beetle = connectTo(beetle_addr)
    if beetle:
        serial_char = getSerialChar(beetle)
        try:
            # serial_char.write(bytes("HELLOxxxxxxxxxxxxxxx", encoding = 'ascii'))
            while True:
                if beetle.waitForNotifications(1.0):
                    serial_char.write(bytes("ACK", encoding = 'ascii'))
                    print("Received notification")
        except KeyboardInterrupt as key:
            print("Keyboard interrupt")
        except Exception as err:
            print(err)
        finally:
            if beetle:
                print("Disconnecting {}".format(beetle.addr))
            beetle.disconnect()
