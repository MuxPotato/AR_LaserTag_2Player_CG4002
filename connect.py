from bluepy.btle import Scanner, DefaultDelegate, Peripheral

# Parameters
BLUNO_NAME = 'Bluno'
BLUNO_MANUFACTURER_ID = "4c000215e2c56db5dffb48d2b060d0f5a71096e000000000c5"
BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b"
]

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device: {}".format(dev.addr))
        elif isNewData:
            print("Received new data from: {}".format(dev.addr))

def parseDeviceName(nameValue):
    # Bluno pads its 'Complete Local Name' with trailing '\x00' characters, so we strip them
    return nameValue.rstrip('\x00').strip()

def fetchCurrentDevices(period = 5.0):
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(period)
    return devices

def scanAllDevices():
    """ scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(5.0) """
    devices = fetchCurrentDevices(5.0)

    for dev in devices:
        """ print("Device {} ({}), RSSI={} dB".format(dev.addr, dev.addrType, dev.rssi))
        for (adtype, desc, value) in dev.getScanData():
            print("  {} = {}".format(desc, value))
            print("Value text: {}".format(dev.getValueText(adtype))) """
        for (adtype, desc, value) in dev.getScanData():
            if adtype == 9 and parseDeviceName(value) == BLUNO_NAME: # 'Complete Local Name' is 'Bluno'
                print("Found Bluno device with MAC: {}".format(dev.addr))

def hasBluno(devices):
    for dev in devices:
        if dev in BLUNO_MAC_ADDR_LIST:
            return True
    return False

def getBlunoFrom(devices):
    blunos = []
    for dev in devices:
        if dev.addr in BLUNO_MAC_ADDR_LIST:
            blunos.append(dev)
    return blunos

def connectTo(mac_addr):
    beetle = None
    try:
        beetle = Peripheral(deviceAddr = mac_addr)
    except:
        print("Unable to connect to Bluno Beetle")
    return beetle

devices = fetchCurrentDevices(5.0)
blunos = getBlunoFrom(devices)
beetles = []
if (len(blunos) > 0):
    for bluno in blunos:
        print("Connecting to {}".format(bluno.addr))
        beetles.append(connectTo(bluno.addr))
print(beetles)
for beetle in beetles:
    print("Disconnecting {}".format(beetle.addr))
    beetle.disconnect()
