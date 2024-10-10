from collections import deque
import queue
import sys
import threading
import traceback
from beetle import GunBeetle, GloveBeetle, VestBeetle
from utils import bcolors

class InternalMainThread(threading.Thread):
    MAIN_BLUNO_MAC_ADDR_LIST = [
        # Below must be player 1 IMU(glove) Beetle
        "F4:B8:5E:42:61:62",
        # Below must be player 1 vest Beetle
        "F4:B8:5E:42:6D:75",
        # Below must be player 1 gun Beetle
        "F4:B8:5E:42:67:6E",

        # Below must be player 2 IMU(glove) Beetle
        "B4:99:4C:89:1B:FD",
        # Below must be player 2 vest Beetle
        "D0:39:72:DF:CA:F2",
        # Below must be player 2 gun Beetle
        "F4:B8:5E:42:6D:0E",

        # Extra 1
        "B4:99:4C:89:1B:FD",
        # Extra 2
        "B4:99:4C:89:18:1D"
    ]

    def __init__(self, outgoing_glove_queue, outgoing_game_state_queue, incoming_game_state_queue):
        super().__init__()
        self.outgoing_glove_queue = outgoing_glove_queue
        self.outgoing_game_state_queue = outgoing_game_state_queue
        self.incoming_game_state_queue = incoming_game_state_queue
        self.incoming_glove_queue = queue.Queue()
        self.outgoing_gun_queue = queue.Queue()
        self.beetles = []

    def run(self):
        self.main()

    def quit(self):
        for mBeetle in self.beetles:
            mBeetle.quit()

    def main(self):
        colors = [bcolors.BRIGHT_RED, bcolors.BRIGHT_GREEN, bcolors.BRIGHT_BLUE, bcolors.BRIGHT_MAGENTA, bcolors.BRIGHT_CYAN, bcolors.BRIGHT_WHITE]
        try:
            index = 0

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            glove1Beetle = GloveBeetle(beetle_addr, self.outgoing_glove_queue, self.incoming_glove_queue, colors[index])
            self.beetles.append(glove1Beetle)
            glove1Beetle.start()
            index += 1

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            gun1Beetle = GunBeetle(beetle_addr, self.outgoing_gun_queue, self.incoming_game_state_queue, colors[index])
            self.beetles.append(gun1Beetle)
            gun1Beetle.start()
            index += 1

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            vest1Beetle = VestBeetle(beetle_addr, self.outgoing_game_state_queue, self.outgoing_gun_queue, colors[index])
            self.beetles.append(vest1Beetle)
            vest1Beetle.start()
            index += 1

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            glove2Beetle = GloveBeetle(beetle_addr, self.outgoing_glove_queue, self.incoming_glove_queue, colors[index])
            self.beetles.append(glove2Beetle)
            glove2Beetle.start()
            index += 1

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            gun2Beetle = GunBeetle(beetle_addr, self.outgoing_gun_queue, self.incoming_game_state_queue, colors[index])
            self.beetles.append(gun2Beetle)
            gun2Beetle.start()
            index += 1

            beetle_addr = InternalMainThread.MAIN_BLUNO_MAC_ADDR_LIST[index]
            vest2Beetle = VestBeetle(beetle_addr, self.outgoing_game_state_queue, self.outgoing_gun_queue, colors[index])
            self.beetles.append(vest2Beetle)
            vest2Beetle.start()
            index += 1
            
            for thisBeetle in self.beetles:
                thisBeetle.join()
        except Exception as exc:
            traceback.print_exception(exc)

if __name__=="__main__":
    sys.exit(0)
    