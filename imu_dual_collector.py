# Constants
import csv
import os
import queue
import sys
import threading
from beetle import GloveUnreliableBeetle
from internal_utils import BEETLE_MAC_ADDR, bcolors

GLOVE_IMU_BEETLE = BEETLE_MAC_ADDR.P1_GLOVE.value
GLOVE2_IMU_BEETLE = BEETLE_MAC_ADDR.P2_GLOVE.value

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
    def __init__(self, glove_queue: queue.Queue, glove2_queue: queue.Queue):
        super().__init__()
        self.stop_event = threading.Event()
        self.glove_queue = glove_queue
        self.glove2_queue = glove2_queue
        self.has_synced = False

    def run(self):
        while not self.stop_event.is_set():
            try:
                if not self.has_synced and self.glove_queue.qsize() > 0 and self.glove2_queue.qsize() > 0:
                    with self.glove_queue.mutex:
                        self.glove_queue.queue.clear()
                    with self.glove2_queue.mutex:
                        self.glove2_queue.queue.clear()
                    print(f"""{bcolors.BRIGHT_YELLOW}Synced both queues{bcolors.ENDC}""")
                    self.has_synced = True
            except queue.Empty:
                continue
    
    def stop(self):
        self.stop_event.set()

if __name__=="__main__":
    glove_imu_beetle = None
    glove2_imu_beetle = None
    synchroniser = None
    glove_color = bcolors.BRIGHT_CYAN
    glove2_color = bcolors.BRIGHT_GREEN
    dummy_incoming_queue = queue.Queue()
    glove_imu_collector_queue = queue.Queue()
    glove2_imu_collector_queue = queue.Queue()
    try:
        synchroniser = QueueSynchroniser(glove_imu_collector_queue, glove2_imu_collector_queue)
        synchroniser.start()
        glove_imu_beetle = GloveUnreliableBeetle(GLOVE_IMU_BEETLE,
                glove_imu_collector_queue, dummy_incoming_queue, glove_color)
        glove_imu_beetle.start()
        glove2_imu_beetle = GloveUnreliableBeetle(GLOVE2_IMU_BEETLE, 
                glove2_imu_collector_queue, dummy_incoming_queue, glove2_color)
        glove2_imu_beetle.start()
        while True:
            pass
    except KeyboardInterrupt:
        if glove_imu_beetle:
            glove_imu_beetle.quit()
            glove_imu_beetle.join()
        if glove2_imu_beetle:
            glove2_imu_beetle.quit()
            glove2_imu_beetle.join()
        if synchroniser:
            synchroniser.stop()
            synchroniser.join()
        
        filename1 = input("Enter the filename to dump IMU data for glove 1: ")
        label1 = input("Enter the label for glove 1: ")
        filename2 = input("Enter the filename to dump IMU data for glove 2: ")
        label2 = input("Enter the label for glove 2: ")
        dump_imu_data_to_csv(filename1, label1, glove_imu_collector_queue, "glove")
        dump_imu_data_to_csv(filename2, label2, glove2_imu_collector_queue, "glove2")
    sys.exit(0)
    