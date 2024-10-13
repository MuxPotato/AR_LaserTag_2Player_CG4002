from threading import Thread
import queue
import random
import time 
import json
from Color import print_message

class GameEngine(Thread):
    def __init__(self, eval_queue, viz_queue,shoot_queue,phone_action_queue,from_eval_queue,phone_response_queue):
        Thread.__init__(self)
        
        self.eval_queue = eval_queue 
        self.viz_queue = viz_queue 
        self.phone_action_queue = phone_action_queue  # New queue for phone actions
        self.from_eval_queue = from_eval_queue
        self.phone_response_queue = phone_response_queue
        self.shoot_queue = shoot_queue 
        # self.to_rs_queue = to_rs_queue (new queue for sending back hp and ammo to relay server)



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



    def get_player_state(self, player_id):
        if player_id == 1:
            return [self.hp_p1, self.shieldHp_p1, self.shieldCharges_p1, self.bullets_p1, self.bomb_p1, self.deaths_p1,
                    self.hp_p2, self.shieldHp_p2, self.shieldCharges_p2, self.bullets_p2, self.bomb_p2, self.deaths_p2]
        elif player_id == 2:
            return [self.hp_p2, self.shieldHp_p2, self.shieldCharges_p2, self.bullets_p2, self.bomb_p2, self.deaths_p2,
                    self.hp_p1, self.shieldHp_p1, self.shieldCharges_p1, self.bullets_p1, self.bomb_p1, self.deaths_p1]
        else:
            print("Game Engine: Invalid player_id")
            return []

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


    def process_phone_action(self, action):
        print_message('Game Engine', f"Processing phone action: {action}")

        

        # If not an FOV response, proceed with regular action processing
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
                success = self.shoot(player_id)
                if success:
                    if player_id == 1:
                        action_p1 = "shoot"
                    else:
                        action_p2 = "shoot"
                else:
                    # Indicate failure directly by setting action_p1 or action_p2
                    if player_id == 1:
                        action_p1 = "shoot_fail"
                        action_p2 = "none"  # For clarity, explicitly set the other action to "none"
                    else:
                        action_p2 = "shoot_fail"
                        action_p1 = "none"

                print_message('Game Engine', f"Player {player_id} attempted to shoot: {'Success' if success else 'Failed'}")

            elif action_type == "reload":
                success = self.reload(player_id)
                if success:
                    if player_id == 1:
                        action_p1 = "reload"
                    else:
                        action_p2 = "reload"
                else:
                    # Indicate failure directly by setting action_p1 or action_p2
                    if player_id == 1:
                        action_p1 = "reload_fail"
                        action_p2 = "none"
                    else:
                        action_p2 = "reload_fail"
                        action_p1 = "none"

                print_message('Game Engine', f"Player {player_id} attempted to reload: {'Success' if success else 'Failed'}")



            elif action_type in ["basket", "soccer", "volley", "bowl", "bomb"]:
                # Handle the AI actions for sports or bomb
                print_message('Game Engine', f"Player {player_id} performed AI action: {action_type}")
                if player_id == 1:
                    action_p1 = action_type
                else:
                    action_p2 = action_type
                print_message('Game Engine', f"Player {player_id} performed {action_type}")

            elif action_type == "ai_damage":
                self.take_ai_damage(player_id)
                if player_id == 1:
                    action_p1 = "ai_damage"
                else:
                    action_p2 = "ai_damage"
                print_message('Game Engine', f"Player {player_id} took AI damage")

            elif action_type == "bullet_damage":
                success = self.take_bullet_damage(player_id)
                if success:
                    if player_id == 1:
                        action_p1 = "bullet_damage"
                    else:
                        action_p2 = "bullet_damage"
                print_message('Game Engine', f"Player {player_id} took bullet damage: {'Success' if success else 'Failed'}")

            elif action_type == "rain_bomb_damage":
                success = self.take_rain_bomb_damage(player_id)
                if success:
                    if player_id == 1:
                        action_p1 = "rain_bomb_damage"
                    else:
                        action_p2 = "rain_bomb_damage"
                print_message('Game Engine', f"Player {player_id} took rain bomb damage: {'Success' if success else 'Failed'}")

            elif action_type == "shield":
                success = self.charge_shield(player_id)
                if success:
                    if player_id == 1:
                        action_p1 = "shield"
                    else:
                        action_p2 = "shield"
                else:
                    # Indicate failure directly by setting action_p1 or action_p2
                    if player_id == 1:
                        action_p1 = "shield_fail"
                        action_p2 = "none"  # Explicitly set the other action to "none" for clarity
                    else:
                        action_p2 = "shield_fail"
                        action_p1 = "none"

                print_message('Game Engine', f"Player {player_id} attempted to charge their shield: {'Success' if success else 'Failed'}")


            elif action_type == "update_ui":
                # Set both player actions to "update_ui" so that both players update their UI
                action_p1 = "update_ui"
                action_p2 = "update_ui"
                print_message('Game Engine', f"UI update requested for both players.")
                
            else:
                print_message('Game Engine', f"Unknown action type: {action_type}")
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


 

    def process_phone_response_and_return_prev_action(self, response):
        print_message('Game Engine', f"Processing phone response: {response}")

        # Parse response in the format: "player_id:isPrevActionAnAIAction:isPrevActionHit:PrevAction:isRainBombHit"
        try:
            parts = response.split(":")
            if len(parts) != 5:
                raise ValueError("Response does not have the expected number of parts")

            player_id = int(parts[0])
            is_ai_action = int(parts[1])
            is_hit = int(parts[2])
            prev_action = parts[3]  # Keeping this as a string for now
            is_rain_bomb_hit = int(parts[4])


            # Check if the previous action is not an AI action (e.g., "shoot", "reload", "charge_shield")
            if prev_action in ["shoot", "reload", "charge_shield"]:
                # Ignore is_ai_action and is_hit for these actions
                is_ai_action = 0
                is_hit = 0
                print_message('Game Engine', f"Non-AI action detected ('{prev_action}'), ignoring is_ai_action and is_hit fields.")



            # Check if the previous action was an AI action and if it hit the opponent
            if is_ai_action == 1:
                if is_hit == 1:
                    print_message('Game Engine', f"Player {player_id}'s AI action hit the opponent")

                    opponent_id = 2 if player_id == 1 else 1

                    # Check if the previous action was a bomb and apply the appropriate damage
                    if prev_action == "bomb":
                        print_message('Game Engine', f"Player {opponent_id} takes rain bomb damage")
                        self.take_rain_bomb_damage(opponent_id)
                    else:
                        print_message('Game Engine', f"Player {opponent_id} takes AI damage")
                        self.take_ai_damage(opponent_id)
                else:
                    print_message('Game Engine', f"Player {player_id}'s AI action missed the opponent")


            # Check if a rain bomb hit is indicated
            if is_rain_bomb_hit == 1:
                print_message('Game Engine', f"Player {player_id}'s rain bomb hit the opponent")
                opponent_id = 2 if player_id == 1 else 1
                self.take_rain_bomb_damage(opponent_id)

            # Update game state after processing the response
            self.update_both_players_game_state()

        except ValueError as e:
            print_message('Game Engine', f"Error: {e}")
        except Exception as e:
            print_message('Game Engine', f"Error processing phone response - {e}")

        return prev_action


        
    def prepare_eval_server_format(self, player_id, prev_action):
        return {
            'player_id': player_id,
            'action': prev_action,
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



    def is_curr_game_state_diff_from_updated(self, updated_game_state_str):
        """
        Compare the current game state with the updated game state string.
        Returns True if any differences are found; otherwise, returns False.
        """
        try:
            # Parse the JSON string into a dictionary
            updated_game_state = json.loads(updated_game_state_str)

            # Access the current game state
            current_game_state = {
                "p1": {
                    "hp": self.hp_p1,
                    "bullets": self.bullets_p1,
                    "bombs": self.bomb_p1,
                    "shield_hp": self.shieldHp_p1,
                    "deaths": self.deaths_p1,
                    "shields": self.shieldCharges_p1,
                },
                "p2": {
                    "hp": self.hp_p2,
                    "bullets": self.bullets_p2,
                    "bombs": self.bomb_p2,
                    "shield_hp": self.shieldHp_p2,
                    "deaths": self.deaths_p2,
                    "shields": self.shieldCharges_p2,
                }
            }

            # Iterate through player 1's stats
            for key in current_game_state["p1"]:
                if current_game_state["p1"][key] != updated_game_state["p1"][key]:
                    print(f"Difference found for p1 - {key}: {current_game_state['p1'][key]} != {updated_game_state['p1'][key]}")
                    return True

            # Iterate through player 2's stats
            for key in current_game_state["p2"]:
                if current_game_state["p2"][key] != updated_game_state["p2"][key]:
                    print(f"Difference found for p2 - {key}: {current_game_state['p2'][key]} != {updated_game_state['p2'][key]}")
                    return True

            # If no differences are found, return False
            return False

        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse updated game state - {e}")
            return True
        except KeyError as e:
            print(f"Error: Key missing in updated game state - {e}")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return True




    def update_current_game_state(self, updated_game_state_str):
        """
        Update the current game state with the values from the updated game state string.
        """

        try:
            # Parse the JSON string into a dictionary
            updated_game_state = json.loads(updated_game_state_str)

            # Update player 1's stats
            self.hp_p1 = updated_game_state["p1"]["hp"]
            self.bullets_p1 = updated_game_state["p1"]["bullets"]
            self.bomb_p1 = updated_game_state["p1"]["bombs"]
            self.shieldHp_p1 = updated_game_state["p1"]["shield_hp"]
            self.deaths_p1 = updated_game_state["p1"]["deaths"]
            self.shieldCharges_p1 = updated_game_state["p1"]["shields"]

            # Update player 2's stats
            self.hp_p2 = updated_game_state["p2"]["hp"]
            self.bullets_p2 = updated_game_state["p2"]["bullets"]
            self.bomb_p2 = updated_game_state["p2"]["bombs"]
            self.shieldHp_p2 = updated_game_state["p2"]["shield_hp"]
            self.deaths_p2 = updated_game_state["p2"]["deaths"]
            self.shieldCharges_p2 = updated_game_state["p2"]["shields"]

            print("Current game state successfully updated.")

        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse updated game state - {e}")
        except KeyError as e:
            print(f"Error: Missing key in updated game state - {e}")
        except Exception as e:
            print(f"Error: {e}")


    

    def run(self):
        while True:
        

            # Handle phone action if it's not empty
            if not self.phone_action_queue.empty():
                phone_action = self.phone_action_queue.get()
                
                print_message('Game Engine', f"Received action '{phone_action}' from phone action queue")
                viz_format = self.process_phone_action(phone_action)
                
    
                self.viz_queue.put(viz_format)

                print("Game Engine: Waiting for phone to reply")
                phone1_response = self.phone_response_queue.get()


                # There should be two phone response but right now, 1 player game so we only put 1 first
                # phone2_response = self.phone_response_queue.get()

                #TODO: Here there will be a problem for the two player game, bcs for the 1 player game, we know which player
                #      is doing the action, but for two player game, identifying which player does the action is tricky
                player1_prev_action = self.process_phone_response_and_return_prev_action(phone1_response)

                # More code below to handle eval_server response but I left this out
                eval_server_format = self.prepare_eval_server_format(1, player1_prev_action)
                print("Game Engine: Putting into eval_queue to be sent to eval_server")
                self.eval_queue.put(eval_server_format)


                print("Game Engine: Waiting for from_eval_queue")
                updated_game_state = self.from_eval_queue.get()
                print("updated game state:")
                print(updated_game_state)

                # # Check if the eval server's game state differs from the current game state
                if self.is_curr_game_state_diff_from_updated(updated_game_state):

                    print("Game Engine: curr game state diff from eval game state")

                    print("Game Engine: updating curr game state to eval game state")
                    self.update_current_game_state(updated_game_state)
                    
                    # Put "update_ui" into the phone response queue to update the UI without triggering an action
                    viz_format = self.process_phone_action("update_ui")
                    self.viz_queue.put(viz_format)

            
