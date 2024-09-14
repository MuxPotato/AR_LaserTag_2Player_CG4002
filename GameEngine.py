from threading import Thread
from queue import Queue
import random


class GameEngine(Thread):
     def __init__(self,game_engine_queue,action_queue, eval_queue, viz_queue):
        Thread.__init__(self)
        self.game_engine_queue = game_engine_queue
        self.action_queue = action_queue
        self.eval_queue = eval_queue 
        self.viz_queue = viz_queue 

     def random_game_state(self):
        return {
            'player': 1,
            'hp': random.randint(10, 90),
            'bullets': random.randint(0, 6),
            'bombs': random.randint(0, 2),
            'shield_hp': random.randint(0, 30),
            'deaths': random.randint(0, 3),
            'shields': random.randint(0, 3)
    }

     def run(self):
         while True:
            IMU_info = self.game_engine_queue.get()
            #print(f"GameEngine: Received '{IMU_info}' from RelayServer")
            print("_"*30)
            print(f"GameEngine: Received message from RelayServer")
            print()
            action = self.action_queue.get()
            print(f"GameEngine: Received '{action}' from AI")
            # i need 2 formats one is for putting in the viz_queue and one is for putting in the eval_queue 
            # first is viz_queue format 
            game_state = self.random_game_state() # make dummy game state data but use action from what AI sent 
            viz_format = (f"player:{game_state['player']},health:{game_state['hp']},bullets:{game_state['bullets']},"
              f"bombs:{game_state['bombs']},shield_hp:{game_state['shield_hp']},deaths:{game_state['deaths']},"
              f"shields:{game_state['shields']},action:{action}")

            
            # next is to eval server format, use the game state data to fill in the game_state, use action from what AI sent 
            eval_server_format = {
                'player_id': 1,
                'action': action,
                'game_state': {
                    'p1': {
                        'hp': game_state['hp'],
                        'bullets': game_state['bullets'],
                        'bombs': game_state['bombs'],
                        'shield_hp': game_state['shield_hp'],
                        'deaths': game_state['deaths'],
                        'shields': game_state['shields']
                    },
                    'p2': {  # Dummy data for another player
                        'hp': random.randint(10, 90),
                        'bullets': random.randint(0, 6),
                        'bombs': random.randint(0, 2),
                        'shield_hp': random.randint(0, 30),
                        'deaths': random.randint(0, 3),
                        'shields': random.randint(0, 3)
                    }
                }
            }
            # put into eval queue and viz queue 
            self.viz_queue.put(viz_format)
            self.eval_queue.put(eval_server_format)
        

