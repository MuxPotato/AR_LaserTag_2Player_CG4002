from threading import Thread
import queue
from pynq import Overlay, PL
import pandas as pd
from AIPredictor import Predictor
import random 
from Color import print_message
import time 


PACKET_NUMBER = 60
ACTIONS = ["basket", "volley", "bowl", "bomb", "shield", "reload", "basket","logout"] 

class AITwo(Thread):
    
    PL.reset()
    bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
    overlay = Overlay(bitstream_path)
    predictor = Predictor(overlay) 

    def __init__(self,P2_IMU_queue,P2_action_queue, P2_fire_queue,P2_ankle_queue):
        Thread.__init__(self)
        self.P2_IMU_queue = P2_IMU_queue
        self.P2_fire_queue = P2_fire_queue  
        self.P2_action_queue = P2_action_queue
        self.P2_ankle_queue = P2_ankle_queue 
        #self.last_activity_time = time.time()
        
    
   
    def random_action(self):
      return random.choice(ACTIONS)
    


    def run(self):
        messages_IMU = []
        
        while True:  
            
            # Check the gun queue first, as it has priority
            try:
                message_Shoot = self.P2_fire_queue.get(timeout=0.005)
                print("Received item from fire queue")
                
                # If there's a gun message and it's a fired action
                if message_Shoot and message_Shoot['isFired']:
                    action = 'gun'
                    combined_action = action + ":2"
                    self.P2_action_queue.put(combined_action)
                    continue  # Skip to the next loop since gun action takes priority

            except queue.Empty:
                pass
                #print("No item received from fire queue; checking IMU queue")\
            
            try:
                message_ankle = self.P2_ankle_queue.get(timeout = 0.005)
                print("Received item from ankle queue")
                
                if message_ankle:
                    action = 'soccer'
                    print_message('AIOne', f"Received '{message_ankle}' from RelayServer")
                    combined_action = action + ":2"
                    self.P2_action_queue.put(combined_action)
                    continue  # Skip to the next loop since ankle  takes priority
            except queue.Empty:
                pass 

            # Check the IMU queue only if no gun data was available
            try:
                message_IMU = self.P2_IMU_queue.get(timeout=0.5)
                
                print("Received item from IMU queue")
                #self.last_activity_time = time.time()

                # TODO: Check hasReceivedP1Action Signal from GameEngine. 

            except queue.Empty:
                message_IMU = None
                pass
                #print("No item received from IMU queue; continuing to next loop")
              
            if message_IMU is not None:
                messages_IMU.append(message_IMU)
            #if time.time() - self.last_activity_time > 3 and len(messages_IMU) > 30 and not message_Shoot['isFire']:
            if len(messages_IMU) == PACKET_NUMBER:
                print("Sending data for prediction")
                data = {
                    'Accel X': [message['accel'][0] for message in messages_IMU],
                    'Accel Y': [message['accel'][1] for message in messages_IMU],
                    'Accel Z': [message['accel'][2] for message in messages_IMU],
                    'Gyro X': [message['gyro'][0] for message in messages_IMU],
                    'Gyro Y': [message['gyro'][1] for message in messages_IMU],
                    'Gyro Z': [message['gyro'][2] for message in messages_IMU],
                }
                #print(data)
                df = pd.DataFrame(data)
                action_number = self.predictor.get_action(df)
                #print(f"ACTION NUMBER IS: {action_number}")
                action = ACTIONS[action_number]
                print(f"Predicted action is: {action}")
                combined_action = action + ":2"
                self.P2_action_queue.put(combined_action)
                #message_Shoot['isFire'] = False
                messages_IMU = []



# ACTIONS = ["basket", "volley", "bowl", "bomb", "shield", "reload", "basket","logout"] #Since logout is not handled yet

# class AITwo(Thread):
    
#     PL.reset()
#     bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
#     overlay = Overlay(bitstream_path)
#     predictor = Predictor(overlay)

