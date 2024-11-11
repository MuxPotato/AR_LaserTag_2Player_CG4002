
import json
from math import sqrt
import queue
import socket
import sys
import threading
import time
import traceback

from external_utils import COOLDOWN_PERIOD, PACKETS_PER_ACTION, QUEUE_GET_TIMEOUT, ImuRelayState
from internal_utils import bcolors

IS_DEBUG_PRINTING = False

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
                if IS_DEBUG_PRINTING:
                    print(f"Received message from server: {received_msg}")
                return received_msg 

        except (ConnectionResetError, socket.error) as e:
            print(f"Error: {str(e)}. Connection might be lost.")
            return None
        except KeyboardInterrupt as exc:
            # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
            raise exc
        
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

class SenderThread(threading.Thread):

    def __init__(self, stop_event: threading.Event, from_ble_IMU_queue: queue.Queue, socket, mutex_lock):
        super().__init__()
        self.stop_event: threading.Event = stop_event
        self.from_ble_IMU_queue: queue.Queue = from_ble_IMU_queue
        self.my_packet_type: str = "ImuPacket"
        self.my_data_type: str = "IMU"
        self.mutex_lock = mutex_lock
        self.relay_socket = socket
        # Threshold for accelerometer data before an incoming packet from Beetle is considered
        #   a potential action packet
        self.data_threshold: float = 1.5
        self.sender_state: ImuRelayState = ImuRelayState.WAITING_FOR_ACTION
        self.num_action_packets_sent: int = 0
        self.cooldown_period_start: float = 0

    def run(self):
        self.handle_beetle_data()

    def handle_beetle_data(self):
        while not self.stop_event.is_set():
            try:
                imu_packet = self.from_ble_IMU_queue.get(timeout = QUEUE_GET_TIMEOUT)  
                if IS_DEBUG_PRINTING:
                    print(f"""{self.my_data_type} data received from int comms: {imu_packet}""")
                # Here, you would parse the data and send it to the server
                self.send_beetle_data(imu_packet)

            except queue.Empty:
                continue
            except KeyboardInterrupt as exc:
                # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
                raise exc
            except Exception as exc:
                traceback.print_exception(exc)

    def send_beetle_data(self, imu_packet):
        if self.sender_state == ImuRelayState.WAITING_FOR_ACTION:
            # Incoming IMU data from Beetle has not crossed threshold yet
            accel_analytics: float = self.get_analytics_for(imu_packet)
            if accel_analytics >= self.data_threshold:
                print(f"""{bcolors.RED}NOTE: Player {imu_packet.playerID} triggered action, sending IMU data{bcolors.ENDC}""")
                # Current packet exceeds threshold for action(potential action packet),
                #   send it to relay server for AI inference
                self.sender_state = ImuRelayState.SENDING_ACTION
            # If imu data hasn't crossed threshold, continue waiting for a potential action packet
        elif self.sender_state == ImuRelayState.SENDING_ACTION:
            if self.num_action_packets_sent < PACKETS_PER_ACTION:
                # Incoming IMU data from Beetle crossed threshold, but number of action data packets
                #   sent is less than PACKETS_PER_ACTION
                serialized_packet: str = self.serialize(imu_packet)
                self.send_to_server(serialized_packet)
                self.num_action_packets_sent += 1
            if self.num_action_packets_sent >= PACKETS_PER_ACTION:
                # Target number of actions packets now sent, begin cooldown period
                self.sender_state = ImuRelayState.COOLDOWN
                self.num_action_packets_sent = 0
                # Cooldown period starts now, record the start time
                self.cooldown_period_start = time.time()
                if IS_DEBUG_PRINTING:
                    print(f"""{bcolors.RED}DEBUG: Player {imu_packet.playerID} cooldown period start{bcolors.ENDC}""")
                return
        elif self.sender_state == ImuRelayState.COOLDOWN:
            # Currently in cooldown period
            if (time.time() - self.cooldown_period_start) > COOLDOWN_PERIOD:
                if IS_DEBUG_PRINTING:
                    print(f"""{bcolors.RED}DEBUG: Player {imu_packet.playerID} cooldown period end, waiting for threshold{bcolors.ENDC}""")
                # Cooldown period is now over, return to waiting for action state
                self.sender_state = ImuRelayState.WAITING_FOR_ACTION
                return
            # Still within cooldown period, don't send any data(just drop the given packet)

    def send_to_server(self, given_data: str):
        #message = json.dumps(given_data)
        length = str(len(given_data))
        first = length + "_"
        # Ensure that only one thread sends data at a time
        self.mutex_lock.acquire()
        self.relay_socket.sendall(first.encode("utf-8"))
        self.relay_socket.sendall(given_data.encode("utf-8"))
        # Allow the other thread to send data now that we're done
        self.mutex_lock.release()
        if IS_DEBUG_PRINTING:
            print(f"""Sent {given_data} for {self.my_packet_type} to relay server""")

    # Begin helper functions section
    def get_analytics_for(self, imu_packet):
        imu_accel: list[float] = imu_packet.accel
        mean_sq_value: float = 0
        # Sum the square of each accelerometer value
        for value in imu_accel:
            mean_sq_value += value ** 2
        # Square root the sum of squares
        mean_sq_value = sqrt(mean_sq_value)
        return mean_sq_value
    
    def serialize(self, imu_packet):
        serialized_imu_data = f"""'{self.my_packet_type}': {imu_packet._asdict()}"""
        return serialized_imu_data
        
    
