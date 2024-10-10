
import json
import queue
import socket
import sys
import threading
import traceback

from external_utils import QUEUE_GET_TIMEOUT, write_packet_to

def handle_IMU_data(terminate_event, from_ble_IMU_queue, glove_output):
    while not terminate_event.is_set():
        try:
            IMU_data = from_ble_IMU_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            print(f'IMU data received from int comms: {IMU_data}')
            # Here, you would parse the data and send it to the server
            # player_data = self.parse_packets(IMU_data, ShootPacket())  # Pass dummy ShootPacket if needed
            # self.send(IMU_data)

            # TODO: Remove line below
            write_packet_to(glove_output, IMU_data)
        except queue.Empty:
            continue
        except Exception as exc:
            traceback.print_exception(exc)


def handle_shoot_data(terminate_event, from_ble_shoot_queue, game_output):
    while not terminate_event.is_set():
        try:
            shoot_data = from_ble_shoot_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            print(f'Shoot data received from int comms: {shoot_data}')
            # player_data = self.parse_packets(IMUPacket(), shoot_data)  # Pass dummy IMUPacket if needed
            # self.send(player_data)

            # TODO: Remove line below
            write_packet_to(game_output, shoot_data)
        except queue.Empty:
            continue
        except Exception as exc:
            traceback.print_exception(exc)

class RelayClient(threading.Thread):

#    def __init__(self, server_ip, server_port, from_ble_IMU_queue, from_ble_shoot_queue):
    def __init__(self, from_ble_IMU_queue, from_ble_shoot_queue, glove_output, game_output):
        super().__init__()
        """ self.server_ip = server_ip
        self.server_port = server_port   """
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.from_ble_IMU_queue = from_ble_IMU_queue
        self.from_ble_shoot_queue = from_ble_shoot_queue 
        self.stop_event = threading.Event()
        self.imu_thread = threading.Thread(target=handle_IMU_data,
                args = (self.stop_event, from_ble_IMU_queue, glove_output,))
        self.shoot_thread = threading.Thread(target=handle_shoot_data, 
                args = (self.stop_event, from_ble_shoot_queue, game_output,))
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

    def run(self):
        #self.connect(self.server_ip,self.server_port)
        #print('Connected to relay server')
        try:
            self.imu_thread.start()
            self.shoot_thread.start()
            print('Threads for IMU and Shoot data started')
            self.stop_event.wait()
        except Exception as exc:
            traceback.print_exception(exc)
            print("No data received from int comms")

    def quit(self):
        self.stop_event.set()
        self.imu_thread.join()
        self.shoot_thread.join()
        print('Threads for IMU and Shoot data stopped')
        #self.socket.close()
        print('Relay client terminated')
