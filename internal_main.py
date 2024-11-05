import queue
import sys
import threading
import traceback
from beetle import AnkleUnreliableBeetle, GloveUnreliableBeetle, GunBeetle, VestBeetle
from internal_utils import BEETLE_MAC_ADDR, GAME_STATE_QUEUE_TIMEOUT, GunUpdatePacket, VestUpdatePacket, bcolors

class GameStateHandler(threading.Thread):
    def __init__(self, incoming_game_state_queue: queue.Queue, gun_update_queue: queue.Queue, vest_update_queue: queue.Queue):
        super().__init__()
        self.incoming_game_state_queue = incoming_game_state_queue
        # TODO: Add 2 queues(1 gun, 1 vest) per player
        self.gun_update_queue = gun_update_queue
        self.vest_update_queue = vest_update_queue
        self.stop_event = threading.Event()

    def quit(self):
        self.stop_event.set()

    def run(self):
        self.main()

    def main(self):
        while not self.stop_event.is_set():
            try:
                if self.incoming_game_state_queue.empty():
                    continue
                new_game_state = self.incoming_game_state_queue.get(timeout = GAME_STATE_QUEUE_TIMEOUT)
                if new_game_state is None:
                    continue
                # TODO: Add parser that checks player ID to determine which queue to put the update in
                player_id = new_game_state["id"]
                if self.is_gun_game_state(new_game_state):
                    # TODO: Remove debug printing line below
                    print(f"""{bcolors.BRIGHT_YELLOW}Gun game state update received{bcolors.ENDC}""")
                    gun_update_packet = GunUpdatePacket(player_id = player_id,
                            bullets = new_game_state["bullets"])
                    # TODO: Check which player ID and put packet in the right Beetle's queue
                    self.gun_update_queue.put(gun_update_packet)
                elif self.is_vest_game_state(new_game_state):
                    # TODO: Remove debug printing line below
                    print(f"""{bcolors.BRIGHT_YELLOW}Vest game state update received{bcolors.ENDC}""")
                    vest_update_packet = VestUpdatePacket(player_id = player_id, 
                            is_hit = new_game_state["isHit"], player_hp = new_game_state["hp"])
                    # TODO: Check which player ID and put packet in the right Beetle's queue
                    self.vest_update_queue.put(vest_update_packet)
                else:
                    print(f"""Unknown game state received from relay server: {new_game_state}""")
            except queue.Empty:
                continue
            except KeyboardInterrupt as exc:
                # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
                raise exc
            except Exception as exc:
                traceback.print_exception(exc)
        
    def is_gun_game_state(self, game_state: dict):
        return 'bullets' in game_state.keys()
    
    def is_vest_game_state(self, game_state: dict):
        return 'isShot' in game_state.keys()

