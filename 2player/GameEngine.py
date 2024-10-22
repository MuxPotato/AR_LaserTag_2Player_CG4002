from threading import Thread
import queue
import random
import time 
import json
from Color import print_message

class GameEngine(Thread):
    def __init__(self, P1_action_queue,P2_action_queue,viz_queue, eval_queue, from_eval_queue , phone_response_queue,shot_queue ,to_rs_queue ):
        Thread.__init__(self)
        
        self.eval_queue = eval_queue 
        self.from_eval_queue = from_eval_queue
        self.viz_queue = viz_queue 
        self.P1_action_queue = P1_action_queue 
        self.P2_action_queue = P2_action_queue
        self.phone_response_queue = phone_response_queue
        self.shot_queue = shot_queue
        self.to_rs_queue = to_rs_queue # queue for sending back hp and ammo to relay server
