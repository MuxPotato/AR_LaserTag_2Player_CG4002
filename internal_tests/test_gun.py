import sys
sys.path.append('..')

import csv
import os
import queue
from beetle import GunBeetle
from internal_utils import BEETLE_MAC_ADDR, bcolors

# Constants
GUN_BEETLE = BEETLE_MAC_ADDR.P2_GUN.value

def dump_gun_data_to_csv(gun_queue):
    filename = input("Enter the filename to dump IMU data to: ")
    target_file_path = f"""gun_data/{filename}.csv"""
    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
    with open(target_file_path, 'w') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(["Player ID", "isFired", "Label"])
        for gun_data in gun_queue.queue:
            csv_writer.writerow([gun_data.playerID, gun_data.isFired, filename])

if __name__=="__main__":
    gun_beetle = None
    color = bcolors.BRIGHT_CYAN
    dummy_incoming_queue = queue.Queue()
    gun_collector_queue = queue.Queue()
    try:
        gun_beetle = GunBeetle(GUN_BEETLE, gun_collector_queue, dummy_incoming_queue, color)
        gun_beetle.start()
        while True:
            pass
    except KeyboardInterrupt:
        if gun_beetle:
            gun_beetle.quit()
            gun_beetle.join()
        dump_gun_data_to_csv(gun_collector_queue)
    sys.exit(0)
    