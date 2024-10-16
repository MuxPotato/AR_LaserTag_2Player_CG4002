# Constants
import csv
import os
import queue
import sys
import time
from beetle import GloveBeetle, GloveUnreliableBeetle
from internal_utils import bcolors

IMU_BEETLE = "F4:B8:5E:42:61:62"

def dump_imu_data_to_csv(imu_queue):
    filename = input("Enter the filename to dump IMU data to: ")
    target_file_path = f"""imu_data/{filename}.csv"""
    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
    label = input("Enter the label for the current data: ")
    with open(target_file_path, 'w') as output_csv:
        csv_writer = csv.writer(output_csv)
        csv_writer.writerow(["Accel X", "Accel Y", "Accel Z", "Gyro X", "Gyro Y", "Gyro Z", "Label"])
        for imu_data in imu_queue.queue:
            # Expand accel and gyro arrays before writing all 6 floats into 1 row
            csv_writer.writerow([*imu_data.accel, *imu_data.gyro, label])

if __name__=="__main__":
    imu_beetle = None
    color = bcolors.BRIGHT_CYAN
    dummy_incoming_queue = queue.Queue()
    imu_collector_queue = queue.Queue()
    try:
        imu_beetle = GloveUnreliableBeetle(IMU_BEETLE, imu_collector_queue, dummy_incoming_queue, color)
        imu_beetle.start()
        while True:
            pass
    except KeyboardInterrupt:
        if imu_beetle:
            imu_beetle.quit()
            imu_beetle.join()
        dump_imu_data_to_csv(imu_collector_queue)
    sys.exit(0)
    