import socket
from threading import Thread, Event
import queue
import time
import traceback

class RelayServer(Thread):
    def __init__(self, host, port):
        Thread.__init__(self)
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.client = None
        #self.IMU_queue = IMU_queue
        #self.from_game_engine_queue = from_game_engine_queue  # Game engine to relay
        #self.game_engine_queue = game_engine_queue  # Relay to game engine
        self.server.settimeout(1.0)
        self.stop_event = Event()

    def handleClient(self, client, address):
        self.client = client
        try:
            while not self.stop_event.is_set():
                # Receive length followed by '_' followed by message
                data = b''
                while not data.endswith(b'_'):
                    _d = client.recv(1)
                    if not _d:  # Client disconnected
                        print(f"Client {address} disconnected")
                        client.close()
                        return
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
                        client.close()
                        return
                    data += _d
                if len(data) == 0:
                    print("No data")
                    continue

                msg = data.decode("utf-8")
                if length != len(data):
                    print("Packet length does not match, packet dropped")
                else:
                    print(f"Received '{msg}' from Relay Client")
                    self.processMessage(msg)
        finally:
            client.close()  # Ensure the connection is closed after handling

    def processMessage(self, msg):
        # Log the message to a file
        with open("received_messages.log", "a") as log_file:
            log_file.write(f"{time.ctime()}: {msg}\n")

        # Check and parse the message (example of differentiating packet types)
        # After checking, send IMU_packets to IMU_queue and gunpacket and vest packets to game engine 
        #self.IMU_queue.put(msg)
        #print("Message sent to AI/IMU processing")
    
    def sendToRelayClient(self):
        """Send details like ammo, hp back to the relay client when available."""
        while not self.stop_event.is_set():
            try:
                # Try to get data from the game engine queue with a timeout to avoid blocking
                game_engine_data = self.from_game_engine_queue.get(timeout=1)
                if game_engine_data:
                    response_msg = f"GameEngine Response: {game_engine_data}"
                    if self.client:
                        self.client.sendall(response_msg.encode('utf-8'))
                        print(f"Sent '{response_msg}' to Relay Client")
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

if __name__ == "__main__":
    try:
        relay_server = RelayServer('172.26.191.210', 6055)  # Start the server
        relay_server.start()
    except Exception as exc:
        traceback.print_exception(exc)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        relay_server.shutdown()
        relay_server.join()
