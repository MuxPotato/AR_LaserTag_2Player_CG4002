from threading import Thread
from queue import Queue
import random
from Color import print_message


#TODO  get from gun queue 


#ACTIONS = ["shoot", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"] 


#ACTIONS = ["bomb", "reload", "basket", "soccer", "volley", "bowl", "shield", "gun"]
ACTIONS = ["bomb", "basket"] #, "shield", "gun"]


player_data = {
    'playerID': 1,
    'accel': [0.1, 0.2, 0.3],
    'gyro': [0.01, 0.02, 0.03],
    'isFire': True, #if this is true dont sent AI IMU data 
    'isHit': False
}

class AI(Thread):
    def __init__(self,IMU_queue,shoot_queue,phone_action_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue
        self.shoot_queue = shoot_queue 
        self.phone_action_queue = phone_action_queue
    
    def run(self):
      while True:
        message = self.IMU_queue.get()
        print_message('AI Thread',f"Received '{message}' from RelayServer")
        print()
        #action = "bomb"
        action = self.random_action()
        combined_action = action + ":1"
        self.phone_action_queue.put(combined_action)
        

    def random_action(self):
      return random.choice(ACTIONS)
    
    