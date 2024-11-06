import struct
import sys
import threading

import anycrc
sys.path.append('..')

import csv
import os
import queue
from beetle import VestBeetle
from internal_utils import BEETLE_MAC_ADDR, bcolors

# Constants
VEST_BEETLE = BEETLE_MAC_ADDR.P2_VEST.value

def dump_vest_data_to_csv(vest_queue):
    filename = input("Enter the filename to dump IMU data to: ")
    target_file_path = f"""vest_data/{filename}.csv"""
    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
    with open(target_file_path, 'w') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(["Player ID", "isHit", "Label"])
        for vest_data in vest_queue.queue:
            csv_writer.writerow([vest_data.playerID, vest_data.isHit, filename])

class DummyVestUpdate(threading.Thread):
    def __init__(self, vest_data_queue, game_state_update_queue):
        super().__init__()
        self.vest_data_queue = vest_data_queue
        self.game_state_update_queue = game_state_update_queue
        self.stop_event = threading.Event()
        self.player_hp = 100
        self.seq_num = 0

    def quit(self):
        self.stop_event.set()

    def run(self):
        while not self.stop_event.is_set():
            if not self.vest_data_queue.empty():
                vest_data = self.vest_data_queue.get()
                if vest_data.isHit:
                    self.player_hp -= 5
                    if self.player_hp == 0:
                        print(f"Player {vest_data.playerID} is dead! Respawning")
                        self.player_hp = 100
                    else:
                        print(f"Player {vest_data.playerID} got hit! HP: {self.player_hp}")
                    update_packet_data = bytearray([1, self.player_hp])
                    update_packet_data.extend([0] * 14)
                    crc8 = anycrc.Model('CRC8-SMBUS')
                    crc8.update(int(6).to_bytes())
                    crc8.update(self.seq_num.to_bytes(length = 2, byteorder = 'little'))
                    data_crc = crc8.update(update_packet_data)
                    update_packet = struct.pack("=BH16sB", 6, self.seq_num, update_packet_data, data_crc)
                    self.seq_num += 1

if __name__=="__main__":
    vest_beetle = None
    color = bcolors.BRIGHT_CYAN
    dummy_incoming_queue = queue.Queue()
    vest_collector_queue = queue.Queue()
    try:
        vest_beetle = VestBeetle(VEST_BEETLE, vest_collector_queue, dummy_incoming_queue, color)
        vest_beetle.start()
        while True:
            pass
    except KeyboardInterrupt:
        if vest_beetle:
            vest_beetle.quit()
            vest_beetle.join()
        dump_vest_data_to_csv(vest_collector_queue)
    sys.exit(0)
    