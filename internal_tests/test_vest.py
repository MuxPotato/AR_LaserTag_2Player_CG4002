import sys
sys.path.append('..')

import csv
import os
import queue
from beetle import VestBeetle
from internal_utils import bcolors

# Constants
VEST_BEETLE = "F4:B8:5E:42:6D:75"

def dump_vest_data_to_csv(vest_queue):
    filename = input("Enter the filename to dump IMU data to: ")
    target_file_path = f"""vest_data/{filename}.csv"""
    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
    with open(target_file_path, 'w') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(["Player ID", "isShot", "Label"])
        for vest_data in vest_queue.queue:
            csv_writer.writerow([vest_data.playerID, vest_data.isShot, filename])

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
    