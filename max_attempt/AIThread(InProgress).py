from threading import Thread
from queue import Queue
import random
from Color import print_message

#ACTIONS = ["shoot", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"] 
#TODO Figure out eval server for non AI actions 

ACTIONS = ["bomb", "reload", "basket", "soccer", "volley", "bowl"]
UPPERTHRESHOLD = 2.2
LOWERTHRESHOLD = 0.2

player_data = {
    'playerID': 1,
    'accel': [0.1, 0.2, 0.3],
    'gyro': [0.01, 0.02, 0.03],
    'isFire': True,
    'isHit': False
}

class AI(Thread):
    def __init__(self,IMU_queue,phone_action_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue

        self.phone_action_queue = phone_action_queue
    
    def detectAction(self, message):
        if LOWERTHRESHOLD <= message['gyro'][0] <= UPPERTHRESHOLD and LOWERTHRESHOLD <= message['gyro'][1] <= UPPERTHRESHOLD and LOWERTHRESHOLD <= message['gyro'][2] <= UPPERTHRESHOLD:
            return True
        return False
    
    def run(self):
      while True:
        message = self.IMU_queue.get() #detection of move start should be here, only send to AI if valid
        print_message('AI Thread',f"Received '{message}' from RelayServer")
        print()
        #action = "bomb"
        action = self.random_action()
        combined_action = action + ":1"
        if #detection of move valid:
          self.phone_action_queue.put(combined_action)
        

    def random_action(self):
      return random.choice(ACTIONS)
    
    