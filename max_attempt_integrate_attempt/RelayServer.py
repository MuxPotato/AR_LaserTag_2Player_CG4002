import ast
import socket
from threading import Thread, Event
import queue
import time
import traceback
import json
import re 
import numpy as np

AI_PACKET_COUNT = 105 # vary this to adjust number of packets to go AI
UPPERTHRESHOLD_X = -0.5 #
LOWERTHRESHOLD_X = -1.4
UPPERTHRESHOLD_Y = 0.0
LOWERTHRESHOLD_Y = -0.9
UPPERTHRESHOLD_Z = 0.5
LOWERTHRESHOLD_Z = -0.5

class RelayServer(Thread):
    def __init__(self, host,port,IMU_queue,shot_queue,fire_queue,to_rs_queue):
        Thread.__init__(self)
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.client = None
        self.IMU_queue = IMU_queue
        self.shot_queue = shot_queue 
        self.fire_queue = fire_queue 
        self.to_rs_queue = to_rs_queue  # hp and ammo to send back to beetles 
        self.server.settimeout(1.0)
        self.stop_event = Event()
        self.process_next_packets = Event()
        self.threshold =  10 
        self.packet_count =  30 
        self.x_packets = AI_PACKET_COUNT

        


    def handleClient(self, client, address):
        self.client = client
        while not self.stop_event.is_set():
            try:
                # Receive length followed by '_' followed by message
                data = b''
                while not data.endswith(b'_'):
                    _d = client.recv(1)
                    if not _d:  # Client disconnected
                        print(f"Client {address} disconnected")
                        raise ConnectionResetError("Client disconnected")
                    data += _d
                if len(data) == 0:
                    print("No data")
                    break

                data = data.decode("utf-8")
                length = int(data[:-1])

                data = b''
                while len(data) < length:
                    _d = client.recv(length - len(data))
                    if not _d:  # Client disconnected
                        print(f"Client {address} disconnected")
                        raise ConnectionResetError("Client disconnected")
                        
                    data += _d
                if len(data) == 0:
                    print("No data")
                    break

                msg = data.decode("utf-8")
                if length != len(data):
                    print("Packet length does not match, packet dropped")
                else:
                    
                    self.processMessage(msg)
          
            except (ConnectionResetError, socket.error) as e:
                    print(f"Error: {str(e)}. Attempting to reconnect...")

                    # Reattempt to accept the client connection
                    self.reconnectClient()

            except Exception as e:
                print(f"Unhandled exception in handleClient: {e}")
                traceback.print_exc()
                self.reconnectClient()
                break

            
    def reconnectClient(self):
        if self.client:
            self.client.close()
            self.client = None 
        while not self.stop_event.is_set():
            try:
                print("Waiting for client to reconnect...")
                client, address = self.server.accept()  # Attempt to reconnect
                print(f"Client reconnected from {address}")
                self.handleClient(client, address)  
                break  # Exit the loop if reconnection succeeds
            except socket.timeout:
                time.sleep(1)  
            except socket.error as e:
                print(f"Socket error during reconnection: {str(e)}")
                time.sleep(1)  
    
    def processMessage(self, msg):
        try:
            # Manually clean up any unwanted quotes or spaces
            msg = msg.strip('"').strip()

            # Check for IMUPacket
            if "IMUPacket" in msg:
                imu_match = re.search(r"'IMUPacket':\s*{.*?playerID':\s*(\d+).*?accel':\s*(\[.*?\]).*?gyro':\s*(\[.*?\])}", msg)
                if imu_match:
                    player_id = int(imu_match.group(1))  
                    accel_data = eval(imu_match.group(2))  # Use eval carefully
                    gyro_data = eval(imu_match.group(3))
        
                    # Create the packet data dictionary
                    packet_data = {
                        'playerID': player_id,
                        'accel': accel_data,
                        'gyro': gyro_data
                    }

                    # Check if accel for either x, y, z is beyond certain thresholds
                    if (np.sqrt(packet_data['accel'][0]**2 + packet_data['accel'][1]**2 + packet_data['accel'][2]**2) > 1.6):
                        #print(packet_data['accel'][0])
                        print(f"Threshold exceeded! Processing next {self.x_packets} packets.")
                        self.process_next_packets.set()  # Set the flag to true

                    
                    # If the flag is set, process the next `x` packets
                    if self.process_next_packets.is_set():
                        #print(f"Processing IMUPacket: {packet_data}")
                        self.IMU_queue.put(packet_data)
                        # Decrement the packet count and stop after `x` packets
                        self.x_packets -= 1
                        if self.x_packets <= 0:
                            self.process_next_packets.clear()  # Reset the flag
                            self.x_packets = AI_PACKET_COUNT  # Reset to the default count

                else:
                    print("Error: Could not parse IMUPacket")

            # Check for ShootPacket with either isFired or isHit
            elif "ShootPacket" in msg:
                shoot_match = re.search(r"'ShootPacket':\s*{.*?playerID':\s*(\d+).*?(isFired|isHit)':\s*(True|False)}", msg)
                if shoot_match:
                    player_id = int(shoot_match.group(1))  # Get playerID
                    action_type = shoot_match.group(2)  # Get either 'isFired' or 'isHit'
                    action_value = shoot_match.group(3)  # Keep the original case (True/False)
                
                    # Convert the string to a boolean
                    if action_value == 'True':
                        action_value = True
                    elif action_value == 'False':
                        action_value = False
                    else:
                        # Handle the case where action_value is neither 'True' nor 'False'
                        raise ValueError(f"Unexpected value for action_value: {action_value}")
                    
                    # Process ShootPacket
                    print(f"ShootPacket -> playerID: {player_id}, {action_type}: {action_value}")
                    if action_type == 'isFired':
                        self.fire_queue.put({
                            'playerID': player_id,
                            'isFired': action_value  # Keep original case
                        })
                    
                    elif action_type == 'isHit':
                        self.shot_queue.put({
                            'playerID': player_id,
                            'isHit': action_value  # Keep original case
                        })
                        
                    
                else:
                    print("Error: Could not parse ShootPacket")

            else:
                print("Unknown packet type received")

        except Exception as e:
            print(f"Error processing message: {e}")

        # Log the message to a file
        #with open("packets_from_beetles.log", "a") as log_file:
            #log_file.write(f"{time.ctime()}: {msg}\n")

    def start_sampling_period(self):
        """Start a 5-second sampling period for processing IMU packets."""
        self.sampling_end_time = time.time() + 5  # Set the end time to 5 seconds from now
        self.process_next_packets.set()  # Activate the flag to process packets

    def is_sampling_period_active(self):
        """Check if the sampling period is still active."""
        if self.sampling_end_time and time.time() < self.sampling_end_time:
            return True
        else:
            self.process_next_packets.clear()  # Deactivate the flag if the period has ended
            self.sampling_end_time = None  # Reset the end time
            return False

    
    def sendToRelayClient(self):
        """Send details like ammo, hp back to the relay client when available."""
        while not self.stop_event.is_set():
            try:
                # Try to get data from the game engine queue with a timeout to avoid blocking
                print("Trying to see if game engine send back anything")
                game_engine_data = self.to_rs_queue.get(timeout=1)
                message = message = json.dumps(game_engine_data)
                length = str(len(message))
                first = length + "_"
                if game_engine_data:
                    try:
                        if self.client:
                            self.client.sendall(first.encode("utf-8"))
                            self.client.sendall(message.encode("utf-8"))
                            print(f"Sent {game_engine_data} to Relay Client")
                    except (ConnectionResetError, socket.error) as e:
                        print(f"Failed to send to Relay Client. Trying to reconnect: {e}")
                        self.reconnectClient()
                    
            except queue.Empty:
                continue  # No data from game engine yet

    
    def run(self):
        self.server.listen(1)
        print(f'Listening on {self.host}:{self.port}')
        while not self.stop_event.is_set():
            try:
                client, address = self.server.accept()
                print(f"Relay Client connected from {address}")
                self.handleClient(client, address) 
                self.sendToRelayClient()
            except socket.timeout:
                pass
    

    def shutdown(self):
        self.stop_event.set()  # Set the stop event to stop the server loop
        self.server.close()  # Close the server socket
        print("Relay server shutdown initiated")