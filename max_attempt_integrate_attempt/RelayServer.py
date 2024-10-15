import ast
import socket
from threading import Thread, Event
import queue
import time
import traceback
import json
import re 


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
                    continue

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
                    continue

                msg = data.decode("utf-8")
                if length != len(data):
                    print("Packet length does not match, packet dropped")
                else:
                    #print(f"Received '{msg}' from Relay Client")
                    self.processMessage(msg)

            except (ConnectionResetError, socket.error) as e:
                    print(f"Error: {str(e)}. Attempting to reconnect...")

                    # Reattempt to accept the client connection
                    self.reconnectClient()
            finally:
                client.close()  # Ensure the connection is closed after handling

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
    
    def processMessage(self,msg):
        try:

            # Use regex to capture packet type and packet data
            match = re.match(r"'?(\w+)'?:\s*(\{.*\})", msg)
            if not match:
                raise ValueError("Message format is incorrect")

            packet_type = match.group(1)  
            packet_data_str = match.group(2)  

            print(f"Packet type: {packet_type}")
            print(f"Packet data string: {packet_data_str}")

            # Convert the packet data string to a dictionary using json.loads
            # First, replace single quotes with double quotes in packet_data_str
            packet_data_str = re.sub(r"(?<!\\)'", '"', packet_data_str)


            packet_data_str = packet_data_str.replace("False", "false").replace("True", "true").replace("None", "null")

            # parse the string as JSON
            packet_data = json.loads(packet_data_str)

            # Process based on packet type
            if packet_type == 'IMUPacket' and 'accel' in packet_data and 'gyro' in packet_data: 
                #check if accel for either x y z is beyond a certain threshold -> send the next x number of packets
                if any(abs(val) > self.threshold for val in packet_data['accel']): #clarify this value with andrew 
                    print(f"Threshold exceeded! Processing next {self.x_packets} packets.")
                    self.process_next_packets.set()  # Set the flag to true

                # If the flag is set, process the next `x` packets
                if self.process_next_packets.is_set():
                    print(f"Processing IMUPacket: {packet_data}")
                    self.IMU_queue.put(packet_data)
                    
                    # Decrement the packet count and stop after `x` packets
                    self.x_packets -= 1
                    if self.x_packets <= 0:
                        self.process_next_packets.clear()  # Reset the flag
                        self.x_packets = 5  # clarify this number with andrew  
                    

            elif packet_type == 'ShootPacket' and 'isFired' in packet_data:
                #print(f"Send to AI: {packet_data}")
                self.fire_queue.put(packet_data)

            elif packet_type == 'ShootPacket' and 'isHit' in packet_data:
                #print(f"Send to game engine: {packet_data}")
                self.shot_queue.put(packet_data)
           
            else:
                print("Unknown packet type received")

        except json.JSONDecodeError as e:
            print(f"Error processing message: Invalid JSON -> {e}")
        except ValueError as e:
            print(f"Error processing message: {e}")
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
                game_engine_data = self.to_rs_queue.get(timeout=1)
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



    """       
    def simulateClientWithLogFile(self,log_file_path):
        Simulate receiving data from a client by reading from a log file.
        try:
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    line  = line.strip()
                    if line: 
                        self.processMessage(line)
                    time.sleep(0.1)  # Simulate 10 packets per second
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    def run(self):
        while True:
            self.simulateClientWithLogFile('packets_from_beetles.log')
            time.sleep(1)

    """

