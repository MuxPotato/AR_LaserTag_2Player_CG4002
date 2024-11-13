from threading import Thread
import queue
from pynq import Overlay, PL
import pandas as pd
from AIPredictor import Predictor
import random 
from Color import print_message
#import time

PACKET_NUMBER = 60
ACTIONS = ["basket", "volley", "bowl", "bomb", "shield", "reload", "logout"] 

class AIOne(Thread):
    
    
    PL.reset()
    bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
    overlay = Overlay(bitstream_path)
    predictor = Predictor(overlay) 

    def __init__(self,P1_IMU_queue,P1_action_queue, P1_fire_queue,P1_ankle_queue):
        Thread.__init__(self)
        self.P1_IMU_queue = P1_IMU_queue
        self.P1_fire_queue = P1_fire_queue  
        self.P1_action_queue = P1_action_queue
        self.P1_ankle_queue = P1_ankle_queue 
        #self.last_activity_time = time.time()
        self.message_ankle_count = 0 
        
    
   
    #def random_action(self):
    #  return random.choice(ACTIONS)
    


    def run(self):
        messages_IMU = []
        while True:
            
            
            # Check the gun queue first, as it has priority
            try:
                message_Shoot = self.P1_fire_queue.get(timeout=0.005)
                print("AIOne: Received item from fire queue")
                
                # If there's a gun message and it's a fired action
                if message_Shoot:
                    action = 'gun'
                    combined_action = action + ":1"
                    self.P1_action_queue.put(combined_action)
                    continue  # Skip to the next loop since gun action takes priority



            except queue.Empty:
                pass
                #print("No item received from fire queue; checking IMU queue")\
            
            # try:
            #     message_ankle = self.P1_ankle_queue.get(timeout = 0.005)
            #     print("Received item from ankle queue")
                
            #     if message_ankle:
            #         action = 'soccer'
            #         print_message('AIOne', f"Received '{message_ankle}' from RelayServer")
            #         combined_action = action + ":1"
            #         self.P1_action_queue.put(combined_action)
            #         continue  # Skip to the next loop since ankle  takes priority
            # except queue.Empty:
            #     pass 
            
            try:
                message_ankle = self.P1_ankle_queue.get(timeout = 0.005)
                print("AIOne: Received item from ankle queue")
                
                if message_ankle:
                    self.message_ankle_count += 1
                    
                    if (self.message_ankle_count == 60):
                        action = 'soccer'
                        print_message('AIOne', f"Received '{message_ankle}' from RelayServer")
                        combined_action = action + ":1"
                        self.P1_action_queue.put(combined_action)
                        self.message_ankle_count = 0

                    continue  # Skip to the next loop since ankle  takes priority
            except queue.Empty:
                pass

            # Check the IMU queue only if no gun data was available
            try:
                message_IMU = self.P1_IMU_queue.get(timeout=0.005)
                
                print("AIOne: Received item from IMU queue")
                #self.last_activity_time = time.time()

                # TODO: Check hasReceivedP1Action Signal from GameEngine. 

            except queue.Empty:
                continue
                #print("No item received from IMU queue; continuing to next loop")
            
           

            # Proper Code

            messages_IMU.append(message_IMU)
            print("AIOne: IMU data appended to messages")
            print("AIOne: Current IMU message count: ", len(messages_IMU))
            #if time.time() - self.last_activity_time > 3 and len(messages_IMU) > 30 and not message_Shoot['isFire']:
            if len(messages_IMU) == PACKET_NUMBER:
                print("AIOne: Sending data for prediction")
                data = {
                    'Accel X': [message['accel'][0] for message in messages_IMU],
                    'Accel Y': [message['accel'][1] for message in messages_IMU],
                    'Accel Z': [message['accel'][2] for message in messages_IMU],
                    'Gyro X': [message['gyro'][0] for message in messages_IMU],
                    'Gyro Y': [message['gyro'][1] for message in messages_IMU],
                    'Gyro Z': [message['gyro'][2] for message in messages_IMU],
                }

                # Comment out for actual test
                print(data)
                try:
                    action_number = self.predictor.get_action(data)
                    #print(f"ACTION NUMBER IS: {action_number}")
                    action = ACTIONS[action_number]
                    print(f"AIOne: Predicted action is: {action}")
                    combined_action = action + ":1"
                    self.P1_action_queue.put(combined_action)
                except Exception as e:
                    print(f"AIOne: Error predicting action: {e}")
                messages_IMU = []
                # #message_Shoot['isFire'] = False
                # df.to_csv('IMU_debug_data.csv', mode='a', index=False, header=not pd.io.common.file_exists('IMU_debug_data.csv'))
                # action_number = self.predictor.get_action(df)
                # #print(f"ACTION NUMBER IS: {action_number}")
                # action = ACTIONS[action_number]


                # print(f"Predicted action is: {action}")
                # combined_action = action + ":1"
                # self.P1_action_queue.put(combined_action)
                # #message_Shoot['isFire'] = False


            # try:
            #     message_ankle = self.P1_ankle_queue.get(timeout = 0.005)
            #     print("Received item from ankle queue")
                
            #     if message_ankle:
            #         self.message_ankle_count += 1
                    
            #         if (self.message_ankle_count >= 60):
            #             action = 'soccer'
            #             print_message('AIOne', f"Received '{message_ankle}' from RelayServer")
            #             combined_action = action + ":1"
            #             self.P1_action_queue.put(combined_action)
            #             self.message_ankle_count = 0

            #         continue  # Skip to the next loop since ankle  takes priority
            # except queue.Empty:
            #     pass 



    

     
    # def run(self):
    #   messages_IMU = []
    #   packet_number = 25
    #   #bitstream_path = "/home/xilinx/BITSTREAM/design_1.bit"
    #   #overlay = Overlay(bitstream_path)
    #   #model = predict_model(overlay)
    #   while True:
    #     try:
    #         message_IMU = self.P1_IMU_queue.get(timeout=0.5) #get from Shoot_queue
    #         print("Received item from IMU queue")
    #     except queue.Empty:
    #         message_IMU = None
    #         print("NO item received as IMU queue is empty")

    #     try:
    #         message_Shoot = self.P1_fire_queue.get(timeout=0.005) #get from Shoot_queue
    #         print("Received item from fire queue")
    #     except queue.Empty:
    #         message_Shoot = None
    #         print("NO item received as fire queue is empty")
        
    #     if message_Shoot is not None and message_Shoot['isFired']: #only care abt isHit and not isFired 
    #        action = 'gun'
    #        number = 1
    #        combined_action = action + ":1"
    #        self.P1_action_queue.put(combined_action) 
      