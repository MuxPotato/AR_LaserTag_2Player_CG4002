from threading import Thread
from queue import Queue
import random
import paho.mqtt.client as mqtt
import json
from Color import print_message
import time 
class MQTT(Thread):

    def __init__(self,viz_queue, phone_action_queue):
        Thread.__init__(self)
        self.viz_queue = viz_queue 
        self.phone_action_queue = phone_action_queue  # Initialize phone_action_queue
        self.gamestate_topic = "tovisualizer/gamestate"  # Topic for sending updates to Unity about gamestate 
        self.fov_topic = "tovisualizer/field_of_view"  # Topic for asking Unity if player in field of view, only if action is bomb
        self.viz_response = "fromvisualizer/response" # topic to get response 

        #self.in_view = False 
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

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

    # Function to process commands from Unity
    def process_command(self,command):
        
        # ADDED
        #Here we put the command received from the phone into the phone_action_queue
        print_message('MQTT', f"Putting command '{command}' into phone_action_queue")
        self.phone_action_queue.put(command)  # Put the command into the phone_action_queue for the Game Engine to process
        
        # If there's any additional processing for specific commands like field of view, it can be added here


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
    
    # # Function to send the current game state to Unity
    # def send_game_state(self,message):
    #     self.client.publish(self.gamestate_topic, message)
    #     print_message('MQTT',"Sent game state to phone")
    #     print("_"*30)
    #     message_dict = self.parse_message(message)
    #     if message_dict['action'] == 'bomb':
    #         print_message('MQTT',"Querying phone if opponent in field of view")
    #         query = f"fov"
    #         self.client.publish(self.fov_topic,query)

    def send_game_state(self, message):
        if message is None:
            print_message('MQTT', "Received an empty message, skipping game state update.")
            return  # Skip further processing if message is None

        # Publish the message to the gamestate topic
        self.client.publish(self.gamestate_topic, message)
        print_message('MQTT', "Sent game state to phone")
        print("_" * 30)

        # Parse the message string into a dictionary
        message_dict = self.parse_message(message)

        # Check if 'p1_action' or 'p2_action' is 'bomb'
        if 'p1_action' in message_dict and message_dict['p1_action'] == 'bomb':
            print_message('MQTT', "Querying phone if opponent in field of view for Player 1's bomb")
            query = f"fov"
            self.client.publish(self.fov_topic, query)
        elif 'p2_action' in message_dict and message_dict['p2_action'] == 'bomb':
            print_message('MQTT', "Querying phone if opponent in field of view for Player 2's bomb")
            query = f"fov"
            self.client.publish(self.fov_topic, query)




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