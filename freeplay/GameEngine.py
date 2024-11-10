from threading import Thread
import queue
import random
import time 
import json
from Color import print_message

class GameEngine(Thread):
    def __init__(self, P1_action_queue,P2_action_queue,viz_queue, phone_response_queue,shot_queue ,to_rs_queue ):
        Thread.__init__(self)
        
        self.viz_queue = viz_queue 
        self.P1_action_queue = P1_action_queue 
        self.P2_action_queue = P2_action_queue
        self.phone_response_queue = phone_response_queue
        self.shot_queue = shot_queue
        self.to_rs_queue = to_rs_queue # queue for sending back hp and ammo to relay server

        self.hp_p1 = 100
        self.shieldHp_p1 = 0
        self.shieldCharges_p1 = 3
        self.bullets_p1 = 6
        self.bomb_p1 = 2
        self.deaths_p1 = 0
        self.hp_p2 = 100
        self.shieldHp_p2 = 0
        self.shieldCharges_p2 = 3
        self.bullets_p2 = 6
        self.bomb_p2 = 2
        self.deaths_p2 = 0
        self.hp_bullet = 5
        self.hp_bomb = 5
        self.ACTIONTIMEOUT = 20
        self.LOGOUT_FAILSAFE_TURNS = 20
        self.PHONE_RESPONSE_TIMEOUT = 5
        self.game_turns_passed = 0
        self.P1_ai_predicted_action = ""
        self.P2_ai_predicted_action = ""

    
    ###########################
    ### Start of Game Logic ###
    ###########################
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
            self.log_game_state()
            return True
        elif player_id == 2 and self.bullets_p2 > 0:
            self.bullets_p2 -= 1
            self.log_game_state()
            return True
        return False
    
    def bomb(self, player_id):
        if player_id == 1 and self.bomb_p1 > 0:
            self.bomb_p1 -= 1
            self.log_game_state()
            return True
        elif player_id == 2 and self.bomb_p1 > 0:
            self.bomb_p2 -= 1
            self.log_game_state()
            return True
        return False


    def reload(self, player_id):
        if player_id == 1:
            if self.bullets_p1 == 0:  # Only reload if bullets are empty
                self.bullets_p1 = 6
                self.log_game_state()
                return True
            else:
                return False  # Cannot reload if bullets are not empty
        elif player_id == 2:
            if self.bullets_p2 == 0:  # Only reload if bullets are empty
                self.bullets_p2 = 6
                self.log_game_state()
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
        self.log_game_state()

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
            self.log_game_state()
            return True
        elif player_id == 2:
            if self.shieldHp_p2 > 0:
                self.shieldHp_p2 = max(0, self.shieldHp_p2 - self.hp_bullet)
            else:
                self.hp_p2 = max(0, self.hp_p2 - self.hp_bullet)

            if self.hp_p2 <= 0:
                self.respawn(player_id)
            self.log_game_state()
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
            self.log_game_state()
            return True
        elif player_id == 2:
            if self.shieldHp_p2 > 0:
                self.shieldHp_p2 = max(0, self.shieldHp_p2 - self.hp_bomb)
            else:
                self.hp_p2 = max(0, self.hp_p2 - self.hp_bomb)

            if self.hp_p2 <= 0:
                self.respawn(player_id)
            self.log_game_state()
            return True
        return False

    def charge_shield(self, player_id):
        if player_id == 1:
            if self.shieldCharges_p1 > 0 and self.shieldHp_p1 <= 0:
                self.shieldHp_p1 = 30
                self.shieldCharges_p1 -= 1
                self.log_game_state()
                return True
        elif player_id == 2:
            if self.shieldCharges_p2 > 0 and self.shieldHp_p2 <= 0:
                self.shieldHp_p2 = 30
                self.shieldCharges_p2 -= 1
                self.log_game_state()
                return True
        return False

    def format_relayclient_packet_isHit(self, id, isHit):
        packet = {
            'id': id, 
            'isHit': isHit # isHit is always 1; 0 never happens, we will never need to send a packet to the vest if we do not need to ring the buzzer
        }
        return packet
    
    def format_relayclient_packet_hp_bullets(self,id):
        if id == 1:
            hp = self.hp_p1
            bullets = self.bullets_p1
        elif id == 2:
            hp = self.hp_p2
            bullets = self.bullets_p2
        else:
            raise ValueError(f"Invalid player ID: {id}")

        # Format the packet as requested
        packet = {
            'id': id,
            'hp' : hp,
            'bullets' : bullets
        }
        return packet
    
    def log_game_state(self):
        game_state_info = (
            "[Game State Log] Player 1 Stats:\n"
            f"HP: {self.hp_p1}, Shield HP: {self.shieldHp_p1}, Shield Charges: {self.shieldCharges_p1}, Bullets: {self.bullets_p1}, Bombs: {self.bomb_p1}, Deaths: {self.deaths_p1}\n"
            "[Game State Log] Player 2 Stats:\n"
            f"HP: {self.hp_p2}, Shield HP: {self.shieldHp_p2}, Shield Charges: {self.shieldCharges_p2}, Bullets: {self.bullets_p2}, Bombs: {self.bomb_p2}, Deaths: {self.deaths_p2}\n"
        )
        print(game_state_info)
    
    #########################
    ### END OF GAME LOGIC ###
    #########################


    def get_action_type_and_player_id(self, action):
        parts = action.split(":")
        if len(parts) != 2:
            print_message('Game Engine', f"Invalid action format: {action}")
            return None, None
        return parts
        

    def process_phone_action_and_get_viz_format(self, action):
        print_message('Game Engine', f"Processing phone action: {action}")

        
        action_p1 = "none"  # Default action for player 1
        action_p2 = "none"  # Default action for player 2

        if ":" not in action: 
            print_message('Game Engine', f"Invalid action format: {action}")
            return None

        
        
        action_type, player_id = self.get_action_type_and_player_id(action)
        player_id = int(player_id)

            
        if action_type == "gun":
            success = self.shoot(player_id)
            if success:
                if player_id == 1:
                    action_p1 = "gun"
                    shot_result = self.check_shot_queue_for_hit(1) # func takes in shooting player's id
                    if shot_result:
                        print_message('Game Engine', "Player 1's shot hit Player 2!")
                        self.take_bullet_damage(2)
                        self.to_rs_queue.put(self.format_relayclient_packet_isHit(2, 1)) # player 2 got shot
                    else:
                        print_message('Game Engine', "Player 1's shot missed Player 2!")
                else: # player_id = 2
                    action_p2 = "gun"
                    shot_result = self.check_shot_queue_for_hit(2) # func takes in shooting player's id
                    if shot_result:
                        print_message('Game Engine', "Player 2's shot hit Player 1!")
                        self.take_bullet_damage(1)
                        self.to_rs_queue.put(self.format_relayclient_packet_isHit(1, 1)) # player 1 got shot
                    else:
                        print_message('Game Engine', "Player 2's shot missed Player 1!")
            else:
                # Indicate failure directly by setting action_p1 or action_p2
                if player_id == 1:
                    action_p1 = "gun_fail"
                    action_p2 = "none"  # For clarity, explicitly set the other action to "none"
                else:
                    action_p2 = "gun_fail"
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



        elif action_type in ["basket", "soccer", "volley", "bowl"]:
            # Handle the AI actions for sports or bomb
            print_message('Game Engine', f"Player {player_id} performed AI action: {action_type}")
            if player_id == 1:
                action_p1 = action_type
            else:
                action_p2 = action_type
            print_message('Game Engine', f"Player {player_id} performed {action_type}")
        
        elif action_type == "bomb":
            success = self.bomb(player_id)
            if success:
                if player_id == 1:
                    action_p1 = "bomb"
                else:
                    action_p2 = "bomb"
            else:
                # Indicate failure directly by setting action_p1 or action_p2
                if player_id == 1:
                    action_p1 = "bomb_fail"
                    action_p2 = "none"  # For clarity, explicitly set the other action to "none"
                else:
                    action_p2 = "bomb_fail"
                    action_p1 = "none"

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


        elif action_type == "logout":
            if player_id == 1:
                action_p1 = "logout"
            else:
                action_p2 = "logout"
    
            print_message('Game Engine', f"Player {player_id} logout")
            
        
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

   



    def check_shot_queue_for_hit(self, shooting_player_id):
        """Check the shot queue to see if the opponent was hit within a 0.5-second timeout."""
        opponent_id = 2 if shooting_player_id == 1 else 1
        start_time = time.time()
        wait_time = 1  # 0.5 seconds to check for opponent hit

        while time.time() - start_time < wait_time:
            # Check if there's something in the queue
            if not self.shot_queue.empty():
                shot = self.shot_queue.get()
                # Check if the shot belongs to the opponent and meets the criteria
                if shot["playerID"] == opponent_id and shot["isHit"] == True:
                    # Opponent was shot
                    
                    return True  # Shot hit the opponent
            else:
                # If queue is empty, wait briefly before checking again
                time.sleep(0.05)  # Avoid busy waiting, sleep for a short time (50 ms)

        # Timeout expired, no valid shot found
        return False

 

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

            prev_action = prev_action.strip()  # Remove leading/trailing whitespace
            self.P1_ai_predicted_action = self.P1_ai_predicted_action.strip()
            self.P2_ai_predicted_action = self.P2_ai_predicted_action.strip()  # Do the same for P2_ai_predicted_action
            

            # Debugging output for verification
            print_message('Game Engine', f"Received player_id: {player_id}, prev_action: {prev_action}")
            print_message('Game Engine', f"P1_ai_predicted_action: {self.P1_ai_predicted_action}, P2_ai_predicted_action: {self.P2_ai_predicted_action}")

            # We overwrite whatever phone action gives us with the action predicted from AI
            if player_id == 1:
                if prev_action != self.P1_ai_predicted_action:
                    print_message('Game Engine', f"Mismatch for Player 1: phone prev action: {prev_action} not same as P1_ai_predicted_action: {self.P1_ai_predicted_action}")
                    prev_action = self.P1_ai_predicted_action
            elif player_id == 2:
                if prev_action != self.P2_ai_predicted_action:
                    print_message('Game Engine', f"Mismatch for Player 2: phone prev action: {prev_action} not same as P2_ai_predicted_action: {self.P2_ai_predicted_action}")
                    prev_action = self.P2_ai_predicted_action
            else:
                print_message('Game Engine', f"Unexpected player_id: {player_id}")



            

            # Check if the previous action is not an AI action (e.g., "shoot", "reload", "charge_shield")
            if prev_action in ["gun", "reload", "charge_shield"]:
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


            # Check if any rain bomb hit is indicated
            if is_rain_bomb_hit > 0:
                print_message('Game Engine', f"Player {player_id}'s rain bomb hit the opponent {is_rain_bomb_hit} time(s)")
                opponent_id = 2 if player_id == 1 else 1

                # Loop to apply damage based on the number of hits
                for _ in range(is_rain_bomb_hit):
                    self.take_rain_bomb_damage(opponent_id)

            # Update game state after processing the response
            self.log_game_state()

        except ValueError as e:
            print_message('Game Engine', f"Error: {e}")
        except Exception as e:
            print_message('Game Engine', f"Error processing phone response - {e}")

        return prev_action


   



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


    def clear_queue(self, queue):
        if not queue.empty():
            print("Debug: Clearing non-empty queue")
        while not queue.empty():
            queue.get()


    def extract_action(self,phone_action):
        return phone_action.split(":")[0]
    
 


    def send_to_phone_and_wait_for_phone_response_with_retries(self, viz_queue, phone_response_queue, viz_format, max_retries, player_id):
        for attempt in range(max_retries):
            try:
                print(f"Game Engine: Sending message to phone, attempt {attempt + 1}")
                viz_queue.put(viz_format)

                print(f"Game Engine: Waiting for phone reply, attempt {attempt + 1}")
                phone_response = phone_response_queue.get(timeout=self.PHONE_RESPONSE_TIMEOUT)
                print("Game Engine: Received response from phone")
                return phone_response  # Successful response, return it

            except queue.Empty:
                print(f"Game Engine: No response received, attempt {attempt + 1} timed out")

        # After max_retries, fallback to the default response
        print("Game Engine: Max retries reached, using default response")

        # Format of response is 
        # string Response = $"{player_id}:{isPrevActionAnAIAction}:{isPrevActionHit}:{prevActionString}:{rainBombHitCount}"
        # I assume that the probabilty of hitting an AI action i.e. players see each other is a lot higher than not seeing
        # Also i assume rain bomb is 0
        default_response = f"{player_id}:1:1:basket:0"
        return default_response


    def run(self):
        while True:
            if not self.P1_action_queue.empty():
                
                


                #####################################
                ### Start of Player 1 Action Code ###
                #####################################
                phone_action1 = self.P1_action_queue.get()

                if (phone_action1 == "logout:1" and self.game_turns_passed <= self.LOGOUT_FAILSAFE_TURNS):
                    print_message('Game Engine', 'Logout detected before turn 21, reverting to default action')
                    phone_action1 = "basket:1"
                
                print_message('Game Engine', f"Received action '{phone_action1}' from phone action queue player 1")
                viz_format1 = self.process_phone_action_and_get_viz_format(phone_action1)
                phone1_response = self.send_to_phone_and_wait_for_phone_response_with_retries(self.viz_queue,self.phone_response_queue,viz_format1,max_retries=2,player_id=1)
                
                
                
                viz_format = self.process_phone_action_and_get_viz_format("update_ui:1")
                self.viz_queue.put(viz_format)


                # Sending packets back to vest and gun
                print_message('Game Engine',"Sending info back to relay client")
                self.to_rs_queue.put(self.format_relayclient_packet_hp_bullets(1))       
                self.to_rs_queue.put(self.format_relayclient_packet_hp_bullets(2))
                
                #####################################
                ###  End of Player 1 Action Code  ###
                #####################################

            

            if not self.P2_action_queue.empty():

                #####################################
                ### Start of Player 2 Action Code ###
                #####################################
                phone_action2 = self.P2_action_queue.get()


                if (phone_action2 == "logout:2" and self.game_turns_passed <= self.LOGOUT_FAILSAFE_TURNS):
                    print_message('Game Engine', 'Logout detected before turn 21, reverting to default action')
                    phone_action2 = "basket:2"
                
                print_message('Game Engine', f"Received action '{phone_action2}' from phone action queue player 2")
                viz_format2 = self.process_phone_action_and_get_viz_format(phone_action2)
                
                phone2_response = self.send_to_phone_and_wait_for_phone_response_with_retries(self.viz_queue,self.phone_response_queue,viz_format2,max_retries=2,player_id=2)
    

               

                ## End of Player 2 Action Code ##

              

                # Update UI
                viz_format = self.process_phone_action_and_get_viz_format("update_ui:1")
                self.viz_queue.put(viz_format)


                # Sending packets back to vest and gun
                self.to_rs_queue.put(self.format_relayclient_packet_hp_bullets(1))
                print_message('Game Engine',"Sending info back to relay client")
                self.to_rs_queue.put(self.format_relayclient_packet_hp_bullets(2))
                print_message('Game Engine',"Sending info back to relay client")

                #####################################
                ###  End of Player 2 Action Code  ###
                #####################################

                


        