class AnkleSenderThread(SenderThread):
    def __init__(self, stop_event: threading.Event, from_ble_IMU_queue: queue.Queue, socket, mutex_lock):
        super().__init__(stop_event, from_ble_IMU_queue, socket, mutex_lock)
        self.my_packet_type: str = "AnklePacket"
        self.my_data_type: str = "Ankle"
        self.data_threshold: float = 2.7
        
class GloveSenderThread(SenderThread):
    def __init__(self, stop_event: threading.Event, from_ble_IMU_queue: queue.Queue, socket, mutex_lock):
        super().__init__(stop_event, from_ble_IMU_queue, socket, mutex_lock)
        self.my_packet_type: str = "IMUPacket"
        self.my_data_type: str = "Glove"
        self.data_threshold: float = 2.0

def handle_IMU_data(terminate_event, from_ble_IMU_queue, send_func):
    while not terminate_event.is_set():
        try:
            IMU_data = from_ble_IMU_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            if IS_DEBUG_PRINTING:
                print(f'IMU data received from int comms: {IMU_data}')
            serialized_imu_data = f"""'IMUPacket': {IMU_data._asdict()}"""
            # Here, you would parse the data and send it to the server
            send_func(serialized_imu_data)

        except queue.Empty:
            continue
        except KeyboardInterrupt as exc:
            # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
            raise exc
        except Exception as exc:
            traceback.print_exception(exc)


def handle_shoot_data(terminate_event, from_ble_shoot_queue, send_func):
    while not terminate_event.is_set():
        try:
            shoot_data = from_ble_shoot_queue.get(timeout = QUEUE_GET_TIMEOUT)  
            if IS_DEBUG_PRINTING:
                print(f'Shoot data received from int comms: {shoot_data}')
            serialized_shoot_data = f"""'ShootPacket': {shoot_data._asdict()}"""
            send_func(serialized_shoot_data)

        except queue.Empty:
            continue
        except KeyboardInterrupt as exc:
            # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
            raise exc
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
        if IS_DEBUG_PRINTING:
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

    def __init__(self, server_ip, server_port, from_ble_p1_ankle_queue, from_ble_p1_glove_queue,
                from_ble_p2_ankle_queue, from_ble_p2_glove_queue,
                from_ble_shoot_queue, to_ble_game_state_queue):
#    def __init__(self, from_ble_IMU_queue, from_ble_shoot_queue, glove_output, game_output):
        super().__init__()
        self.server_ip = server_ip
        self.server_port = server_port  
        self.timeout = 100   # the timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.from_ble_p1_ankle_queue = from_ble_p1_ankle_queue
        self.from_ble_p1_glove_queue = from_ble_p1_glove_queue
        self.from_ble_p2_ankle_queue = from_ble_p2_ankle_queue
        self.from_ble_p2_glove_queue = from_ble_p2_glove_queue
        self.from_ble_shoot_queue = from_ble_shoot_queue 
        self.to_ble_game_state_queue = to_ble_game_state_queue
        self.stop_event = threading.Event()
        self.socket_mutex = threading.Lock()
        self.ankle_p1_thread = AnkleSenderThread(self.stop_event, self.from_ble_p1_ankle_queue, self.socket, self.socket_mutex)
        self.glove_p1_thread = GloveSenderThread(self.stop_event, self.from_ble_p1_glove_queue, self.socket, self.socket_mutex)
        self.ankle_p2_thread = AnkleSenderThread(self.stop_event, self.from_ble_p2_ankle_queue, self.socket, self.socket_mutex)
        self.glove_p2_thread = GloveSenderThread(self.stop_event, self.from_ble_p2_glove_queue, self.socket, self.socket_mutex)
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
                if IS_DEBUG_PRINTING:
                    print(f"Received message from server: {msg}")
                return msg 

        except (ConnectionResetError, socket.error) as e:
            print(f"Error: {str(e)}. Connection might be lost.")
            return None

    def run(self):
        self.connect(self.server_ip,self.server_port)
        print('Connected to relay server')
        try:
            self.ankle_p1_thread.start()
            self.glove_p1_thread.start()
            self.ankle_p2_thread.start()
            self.glove_p2_thread.start()
            self.shoot_thread.start()
            print('Threads for ankle, glove and Shoot data started')
            self.receive_handler.start()
            print('Thread for receiving data from RelayServer started')
            self.stop_event.wait()
        except KeyboardInterrupt as exc:
            # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
            raise exc
        except Exception as exc:
            traceback.print_exception(exc)
            print("No data received from int comms")

    def quit(self):
        self.stop_event.set()
        self.ankle_p1_thread.join()
        self.glove_p1_thread.join()
        self.ankle_p2_thread.join()
        self.glove_p2_thread.join()
        self.shoot_thread.join()
        self.receive_handler.join()
        print('Threads for ankle, glove, Shoot data and receiving data stopped')
        self.socket.close()
        print('Relay client terminated')
