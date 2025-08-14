#pragma once
#include <stdint.h>

// ===== ピン番号 =====
#define LIGHT_SENSOR_PIN 6
#define PUMP_PIN 2
#define SOIL_SENSOR_PIN 1
#define BME_SDA_PIN 7
#define BME_SCL_PIN 8
#define INA_SDA_PIN 39
#define INA_SCL_PIN 38
#define RESET_BTN_PIN 41

// ===== 制御系のデフォルト値 =====
#define DEF_SOIL_DRY_THRESHOLD 1900
#define DEF_PUMP_ON_MS 5000
#define DEF_INIT_WAIT_MS 5000
#define DEF_DEEP_SLEEP_WAIT_MS 1000
#define DEF_SLEEP_SEC 600 // DeepSleep間隔(秒)

// ===== 通信系のデフォルト値 =====
#define SENSOR_SND_UPORT 12345
#define WIFI_CONNECT_TIMEOUT_MS 10000

// ===== プロビジョン =====
#define PRV_SND_RCV_UPORT 12346
#define PROVISION_WINDOW_MS 60000UL // 1分

// ===== センサーデータ構造体 =====
struct SensorData {
  float temp, hum, pres;
  int   light, soil;
  float busVoltage, current_mA, power_mW;
};

// ===== アプリケーション設定構造体 =====
struct AppConfig {
  uint16_t soilDryThreshold;
  uint16_t pumpOnMs;
  uint16_t initWaitMs;
  uint16_t deepSleepWaitMs;
  uint32_t sleepSec;
  uint16_t udpPort;
  char ssid[32];
  char pass[64];
  char udpAddr[16];
};

void loadConfig(AppConfig &cfg);
void saveConfig(const AppConfig &cfg);
