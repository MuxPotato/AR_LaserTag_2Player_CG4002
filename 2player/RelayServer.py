import ast
import socket
from threading import Thread, Event
import queue
import time
import traceback
import json
import re 
from Color import print_message
import numpy as np



class RelayServer(Thread):
    def __init__(self, host ,port ,P1_IMU_queue,P2_IMU_queue,shot_queue ,P1_fire_queue ,P2_fire_queue ,to_rs_queue ):
        Thread.__init__(self)
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.client = None
        self.P1_IMU_queue = P1_IMU_queue
        self.P2_IMU_queue = P2_IMU_queue
        self.shot_queue = shot_queue 
        self.P1_fire_queue = P1_fire_queue 
        self.P2_fire_queue = P2_fire_queue 
        self.to_rs_queue = to_rs_queue  # hp and ammo to send back to beetles 
        self.server.settimeout(1.0)
        self.stop_event = Event()
        
        


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

                    

                    if packet_data["playerID"] == 1:
                        self.P1_IMU_queue.put(packet_data)
                    elif packet_data["playerID"] == 2:
                        self.P2_IMU_queue.put(packet_data)
                        
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
                        if player_id == 1:
                            self.P1_fire_queue.put({
                                'playerID': player_id,
                                'isFired': action_value  # Keep original case
                            })
                        elif player_id == 2:
                            self.P2_fire_queue.put({
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

    

    
    def sendToRelayClient(self):
        """Send details like ammo, hp back to the relay client when available."""
        while not self.stop_event.is_set():
            try:
                # Try to get data from the game engine queue with a timeout to avoid blocking
                print_message("Relay Server","Checking if any updates to send back to beetles")
                game_engine_data = self.to_rs_queue.get(timeout=0.5)
                message = json.dumps(game_engine_data)
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
        self.send_thread = Thread(target=self.sendToRelayClient)
        self.send_thread.start()
        
        while not self.stop_event.is_set():
            try:
                client, address = self.server.accept()
                print(f"Relay Client connected from {address}")
                self.handleClient(client, address)
            except socket.timeout:
                pass
    

    def shutdown(self):
        self.stop_event.set()  # Set the stop event to stop the server loop
        self.server.close()  # Close the server socket
        if self.send_thread:
            self.send_thread.join()
        print("Relay server shutdown initiated")