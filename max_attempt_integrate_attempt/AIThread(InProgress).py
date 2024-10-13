from threading import Thread
from queue import Queue
import random
from AI import AI
from Color import print_message

#ACTIONS = ["shoot", "shield", "bomb", "reload", "basket", "soccer", "volley", "bowl"] 
#TODO Figure out eval server for non AI actions 


#format to send out = action + ":player_id" 

ACTIONS = ["bomb", "reload", "basket", "soccer", "volley", "bowl"]
UPPERTHRESHOLD = 2.2
LOWERTHRESHOLD = 0.2



class AI(Thread):
    def __init__(self,IMU_queue,phone_action_queue):
        Thread.__init__(self)
        self.IMU_queue = IMU_queue

        self.phone_action_queue = phone_action_queue
    
    def detectAction(self, message):
        if LOWERTHRESHOLD <= message['gyro'][0] <= UPPERTHRESHOLD and LOWERTHRESHOLD <= message['gyro'][1] <= UPPERTHRESHOLD and LOWERTHRESHOLD <= message['gyro'][2] <= UPPERTHRESHOLD:
            return True
        return False
    
    def sendData(self, messages):
       return #AI call
       
    def run(self):
      while True:
        message = self.IMU_queue.get() #detection of move start should be here, only send to AI if valid
        if message['isFire'] and message['isHit']: #only care abt is fired and not is hit
           self.phone_action_queue.put(combined_action) #
        print_message('AI Thread',f"Received '{message}' from RelayServer")
        print()
        if self.detectAction(message):
           messages = []
           while len(messages) < 30:
              messages.append(message)
           action = self.sendData(messages)
           self.phone_action_queue.put(combined_action)

    
    