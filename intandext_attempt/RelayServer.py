import socket
from threading import Thread, Event
import queue
import time
import traceback

class RelayServer(Thread):
    def __init__(self, host,port,IMU_queue,shoot_queue):
        Thread.__init__(self)
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.client = None
        self.IMU_queue = IMU_queue
        self.shoot_queue = shoot_queue 
        #self.from_game_engine_queue = from_game_engine_queue  # hp and ammo to send back to beetles 
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
        # Close the current client socket if it's open
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
        # Check and parse the message (example of differentiating packet types)
        try:
            if 'accel' in msg and 'gyro' in msg:
                print(f"Processing IMUPacket from player {msg['playerID']}")
                self.IMU_queue.put(msg)  
            # Check if it's a ShootPacket by the presence of 'isFired' or 'isHit'
            elif 'isFired' in msg or 'isHit' in msg:
                print(f"Processing ShootPacket from player {msg['playerID']}")
                self.shoot_queue.put(msg)  # put in shoot _queue for both AI and game engine to get later 
            else:
                print("Unknown packet type received")
        
        except KeyError as e:
            print(f"Missing key in message: {e}")
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
                game_engine_data = self.from_game_engine_queue.get(timeout=1)
                if game_engine_data:
                    try:
                        if self.client:
                            self.client.sendall(game_engine_data.encode('utf-8'))
                            print(f"Sent '{game_engine_data}' to Relay Client")
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
            except socket.timeout:
                pass

    def shutdown(self):
        self.stop_event.set()  # Set the stop event to stop the server loop
        self.server.close()  # Close the server socket
        print("Relay server shutdown initiated")


