import socket 
import sys 
import json
import random


class RelayClient:

    def __init__(self,server_ip,server_port,ble_to_relay_queue):
        self.server_ip = server_ip
        self.server_port = server_port  
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.ble_to_relay_queue = ble_to_relay_queue
    
    def connect(self,host,port):
        try:
            self.socket.connect((host,port))
        except Exception as e:
            print(f'Could not connect:{e}')
            sys.exit(1)
    
    def send(self,message):
        message = json.dumps(message)
        length = str(len(message))
        first = length + "_"
        self.socket.sendall(first.encode("utf-8"))
        self.socket.sendall(message.encode("utf-8"))
        print(f'Sent {message} to relay server')


    def receive(self,message):
        pass

    def choosemsg(self):
        messages = [
            {'playerID': 2, 'sensorID': 4, 'shotDetected': 'True', "IMU": {'x': 0, 'y': 0, 'z': 0}},
            {'playerID': 2, 'sensorID': 3, 'shotDetected': 'True', "IMU": {'x': 10, 'y': 11, 'z': 0}},
            {'playerID': 1, 'sensorID': 1, 'shotDetected': 'False', "IMU": {'x': 15, 'y': 20, 'z': 5}},
            {'playerID': 2, 'sensorID': 4, 'shotDetected': 'True', "IMU": {'x': 32, 'y': 15, 'z': 4}}
            # IMU, isshot, isfired, 
        ]
        return random.choice(messages)

    def run(self):
        self.connect(self.server_ip,self.server_port)
        print('Connected to relay server')
        while True:
            try:
              ble_data = self.data_queue.get()
              print(f'data received from int comms {ble_data}')
              self.send(ble_data)
            except ble_data:
                print("No data received from int comms")







