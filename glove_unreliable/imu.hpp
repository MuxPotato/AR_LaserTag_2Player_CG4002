#include <Wire.h>

#define ACC_LSB 16384
#define NUM_CALIBRATION_ROUNDS 2000
#define IMU_SETUP_DELAY 5000

void update_imu_data(void);
