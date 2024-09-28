import threading 
import queue 
import socket 
import sys 
from thread_connect import PacketType,bcolors,BlePacketDelegate,Beetle
from RelayClient import RelayClient
# Constants

BLUNO_MAC_ADDR_LIST = [
    "f4:b8:5e:42:67:2b",
    "F4:B8:5E:42:6D:75",
    "F4:B8:5E:42:67:6E"
]







if __name__ == "__main__":
    if len(sys.argv) != 3:
            print("Usage: python main.py <server_ip> <server_port>")
            sys.exit(1)
        
    ipaddress = sys.argv[1]
    port = int(sys.argv[2])
    ble_to_relay_queue = queue.Queue()
    
    beetles = []
    colors = [bcolors.OKGREEN, bcolors.OKCYAN, bcolors.FAIL]
    try:
        index = 0
        for beetle_addr in BLUNO_MAC_ADDR_LIST:
            thisBeetle = Beetle(ble_to_relay_queue,beetle_addr, colors[index])
            thisBeetle.start()
            beetles.append(thisBeetle)
            index += 1
        relay_client = RelayClient(ipaddress,port,ble_to_relay_queue)
        relay_client.start()
        for thisBeetle in beetles:
            thisBeetle.join()
        relay_client.join()

    except KeyboardInterrupt as err:
        for mBeetle in beetles:
            mBeetle.quit()
        relay_client.quit()
        sys.exit(0)
