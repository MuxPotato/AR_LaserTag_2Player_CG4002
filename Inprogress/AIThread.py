from threading import Thread
from queue import Queue
import random
from Color import print_message

ACTIONS = ["gun", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"]

class AI(Thread):
    def __init__(self,IMU_queue,action_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue
        self.action_queue = action_queue
    
    def run(self):
      while True:
        message = self.IMU_queue.get()
        print_message('AI Thread',f"Received '{message}' from RelayServer")
        print()
        #action = "bomb"
        action = self.random_action()
        combined_message = action + ":1" 
        self.action_queue.put(combined_message)
        

    def random_action(self):
      return random.choice(ACTIONS)
    
    