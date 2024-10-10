from collections import deque
import sys
import threading
from beetle import Beetle, GunBeetle, VestBeetle
from utils import bcolors

class MainThread(threading.Thread):
    MAIN_BLUNO_MAC_ADDR_LIST = [
        # Below must be IMU(glove) Beetle
        "F4:B8:5E:42:67:6E",
        # Below must be vest Beetle
        "F4:B8:5E:42:6D:75",
        # Below must be gun Beetle
        "B4:99:4C:89:1B:FD"
    ]

    def __init__(self, outgoing_imu_queue, outgoing_game_state_queue, incoming_game_state_queue):
        super().__init__()
        self.outgoing_imu_queue = outgoing_imu_queue
        self.outgoing_game_state_queue = outgoing_game_state_queue
        self.incoming_game_state_queue = incoming_game_state_queue
        self.incoming_glove_queue = deque()
        self.outgoing_gun_queue = deque()

    def run(self):
        self.main()

    def main(self):
        beetles = []
        colors = [bcolors.OKGREEN, bcolors.OKCYAN, bcolors.FAIL]
        try:
            index = 0
            for i in range(3):
                beetle_addr = MainThread.MAIN_BLUNO_MAC_ADDR_LIST[i]
                thisBeetle = None
                if i == 0:
                    # IMU(glove) Beetle
                    thisBeetle = Beetle(beetle_addr, colors[index], self.outgoing_imu_queue, self.incoming_glove_queue)
                elif i == 1:
                    # Vest Beetle
                    thisBeetle = VestBeetle(beetle_addr, colors[index], self.outgoing_game_state_queue, self.outgoing_gun_queue)
                elif i == 2:
                    # Gun Beetle
                    thisBeetle = GunBeetle(beetle_addr, colors[index], self.outgoing_gun_queue, self.incoming_game_state_queue)
                thisBeetle.start()
                beetles.append(thisBeetle)
                index += 1
            for thisBeetle in beetles:
                thisBeetle.join()
        except KeyboardInterrupt:
            for mBeetle in beetles:
                mBeetle.quit()

if __name__=="__main__":
    sys.exit(0)
    