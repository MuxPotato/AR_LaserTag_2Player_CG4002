from threading import Thread
from queue import Queue
import random
ACTIONS = ["gun", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"]

class AI(Thread):
    def __init__(self,IMU_queue,action_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue
        self.action_queue = action_queue
    
    def run(self):
      while True:
        message = self.IMU_queue.get()
        print("-"*30)
        print(f"AI: Received '{message}' from RelayServer")
        action = self.random_action()
        self.action_queue.put(action)
        

    def random_action(self):
      return random.choice(ACTIONS)
    
    