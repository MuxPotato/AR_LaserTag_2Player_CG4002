from threading import Thread
from queue import Queue
import random
import time 
import socket 
import json
import base64
from Crypto import Random
from Crypto.Cipher import AES
import sys
import time
from Crypto.Util.Padding import pad
from Color import print_message

class EvalClient(Thread):
    def __init__(self,eval_queue,server_ip, server_port,from_eval_queue):
        Thread.__init__(self)
        self.eval_queue = eval_queue
        self.secret_key = b'PLEASEMAYITWORKS'
        self.server_ip = server_ip
        self.server_port = server_port  
        self.from_eval_queue = from_eval_queue
        self.timeout = 100  # The timeout for receiving any data
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_running = False 
        self.conn = None
       
    # Debug
    # def connect(self):
    #     """
    #     Establish a connection to the server.
    #     """
    #     self.socket.connect((self.server_ip, self.server_port))
    #     self.send_text("hello")


    def connect(self):
        """
        Establish a connection to the server.
        """
        try:
            self.socket.connect((self.server_ip, self.server_port))
            print("Connection to eval_server established successfully.")
            self.send_text("hello")
        except (ConnectionRefusedError, TimeoutError) as e:
            print(f"Failed to connect to server: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        
    def encrypt_message(self, message_dict):
        """
        Encrypts the message using AES encryption (CBC mode).
        """
        encoded_msg = b""
        try:
            iv = Random.new().read(AES.block_size)
            cipher = AES.new(self.secret_key, AES.MODE_CBC, iv)
            encoded_msg = base64.b64encode(iv + cipher.encrypt(pad(message_dict.encode('utf-8'), AES.block_size)))
        except Exception as e:
            print(f"Exception in encrypt_message: {e}")
        return encoded_msg
    
    def send_text(self, message):
        """
        Send an encrypted message to the server.
        """
        encrypted_message = self.encrypt_message(message)
        length = str(len(encrypted_message))
        first = length + "_"
        second = encrypted_message
        self.socket.sendall(first.encode("utf-8"))
        self.socket.sendall(second)
  
    # def recv_text(self):
    #     """
    #     Receive a message from the server.
    #     """
    #     msg = ""
    #     success = False

    #     if self.socket is not None:
    #         try:
    #             while True:
    #                 # Receive length followed by '_' followed by message
    #                 data = b''
    #                 while not data.endswith(b'_'):
    #                     _d = self.socket.recv(1)
    #                     if not _d:
    #                         data = b''
    #                         break
    #                     data += _d
    #                 if len(data) == 0:
    #                     print("No data")
    #                     break
                        
    #                 data = data.decode("utf-8")
    #                 length = int(data[:-1])

    #                 data = b''
    #                 while len(data) < length:
    #                     _d = self.socket.recv(length - len(data))
    #                     if not _d:
    #                         data = b''
    #                         break
    #                     data += _d
    #                 if len(data) == 0:
    #                     break
    #                 msg = data.decode("utf8")  # Decode raw bytes to UTF-8
    #                 success = True
    #                 break
    #         except (ConnectionResetError, TimeoutError) as e:
    #             print(f"Exception in recv_text: {e}")
    #             self.socket.close()

    #     return success, msg

    def recv_text(self, timeout=10):
        """
        Receive a message from the server, waiting until a valid response is received or a timeout occurs.
        """
        msg = ""
        success = False
        start_time = time.time()

        if self.socket is not None:
            try:
                while True:
                    # Check if the timeout period has elapsed
                    if time.time() - start_time > timeout:
                        print("Timeout occurred while waiting for a response.")
                        break

                    # Receive length followed by '_' followed by message
                    data = b''
                    while not data.endswith(b'_'):
                        _d = self.socket.recv(1)
                        if not _d:
                            data = b''
                            break
                        data += _d

                    if len(data) == 0:
                        print("No data received for length")
                        continue  # Retry receiving if no data received

                    data = data.decode("utf-8")
                    length = int(data[:-1])

                    data = b''
                    while len(data) < length:
                        _d = self.socket.recv(length - len(data))
                        if not _d:
                            data = b''
                            break
                        data += _d

                    if len(data) == 0:
                        print("No data received for message")
                        continue  # Retry receiving if no data received

                    msg = data.decode("utf8")  # Decode raw bytes to UTF-8
                    success = True
                    break

            except (ConnectionResetError, TimeoutError) as e:
                print(f"Exception in recv_text: {e}")
                self.socket.close()

        return success, msg



    def run(self):
        self.connect()
        while True:
            
            message = self.eval_queue.get()
            
            #print(f"EvalClient: Received '{message}' from game engine")
            print("_"*30)
            print_message('Eval Client',f"Received message from game engine")
            print()

            # send message to eval server 
            self.send_text(json.dumps(message))
            success,response = self.recv_text()
            if success:
                print_message('Eval Client',f"Received {response} from EvalServer")
                self.from_eval_queue.put(response)
                print("_"*30)
                
            else: 
                print(f"EvalClient: Failed to receive response from EvalServer")

