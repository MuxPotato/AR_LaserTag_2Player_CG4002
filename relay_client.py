
import json
import queue
import socket
import sys
import threading
import traceback

from external_utils import QUEUE_GET_TIMEOUT

class ReceiverThread(threading.Thread):
    def __init__(self, my_socket: socket.SocketType, server_ip: str, stop_event: threading.Event, to_ble_game_state_queue: queue.Queue):
        super().__init__()
        self.my_socket = my_socket
        self.server_ip = server_ip
        self.stop_event = stop_event
        self.to_ble_game_state_queue = to_ble_game_state_queue
        
    def handle_receive(self):
        try:
            # Receive length followed by '_' followed by message
            data = b''
            while not data.endswith(b'_'):
                _d = self.my_socket.recv(1)
                if not _d:  
                    print(f"Server {self.server_ip} disconnected")
                    raise ConnectionResetError("Server disconnected")
                data += _d
            
            if len(data) == 0:
                print("No data received")
                return None

            data = data.decode("utf-8")
            length = int(data[:-1])

            data = b''
            while len(data) < length:
                _d = self.my_socket.recv(length - len(data))
                if not _d: 
                    print(f"Server {self.server_ip} disconnected")
                    raise ConnectionResetError("Server disconnected")
                data += _d

            if len(data) == 0:
                print("No data received")
                return None

            received_msg = data.decode("utf-8")
            if length != len(data):
                print("Packet length does not match, packet dropped")
                return None
            else:
                print(f"Received message from server: {received_msg}")
                return received_msg 

        except (ConnectionResetError, socket.error) as e:
            print(f"Error: {str(e)}. Connection might be lost.")
            return None
        
    def update_game_state(self, received_msg: str):
        # game state is a dictionary
        game_state = json.loads(received_msg)
        self.to_ble_game_state_queue.put(game_state)

    def run(self):
        while not self.stop_event.is_set():
            received_msg = self.handle_receive()
            if received_msg is not None:
                # Do something with the received message
                self.update_game_state(received_msg)  

def handle_IMU_data(terminate_event, from_ble_IMU_queue, send_func):
    while not terminate_event.is_set():
        try:
            IMU_data = from_ble_IMU_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            print(f'IMU data received from int comms: {IMU_data}')
            serialized_imu_data = f"""'IMUPacket': {IMU_data._asdict()}"""
            # Here, you would parse the data and send it to the server
            send_func(serialized_imu_data)

        except queue.Empty:
            continue
        except Exception as exc:
            traceback.print_exception(exc)


def handle_shoot_data(terminate_event, from_ble_shoot_queue, send_func):
    while not terminate_event.is_set():
        try:
            shoot_data = from_ble_shoot_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            print(f'Shoot data received from int comms: {shoot_data}')
            serialized_shoot_data = f"""'ShootPacket': {shoot_data._asdict()}"""
            send_func(serialized_shoot_data)

        except queue.Empty:
            continue
        except Exception as exc:
            traceback.print_exception(exc)

def get_send_func(socket, mutex):
    def send_func(given_msg):
        #message = json.dumps(given_msg)
        length = str(len(given_msg))
        first = length + "_"
        # Ensure that only one thread sends data at a time
        mutex.acquire()
        socket.sendall(first.encode("utf-8"))
        socket.sendall(given_msg.encode("utf-8"))
        # Allow the other thread to send data now that we're done
        mutex.release()
        print(f'Sent {given_msg} to relay server')
    
    return send_func

# Function to parse the IMU and gun/vest packets into a unified dictionary
def parse_packets(imu_packet, Shootpacket):
    # Create a unified dictionary for the player
    player_data = {
        'playerID': imu_packet.playerID,
        'accel': imu_packet.accel,
        'gyro': imu_packet.gyro,
        'isFired': Shootpacket.isFire,
        'isHit': Shootpacket.isHit
    }
    
    return player_data

class RelayClient(threading.Thread):

    def __init__(self, server_ip, server_port, from_ble_IMU_queue, from_ble_shoot_queue, to_ble_game_state_queue):
#    def __init__(self, from_ble_IMU_queue, from_ble_shoot_queue, glove_output, game_output):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port  
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.from_ble_IMU_queue = from_ble_IMU_queue
        self.from_ble_shoot_queue = from_ble_shoot_queue 
        self.to_ble_game_state_queue = to_ble_game_state_queue
        self.stop_event = threading.Event()
        self.socket_mutex = threading.Lock()
        self.imu_thread = threading.Thread(target=handle_IMU_data,
                args = (self.stop_event, from_ble_IMU_queue, get_send_func(self.socket, self.socket_mutex),))
        self.shoot_thread = threading.Thread(target=handle_shoot_data, 
                args = (self.stop_event, from_ble_shoot_queue, get_send_func(self.socket, self.socket_mutex),))
        self.receive_handler = ReceiverThread(self.socket, self.server_ip, self.stop_event, 
                self.to_ble_game_state_queue)

    def connect(self,host,port):
        try:
            self.socket.connect((host,port))
        except Exception as e:
            print(f'Could not connect:{e}')
            sys.exit(1)

    def receive(self):
        try:
            # Receive length followed by '_' followed by message
            data = b''
            while not data.endswith(b'_'):
                _d = self.socket.recv(1)
                if not _d:  
                    print(f"Server {self.server_ip} disconnected")
                    raise ConnectionResetError("Server disconnected")
                data += _d
            
            if len(data) == 0:
                print("No data received")
                return None

            data = data.decode("utf-8")
            length = int(data[:-1])

            data = b''
            while len(data) < length:
                _d = self.socket.recv(length - len(data))
                if not _d: 
                    print(f"Server {self.server_ip} disconnected")
                    raise ConnectionResetError("Server disconnected")
                data += _d

            if len(data) == 0:
                print("No data received")
                return None

            msg = data.decode("utf-8")
            if length != len(data):
                print("Packet length does not match, packet dropped")
                return None
            else:
                print(f"Received message from server: {msg}")
                return msg 

        except (ConnectionResetError, socket.error) as e:
            print(f"Error: {str(e)}. Connection might be lost.")
            return None

    def run(self):
        self.connect(self.server_ip,self.server_port)
        print('Connected to relay server')
        try:
            self.imu_thread.start()
            self.shoot_thread.start()
            print('Threads for IMU and Shoot data started')
            self.receive_handler.start()
            print('Thread for receiving data from RelayServer started')
            self.stop_event.wait()
        except Exception as exc:
            traceback.print_exception(exc)
            print("No data received from int comms")

    def quit(self):
        self.stop_event.set()
        self.imu_thread.join()
        self.shoot_thread.join()
        self.receive_handler.join()
        print('Threads for IMU, Shoot data and receiving data stopped')
        self.socket.close()
        print('Relay client terminated')
