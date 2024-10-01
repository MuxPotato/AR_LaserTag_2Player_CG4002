from threading import Thread
from queue import Queue
import random
import paho.mqtt.client as mqtt
import json
from Color import print_message
import time 
class MQTT(Thread):

    def __init__(self,viz_queue):
        Thread.__init__(self)
        self.viz_queue = viz_queue 
        self.gamestate_topic = "tovisualizer/gamestate"  # Topic for sending updates to Unity about gamestate 
        self.fov_topic = "tovisualizer/field_of_view"  # Topic for asking Unity if player in field of view, only if action is bomb
        self.viz_response = "fromvisualizer/response" # topic to get response 

        #self.in_view = False 
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client._on_disconnect = self.on_disconnect 

        self.connected = False 
        self.reconnect_delay = 1 

        # Connect to the HiveMQ broker running on the Ultra96
        self.client.connect("localhost", 1883, 60)  # Adjust IP if HiveMQ is running elsewhere

        # Start the MQTT client loop
        self.client.loop_start()

    # Callback when the client connects to the broker
    def on_connect(self, client, userdata, flags, rc):
        print_message('MQTT',"Connected")
        self.client.subscribe(self.viz_response)  # Subscribe to commands from Unity

    # Callback when a message is received
    def on_message(self, client, userdata, msg):
        command = msg.payload.decode()
        print_message('MQTT',f"Received command from phone: {command}")
        print("_"*30)
        self.process_command(command)
    
    def on_disconnect(self,client,userdata,rc):
        self.connected = False 
        print_message('MQTT',f"Disconnected from MQTT broker. Reason:{rc}")
        if rc!=0:
            self.reconnect()

    def reconnect(self):
        while not self.connected:
            try:
                print_message('MQTT',f"Trying to reconnect in {self.reconnect_delay} seconds.. ")
                time.sleep(self.reconnect_delay)
                self.client.reconnect()
                self.reconnect_delay = min(self.reconnect_delay * 2 ,60)
            except Exception as e:
                print_message('MQTT',f"Reconnection failed:{e}")




    # Function to process commands from Unity
    def process_command(self,command):
        if command.startswith("fov:"):
            in_view = bool(command.split(":")[1])
            print_message('MQTT',f"The opponent is in view is {in_view}")
        
    def parse_message(self,message):
        # Split the message by commas first
        message_items = message.split(',')
        message_dict = {}
        for item in message_items:
            key, value = item.split(':')
            # Convert numeric values if needed
            if value.isdigit():
                value = int(value)
            message_dict[key] = value
        
        return message_dict
    
    # Function to send the current game state to Unity
    def send_game_state(self,message):
        self.client.publish(self.gamestate_topic, message)
        print_message('MQTT',"Sent game state to phone")
        print("_"*30)
        message_dict = self.parse_message(message)
        if message_dict['action'] == 'bomb':
            print_message('MQTT',"Querying phone if opponent in field of view")
            query = f"fov"
            self.client.publish(self.fov_topic,query)



    def run(self):
      while True:
        # Receive message from GameEngine
        time.sleep(2)
        message = self.viz_queue.get()
        #print(f"Visualizer thread: Received '{message}' from GameEngine")
        #print("_"* 30)
        print_message('MQTT',"Received message from GameEngine")
        print()
        self.send_game_state(message)
    
    def shutdown(self):
        print("Shutting down MQTT client...")

        # Disconnect from the broker
        self.client.disconnect()

        # Stop the network loop if loop_start() was used
        self.client.loop_stop()

        print("MQTT client shutdown complete.")