#     def __init__(self,P2_IMU_queue,P2_action_queue, P2_fire_queue):
#         Thread.__init__(self)
#         self.P2_IMU_queue = P2_IMU_queue
#         self.P2_fire_queue = P2_fire_queue  
#         self.P2_action_queue = P2_action_queue
    
   
#     def random_action(self):
#       return random.choice(ACTIONS)
    

#     def run(self):
#         while True:
#             # Check the gun queue first, as it has priority
#             try:
#                 message_Shoot = self.P2_fire_queue.get(timeout=0.005)
#                 print("Received item from fire queue")
                
#                 # If there's a gun message and it's a fired action
#                 if message_Shoot and message_Shoot['isFired']:
#                     action = 'gun'
#                     combined_action = action + ":2"
#                     self.P2_action_queue.put(combined_action)
#                     continue  # Skip to the next loop since gun action takes priority

#             except queue.Empty:
#                 pass
#                 #print("No item received from fire queue; checking IMU queue")
            
#             # Check the IMU queue only if no gun data was available
#             try:
#                 message_IMU = self.P2_IMU_queue.get(timeout=0.5)
#                 print("Received item from IMU queue")
                
#                 # TODO: Check hasReceivedP2Action Signal from GameEngine. 

#                 if message_IMU:
#                     print_message('AITwo', f"Received '{message_IMU}' from RelayServer")
#                     action = self.random_action()  # Generate a random action if IMU data is present
#                     combined_action = action + ":2"
#                     self.P2_action_queue.put(combined_action)
#                     time.sleep(10)

#             except queue.Empty:
#                 pass
#                 #print("No item received from IMU queue; continuing to next loop")

    


    # while True:
    #     message = self.P2_IMU_queue.get()
    #     print_message('AITwo Thread',f"Received '{message}' from RelayServer")
    #     print()
    #     #action = "bomb"
    #     action = self.random_action()
    #     combined_action = action + ":2"
    #     self.P2_action_queue.put(combined_action)


     
    # def run(self):
    #   messages_IMU = []
    #   packet_number = 25
    
    #   while True:
    #     try:
    #         message_IMU = self.P2_IMU_queue.get(timeout=0.5) #get from Shoot_queue
    #         print("Received item from IMU queue")
    #     except queue.Empty:
    #         message_IMU = None
    #         print("NO item received as IMU queue is empty")

    #     try:
    #         message_Shoot = self.P2_fire_queue.get(timeout=0.005) #get from Shoot_queue
    #         print("Received item from fire queue")
    #     except queue.Empty:
    #         message_Shoot = None
    #         print("NO item received as fire queue is empty")
        
    #     if message_Shoot is not None and message_Shoot['isFired']: #only care abt isHit and not isFired 
    #        action = 'gun'
    #        number = 2
    #        combined_action = action+ ":2"
    #        self.P2_action_queue.put(combined_action) 
        
    #     if len(messages_IMU) < packet_number and message_IMU is not None:
    #         messages_IMU.append(message_IMU)
    #         if len(messages_IMU) == packet_number: #and ~message_Shoot['isFire']:
    #             print("Sending data for prediction")
    #             data = {
    #                 'Accel X': [message['accel'][0] for message in messages_IMU],
    #                 'Accel Y': [message['accel'][1] for message in messages_IMU],
    #                 'Accel Z': [message['accel'][2] for message in messages_IMU],
    #                 'Gyro X': [message['gyro'][0] for message in messages_IMU],
    #                 'Gyro Y': [message['gyro'][1] for message in messages_IMU],
    #                 'Gyro Z': [message['gyro'][2] for message in messages_IMU],
    #             }
    #             #print(data)
    #             #df = pd.DataFrame(data)
    #             action = self.random_action()
    #             #action_number = self.predictor.get_action(df)
    #             #print(f"ACTION NUMBER IS: {action_number}")
    #             #action = ACTIONS[action_number]
    #             #print(f"Predicted action is: {action}")
    #             number = 2 #Can assume 2 as this queue is reserved for player 2 
    #             combined_action = action + ":2"
    #             self.P2_action_queue.put(combined_action)
    #             #message_Shoot['isFire'] = False
    #             messages_IMU = []
        