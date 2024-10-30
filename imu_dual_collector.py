# Constants
import csv
import os
import queue
import sys
import threading
from beetle import GloveUnreliableBeetle
from internal_utils import bcolors

# Set 1 Glove IMU
GLOVE_IMU_BEETLE = "F4:B8:5E:42:61:62"
# Set 1 Ankle strap
ANKLE_IMU_BEETLE = "D0:39:72:DF:CA:F2"

# Set 2 Glove IMU
#GLOVE_IMU_BEETLE = "B4:99:4C:89:1B:FD"
# Set 2 Ankle strap
#ANKLE_IMU_BEETLE = "34:08:E1:2A:08:61"

def dump_imu_data_to_csv(filename: str, label: str, imu_queue: queue.Queue, imu_type: str = "glove"):
    target_file_path = f"""imu_data/{filename}_{imu_type}.csv"""
    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
    with open(target_file_path, 'w') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(["Accel X", "Accel Y", "Accel Z", "Gyro X", "Gyro Y", "Gyro Z", "Label"])
        for imu_data in imu_queue.queue:
            # Expand accel and gyro arrays before writing all 6 floats into 1 row
            csv_writer.writerow([*imu_data.accel, *imu_data.gyro, label])

class QueueSynchroniser(threading.Thread):
    def __init__(self, glove_queue: queue.Queue, ankle_queue: queue.Queue):
        super().__init__()
        self.stop_event = threading.Event()
        self.glove_queue = glove_queue
        self.ankle_queue = ankle_queue
        self.has_synced = False

    def run(self):
        while not self.stop_event.is_set():
            try:
                if not self.has_synced and self.glove_queue.qsize() > 0 and self.ankle_queue.qsize() > 0:
                    with self.glove_queue.mutex:
                        self.glove_queue.queue.clear()
                    with self.ankle_queue.mutex:
                        self.ankle_queue.queue.clear()
                    print(f"""{bcolors.BRIGHT_YELLOW}Synced both queues{bcolors.ENDC}""")
                    self.has_synced = True
            except queue.Empty:
                continue
    
    def stop(self):
        self.stop_event.set()

if __name__=="__main__":
    glove_imu_beetle = None
    ankle_imu_beetle = None
    synchroniser = None
    glove_color = bcolors.BRIGHT_CYAN
    ankle_color = bcolors.BRIGHT_GREEN
    dummy_incoming_queue = queue.Queue()
    glove_imu_collector_queue = queue.Queue()
    ankle_imu_collector_queue = queue.Queue()
    try:
        synchroniser = QueueSynchroniser(glove_imu_collector_queue, ankle_imu_collector_queue)
        synchroniser.start()
        glove_imu_beetle = GloveUnreliableBeetle(GLOVE_IMU_BEETLE,
                glove_imu_collector_queue, dummy_incoming_queue, glove_color)
        glove_imu_beetle.start()
        ankle_imu_beetle = GloveUnreliableBeetle(ANKLE_IMU_BEETLE, 
                ankle_imu_collector_queue, dummy_incoming_queue, ankle_color)
        ankle_imu_beetle.start()
        while True:
            pass
    except KeyboardInterrupt:
        if glove_imu_beetle:
            glove_imu_beetle.quit()
            glove_imu_beetle.join()
        if ankle_imu_beetle:
            ankle_imu_beetle.quit()
            ankle_imu_beetle.join()
        if synchroniser:
            synchroniser.stop()
            synchroniser.join()
        
        filename = input("Enter the filename to dump IMU data to: ")
        label = input("Enter the label for the current data: ")
        dump_imu_data_to_csv(filename, label, glove_imu_collector_queue, "glove")
        dump_imu_data_to_csv(filename, label, ankle_imu_collector_queue, "ankle")
    sys.exit(0)
    