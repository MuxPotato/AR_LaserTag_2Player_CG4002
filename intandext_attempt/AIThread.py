from threading import Thread
from queue import Queue
import random
from Color import print_message

#ACTIONS = ["shoot", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"] 
#TODO Figure out eval server for non AI actions 

ACTIONS = ["bomb", "reload", "basket", "soccer", "volley", "bowl"]

class AI(Thread):
    def __init__(self,IMU_queue,phone_action_queue,shoot_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue
        self.shoot_queue = shoot_queue 
        self.phone_action_queue = phone_action_queue
    
    def run(self):
      while True:
        message = self.IMU_queue.get() #Check if the data is valid (sth to do with shoot), the start of move detection code should be here too. Only call to the AI if the detection of move is valid.
        shoot_data = self.shoot_queue.get()
        print_message('AI Thread',f"Received '{message}' from RelayServer")
        print()
        #action = "bomb"
        action = self.random_action()
        combined_action = action + ":1"
        self.action_queue.put(action)
        self.phone_action_queue.put(combined_action)
        

    def random_action(self):
      return random.choice(ACTIONS)
    
    