class InternalMainThread(threading.Thread):
    MAIN_BLUNO_MAC_ADDR_LIST = [
        # Below must be player 1 IMU(glove) Beetle
        "F4:B8:5E:42:61:62",
        # Below must be player 1 IMU(ankle) Beetle
        "D0:39:72:DF:CA:F2",
        # Below must be player 1 gun Beetle
        "B4:99:4C:89:18:72",
        # Below must be player 1 vest Beetle
        "F4:B8:5E:42:6D:0E",

        # Below must be player 2 IMU(glove) Beetle
        "B4:99:4C:89:1B:FD",
        # Below must be player 2 IMU(ankle) Beetle
        "34:08:E1:2A:08:61",
        # Below must be player 2 gun Beetle
        "F4:B8:5E:42:67:2B",
        # Below must be player 2 vest Beetle
        "F4:B8:5E:42:6D:75",

        # Extra 1
#        "F4:B8:5E:42:67:6E",
        # Extra 2
#        "B4:99:4C:89:18:1D",
    ]

    def __init__(self, outgoing_p1_ankle_queue, outgoing_p1_glove_queue, outgoing_p2_ankle_queue, outgoing_p2_glove_queue, outgoing_game_state_queue, incoming_game_state_queue):
        super().__init__()
        self.outgoing_p1_ankle_queue = outgoing_p1_ankle_queue
        self.outgoing_p1_glove_queue = outgoing_p1_glove_queue
        self.outgoing_p2_ankle_queue = outgoing_p2_ankle_queue
        self.outgoing_p2_glove_queue = outgoing_p2_glove_queue
        self.outgoing_game_state_queue = outgoing_game_state_queue
        self.incoming_game_state_queue = incoming_game_state_queue
        self.incoming_glove_queue = queue.Queue()
        # TODO: Add 1 gun queue per player
        self.to_gun_queue = queue.Queue()
        # TODO: Add 1 vest queue per player
        self.to_vest_queue = queue.Queue()
        self.beetles = []
        self.game_state_handler = GameStateHandler(self.incoming_game_state_queue, 
                self.to_gun_queue, self.to_vest_queue)

    def run(self):
        print("Starting Internal's main thread...")
        self.main()

    def quit(self):
        # TODO: Switch to 1 shared threading.Event instead of calling .quit() on every single Thread
        for mBeetle in self.beetles:
            mBeetle.quit()
        self.game_state_handler.quit()

    def main(self):
        try:
            beetle_addr = BEETLE_MAC_ADDR.P1_GLOVE.value
            glove1Beetle = GloveUnreliableBeetle(beetle_addr, self.outgoing_p1_glove_queue, self.incoming_glove_queue, bcolors.BRIGHT_BLUE)
            self.beetles.append(glove1Beetle)
            glove1Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P1_ANKLE.value
            ankle1Beetle = AnkleUnreliableBeetle(beetle_addr, self.outgoing_p1_ankle_queue, self.incoming_glove_queue, bcolors.BLUE)
            self.beetles.append(ankle1Beetle)
            ankle1Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P1_GUN.value
            gun1Beetle = GunBeetle(beetle_addr, self.outgoing_game_state_queue, self.to_gun_queue, bcolors.BRIGHT_RED)
            self.beetles.append(gun1Beetle)
            gun1Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P1_VEST.value
            vest1Beetle = VestBeetle(beetle_addr, self.outgoing_game_state_queue, self.to_vest_queue, bcolors.BRIGHT_CYAN)
            self.beetles.append(vest1Beetle)
            vest1Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P2_GLOVE.value
            glove2Beetle = GloveUnreliableBeetle(beetle_addr, self.outgoing_p2_glove_queue, self.incoming_glove_queue, bcolors.BRIGHT_MAGENTA)
            self.beetles.append(glove2Beetle)
            glove2Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P2_ANKLE.value
            ankle2Beetle = AnkleUnreliableBeetle(beetle_addr, self.outgoing_p2_ankle_queue, self.incoming_glove_queue, bcolors.MAGENTA)
            self.beetles.append(ankle2Beetle)
            ankle2Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P2_GUN.value
            gun2Beetle = GunBeetle(beetle_addr, self.outgoing_game_state_queue, self.to_gun_queue, bcolors.BRIGHT_GREEN)
            self.beetles.append(gun2Beetle)
            gun2Beetle.start()

            beetle_addr = BEETLE_MAC_ADDR.P2_VEST.value
            vest2Beetle = VestBeetle(beetle_addr, self.outgoing_game_state_queue, self.to_vest_queue, bcolors.BRIGHT_WHITE)
            self.beetles.append(vest2Beetle)
            vest2Beetle.start()

            # Start separate thread to wait for incoming game state from game engine
            self.game_state_handler.start()
            
            for thisBeetle in self.beetles:
                thisBeetle.join()
            self.game_state_handler.join()
            print("All Beetle threads have now terminated")
        except KeyboardInterrupt as exc:
            # Explicitly catch and rethrow KeyboardInterrupt to ensure caller can handle CTRL+C
            raise exc
        except Exception as exc:
            traceback.print_exception(exc)

if __name__=="__main__":
    sys.exit(0)
    