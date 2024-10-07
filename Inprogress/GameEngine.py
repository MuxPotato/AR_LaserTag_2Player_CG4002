from threading import Thread
from queue import Queue
import random
from Color import print_message

class GameEngine(Thread):
     def __init__(self,game_engine_queue,action_queue, eval_queue, viz_queue,from_eval_queue):
        Thread.__init__(self)
        self.game_engine_queue = game_engine_queue
        self.action_queue = action_queue
        self.eval_queue = eval_queue 
        self.viz_queue = viz_queue 
        self.from_eval_queue = from_eval_queue


         # Player 1 Variables
        self.hp_p1 = 100
        self.shieldHp_p1 = 0
        self.shieldCharges_p1 = 3
        self.bullets_p1 = 6
        self.bomb_p1 = 2
        self.deaths_p1 = 0

        # Player 2 Variables
        self.hp_p2 = 100
        self.shieldHp_p2 = 0
        self.shieldCharges_p2 = 3
        self.bullets_p2 = 6
        self.bomb_p2 = 2
        self.deaths_p2 = 0

        # Damage constants
        self.hp_bullet = 5
        self.hp_bomb = 5

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
    
     def shoot(self, player_id):
            if player_id == 1 and self.bullets_p1 > 0:
                self.bullets_p1 -= 1
                self.update_both_players_game_state()
                return True
            elif player_id == 2 and self.bullets_p2 > 0:
                self.bullets_p2 -= 1
                self.update_both_players_game_state()
                return True
            return False

     def reload(self, player_id):
        if player_id == 1:
            if self.bullets_p1 == 0:  # Only reload if bullets are empty
                self.bullets_p1 = 6
                self.update_both_players_game_state()
                return True
            else:
                return False  # Cannot reload if bullets are not empty
        elif player_id == 2:
            if self.bullets_p2 == 0:  # Only reload if bullets are empty
                self.bullets_p2 = 6
                self.update_both_players_game_state()
                return True
            else:
                return False  # Cannot reload if bullets are not empty
        return False

     def take_ai_damage(self, player_id):
            if player_id == 1:
                if self.shieldHp_p1 > 0:
                    self.shieldHp_p1 = max(0, self.shieldHp_p1 - 10)
                else:
                    self.hp_p1 = max(0, self.hp_p1 - 10)
                if self.hp_p1 <= 0:
                    self.respawn(player_id)
            elif player_id == 2:
                if self.shieldHp_p2 > 0:
                    self.shieldHp_p2 = max(0, self.shieldHp_p2 - 10)
                else:
                    self.hp_p2 = max(0, self.hp_p2 - 10)
                if self.hp_p2 <= 0:
                    self.respawn(player_id)
            self.update_both_players_game_state()


        # Right now this function does nth
     def update_both_players_game_state(self):
            self.log_game_state()

     def log_game_state(self):
            game_state_info = (
                "[Game State Log] Player 1 Stats:\n"
                f"HP: {self.hp_p1}, Shield HP: {self.shieldHp_p1}, Shield Charges: {self.shieldCharges_p1}, Bullets: {self.bullets_p1}, Bombs: {self.bomb_p1}, Deaths: {self.deaths_p1}\n"
                "[Game State Log] Player 2 Stats:\n"
                f"HP: {self.hp_p2}, Shield HP: {self.shieldHp_p2}, Shield Charges: {self.shieldCharges_p2}, Bullets: {self.bullets_p2}, Bombs: {self.bomb_p2}, Deaths: {self.deaths_p2}\n"
            )
            print(game_state_info)

     def respawn(self, player_id):
            if player_id == 1:
                self.hp_p1 = 100
                self.bomb_p1 = 2
                self.shieldCharges_p1 = 3
                self.shieldHp_p1 = 0
                self.bullets_p1 = 6
                self.deaths_p1 += 1
            elif player_id == 2:
                self.hp_p2 = 100
                self.bomb_p2 = 2
                self.shieldCharges_p2 = 3
                self.shieldHp_p2 = 0
                self.bullets_p2 = 6
                self.deaths_p2 += 1

     def take_bullet_damage(self, player_id):
            if player_id == 1:
                if self.shieldHp_p1 > 0:
                    self.shieldHp_p1 = max(0, self.shieldHp_p1 - self.hp_bullet)
                else:
                    self.hp_p1 = max(0, self.hp_p1 - self.hp_bullet)

                if self.hp_p1 <= 0:
                    self.respawn(player_id)
                self.update_both_players_game_state()
                return True
            elif player_id == 2:
                if self.shieldHp_p2 > 0:
                    self.shieldHp_p2 = max(0, self.shieldHp_p2 - self.hp_bullet)
                else:
                    self.hp_p2 = max(0, self.hp_p2 - self.hp_bullet)

                if self.hp_p2 <= 0:
                    self.respawn(player_id)
                self.update_both_players_game_state()
                return True
            return False

     def take_rain_bomb_damage(self, player_id):
            if player_id == 1:
                if self.shieldHp_p1 > 0:
                    self.shieldHp_p1 = max(0, self.shieldHp_p1 - self.hp_bomb)
                else:
                    self.hp_p1 = max(0, self.hp_p1 - self.hp_bomb)

                if self.hp_p1 <= 0:
                    self.respawn(player_id)
                self.update_both_players_game_state()
                return True
            elif player_id == 2:
                if self.shieldHp_p2 > 0:
                    self.shieldHp_p2 = max(0, self.shieldHp_p2 - self.hp_bomb)
                else:
                    self.hp_p2 = max(0, self.hp_p2 - self.hp_bomb)

                if self.hp_p2 <= 0:
                    self.respawn(player_id)
                self.update_both_players_game_state()
                return True
            return False

     def charge_shield(self, player_id):
            if player_id == 1 and self.shieldCharges_p1 > 0:
                self.shieldHp_p1 = 30
                self.shieldCharges_p1 -= 1
                self.update_both_players_game_state()
                return True
            elif player_id == 2 and self.shieldCharges_p2 > 0:
                self.shieldHp_p2 = 30
                self.shieldCharges_p2 -= 1
                self.update_both_players_game_state()
                return True
            return False



    
     def process_phone_action(self, action):
        print_message('Game Engine', f"Processing phone action: {action}")

        action_p1 = "none"  # Default action for player 1
        action_p2 = "none"  # Default action for player 2

        # Validate and split the action string (e.g., "shoot:1", "reload:2")
        if ":" in action:
            parts = action.split(":")
            if len(parts) != 2:
                print_message('Game Engine', f"Invalid action format: {action}")
                return None

            action_type, player_id = parts
            player_id = int(player_id)

            if action_type == "shoot":
                success = self.shoot(2)
                success = self.take_bullet_damage(2)
                if success:
                    if player_id == 1:
                        action_p1 = "shoot"
                    else:
                        action_p2 = "shoot"
                print_message('Game Engine', f"Player {player_id} attempted to shoot: {'Success' if success else 'Failed'}")

            elif action_type == "reload":
                success = self.reload(2)
                if success:
                    if player_id == 1:
                        action_p1 = "reload"
                    else:
                        action_p2 = "reload"
                print_message('Game Engine', f"Player {player_id} attempted to reload: {'Success' if success else 'Failed'}")

            elif action_type in ["basket", "soccer", "volley", "bowl"]:
                # Handle the AI actions for sports or bomb
                print_message('Game Engine', f"Player {player_id} performed AI action: {action_type}")
                
                ## Temp for 1-player game
                self.take_ai_damage(2)
                if player_id == 1:
                    action_p1 = action_type
                else:
                    action_p2 = action_type
                print_message('Game Engine', f"Player {player_id} performed {action_type}")
                print_message('Game Engine', f"Player 2 took AI damage")

            elif action_type == "bomb":
                success = self.take_rain_bomb_damage(2)
                if success:
                    if player_id == 1:
                        action_p1 = "rain_bomb_damage"
                    else:
                        action_p2 = "rain_bomb_damage"
                print_message('Game Engine', f"Player {2} took rain bomb damage: {'Success' if success else 'Failed'}")

            elif action_type == "shield":
                success = self.charge_shield(2)
                if success:
                    if player_id == 1:
                        action_p1 = "shield"
                    else:
                        action_p2 = "shield"
                print_message('Game Engine', f"Player {player_id} charged their shield: {'Success' if success else 'Failed'}")

            
        else:
            print_message('Game Engine', "Invalid action format received from phone")

        # After processing the action, update the game state for the visualizer with actions included
        viz_format = (
            f"p1_hp:{self.hp_p1},p1_bombs:{self.bomb_p1},p1_shieldCharges:{self.shieldCharges_p1},"
            f"p1_shieldHp:{self.shieldHp_p1},p1_bullets:{self.bullets_p1},p1_deaths:{self.deaths_p1},"
            f"p2_hp:{self.hp_p2},p2_bombs:{self.bomb_p2},p2_shieldCharges:{self.shieldCharges_p2},"
            f"p2_shieldHp:{self.shieldHp_p2},p2_bullets:{self.bullets_p2},p2_deaths:{self.deaths_p2},"
            f"p1_action:{action_p1},p2_action:{action_p2}"
        )

        return viz_format



     def run(self):
         while True:
            IMU_info = self.game_engine_queue.get()
            #print(f"GameEngine: Received '{IMU_info}' from RelayServer")
            print("_"*30)
            print_message('Game Engine',"Received message from RelayServer")
            print()
            actionformat = self.action_queue.get()
            action = actionformat.split(":")[0]
            print_message('Game Engine',f"Received '{action}' from AI")

            
            # i need 2 formats one is for putting in the viz_queue and one is for putting in the eval_queue 
            # first is viz_queue format 
            viz_format = self.process_phone_action(actionformat) 
        

            
            # next is to eval server format, use the game state data to fill in the game_state, use action from what AI sent 
            eval_server_format = {
                'player_id': 1,
                'action': action,
                'game_state': {
                    'p1': {
                        'hp': self.hp_p1,
                        'bullets': self.bullets_p1,
                        'bombs': self.bomb_p1,
                        'shield_hp': self.shieldHp_p1,
                        'deaths': self.deaths_p1,
                        'shields': self.shieldCharges_p1
                    },
                    'p2': {  
                        'hp': self.hp_p2,
                        'bullets': self.bullets_p2,
                        'bombs': self.bomb_p2,
                        'shield_hp': self.shieldHp_p2,
                        'deaths': self.deaths_p2,
                        'shields': self.shieldCharges_p2
                    }
                }
            }
            # put into eval queue and viz queue 
            self.viz_queue.put(viz_format)
            
            self.eval_queue.put(eval_server_format)
            updated_game_state = self.from_eval_queue.get()
            print_message('Game Engine',f"Received updated game state from eval server")

            # need to send the updated game state to phone 

        

