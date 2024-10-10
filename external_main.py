import socket 
import sys 
import json
import queue
import time
import traceback

from external_utils import PlayerData, dump_to_file
from internal_main import InternalMainThread

class RelayClient:

    def __init__(self,server_ip,server_port,from_ble_IMU_queue,from_ble_shoot_queue):
        self.server_ip = server_ip
        self.server_port = server_port  
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.from_ble_IMU_queue = from_ble_IMU_queue
        self.from_ble_shoot_queue = from_ble_shoot_queue 

    # Function to parse the IMU and gun/vest packets into a unified dictionary
    def parse_packets(imu_packet, gun_packet, vest_packet):
        # Create a unified dictionary for the player
        player_data = PlayerData(imu_packet.playerID, imu_packet.accel, imu_packet.gyro,
                gun_packet.isFired, vest_packet.isHit)
        
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
        while True:
            try:
              IMU_data = self.from_ble_IMU_queue.get()
              print(f'IMU data received from int comms {IMU_data}')
              shoot_data = self.from_ble_shoot_queue.get()
              print(f'shoot data received from int comms {shoot_data}')
              #player_data = self.parse_packets(IMU_data, shoot_data)
              #self.send(player_data)
            except Exception as e:
                traceback.print_exception(e)
                print("No data received from int comms")

if __name__=="__main__":
    outgoing_glove_queue = queue.Queue()
    outgoing_game_state_queue = queue.Queue()
    incoming_game_state_queue = queue.Queue()
    int_main = InternalMainThread(outgoing_glove_queue,outgoing_game_state_queue,incoming_game_state_queue)
    try:
        int_main.start()
        int_main.join()
    except KeyboardInterrupt:
        int_main.quit()
        """ print("Outgoing glove queue: ",outgoing_glove_queue)
        print("Outgoing game state queue: ",outgoing_game_state_queue)
        print("Incoming game state queue: ",incoming_game_state_queue) """
        time.sleep(1)
        dump_to_file(outgoing_glove_queue, "glove")
        dump_to_file(outgoing_game_state_queue, "outgoing game state")
        dump_to_file(incoming_game_state_queue, "incoming game state")
    except Exception as exc:
        traceback.print_exception(exc)
    sys.exit(0)