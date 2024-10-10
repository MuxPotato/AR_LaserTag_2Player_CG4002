
import json
import queue
import socket
import sys
import threading
import traceback

class RelayClient:

    def __init__(self,from_ble_IMU_queue,from_ble_shoot_queue):
        """ self.server_ip = server_ip
        self.server_port = server_port   """
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.from_ble_IMU_queue = from_ble_IMU_queue
        self.from_ble_shoot_queue = from_ble_shoot_queue 
        # Define the NamedTuple structures

# Function to parse the IMU and gun/vest packets into a unified dictionary
    def parse_packets(imu_packet, Shootpacket):
        # Create a unified dictionary for the player
        player_data = {
            'playerID': imu_packet.playerID,
            'accel': imu_packet.accel,
            'gyro': imu_packet.gyro,
            'isFire': Shootpacket.isFire,
            'isHit': Shootpacket.isHit
        }
        
        return player_data

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
    
    def handle_IMU_data(self):
        while True:
            try:
                IMU_data = self.from_ble_IMU_queue.get()  
                print(f'IMU data received from int comms: {IMU_data}')
                # Here, you would parse the data and send it to the server
                # player_data = self.parse_packets(IMU_data, ShootPacket())  # Pass dummy ShootPacket if needed
                # self.send(IMU_data)
            except queue.Empty:
                continue
    
    
    def handle_shoot_data(self):
        while True:
            try:
                shoot_data = self.from_ble_shoot_queue.get()  
                print(f'Shoot data received from int comms: {shoot_data}')
                # player_data = self.parse_packets(IMUPacket(), shoot_data)  # Pass dummy IMUPacket if needed
                # self.send(player_data)
            except queue.Empty:
                continue

    def run(self):
        #self.connect(self.server_ip,self.server_port)
        #print('Connected to relay server')
        while True:
            try:
              imu_thread = threading.Thread(target=self.handle_IMU_data)
              shoot_thread = threading.Thread(target=self.handle_shoot_data)
              imu_thread.start()
              shoot_thread.start()

              print('Threads for IMU and Shoot data started')
              
            except Exception as e :
                traceback.print_exception(e)
                print("No data received from int comms")
