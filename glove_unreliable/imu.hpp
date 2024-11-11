#include <TimerFreeTone.h>
#include <Wire.h>

#define ACC_LSB 16384
#define BUZZER_PIN 5
#define ACCELEROMETER_THRESHOLD 2.0
#define GYRO_LSB 131
#define IMU_SETUP_DELAY 5000
#define IMU_TRANSMISSION_COOLDOWN_PERIOD 3000
#define NUM_CALIBRATION_ROUNDS 2000
#define THRESHOLD_START_TONE 880
#define THRESHOLD_END_TONE 500
#define THRESHOLD_TONE_DURATION 500
#define IS_GLOVE false

enum ImuTransmissionState {
  WAITING_FOR_ACTION = 0,
  TRANSMITTING_ACTION = 1,
  COOLDOWN = 2,
};

void update_imu_data(void);

float getRootSumSquareOf(const float accX, const float accY, const float accZ) {
  float sumSquare = accX * accX;
  sumSquare += accY * accY;
  sumSquare += accZ * accZ;
  return (double) sqrt(sumSquare);
}

float getAccDegreesOf(int16_t accValue) {
  return ((float) accValue) / ACC_LSB;
}

float getGyroDegreesOf(int16_t gyroValue) {
  return ((float) gyroValue) / GYRO_LSB;
}

float getAnalyticsFor(int16_t accX, int16_t accY, int16_t accZ,
    int16_t gyroX, int16_t gyroY, int16_t gyroZ) {
  return getRootSumSquareOf(getAccDegreesOf(accX), getAccDegreesOf(accY), getAccDegreesOf(accZ));
}
