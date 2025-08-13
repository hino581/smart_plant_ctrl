#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>
#include <WiFi.h>
#include <WiFiUdp.h>

/** @file main.cpp
 *  @brief 植物モニター：センサ測定 → UDP送信 → Deep Sleep
 */

// ===== Wi-Fi設定 =====
const char* ssid     = "Fight Club";      ///< WiFi SSID
const char* password = "soap1999";        ///< WiFi パスワード

// ===== UDP送信先 =====
const char* udpAddress = "192.168.0.214"; ///< UDP受信先IPアドレス
const int udpPort = 12345;                ///< UDPポート番号
WiFiUDP udp;

// ===== ピン定義 =====
#define LIGHT_SENSOR_PIN 6
#define PUMP_PIN         2
#define SOIL_SENSOR_PIN  1
#define BME_SDA_PIN      7
#define BME_SCL_PIN      8
#define INA_SDA_PIN      39
#define INA_SCL_PIN      38

// ===== 時間・制御定数 =====
const int INIT_ON_MSEC = 5000;               ///< 起動後の安定待ち時間(ms)
const int DEEP_SLEEP_WAIT_MSEC = 1000;       ///< Deep Sleep前の待ち時間(ms)
const int PUMP_ON_MSEC = 5000;               ///< ポンプON時間(ms)
const int SOIL_DRY_THRESHOLD = 1900;         ///< 土壌乾燥しきい値(ADC)

Adafruit_BME280 bme;
TwoWire INA_Wire = TwoWire(1);
Adafruit_INA219 ina219(0x40);
bool hasBME280 = false;
bool hasINA = false;

/**
 * @struct SensorData
 * @brief 全センサ値を格納する構造体
 */
struct SensorData {
  float temp;
  float hum;
  float pres;
  int light;
  int soil;
  float busVoltage;
  float current_mA;
  float power_mW;
};

/**
 * @brief I2Cセンサ（BME280, INA219）初期化
 */
void initSensors() {
  Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
  hasBME280 = bme.begin(0x77) || bme.begin(0x76);
  INA_Wire.begin(INA_SDA_PIN, INA_SCL_PIN);
  hasINA = ina219.begin(&INA_Wire);
}

/**
 * @brief アナログピンを中央値フィルタで読み取る
 * @param pin アナログピン番号
 * @param samples サンプリング回数
 * @param interval_ms サンプリング間隔
 * @return 中央値
 */
int readAnalogMedian(int pin, int samples = 5, int interval_ms = 20) {
  int values[10];
  samples = min(samples, 10);
  for (int i = 0; i < samples; i++) {
    values[i] = analogRead(pin);
    delay(interval_ms);
  }
  std::sort(values, values + samples);
  return values[samples / 2];
}

/**
 * @brief BME280/INA219を移動平均で読み取り、アナログ値は中央値で取得
 * @param samples サンプリング回数
 * @param interval_ms サンプリング間隔
 * @return フィルタ後のセンサデータ
 */
SensorData readSensorsFiltered(int samples = 5, int interval_ms = 100) {
  SensorData acc = {};
  for (int i = 0; i < samples; i++) {
    if (hasBME280) {
      acc.temp += bme.readTemperature();
      acc.hum  += bme.readHumidity();
      acc.pres += bme.readPressure() / 100.0f;
    }
    if (hasINA) {
      acc.busVoltage += ina219.getBusVoltage_V();
      acc.current_mA += ina219.getCurrent_mA();
      acc.power_mW   += ina219.getPower_mW();
    }
    delay(interval_ms);
  }

  SensorData result;
  result.temp = acc.temp / samples;
  result.hum  = acc.hum  / samples;
  result.pres = acc.pres / samples;
  result.busVoltage = acc.busVoltage / samples;
  result.current_mA = acc.current_mA / samples;
  result.power_mW   = acc.power_mW   / samples;

  result.light = readAnalogMedian(LIGHT_SENSOR_PIN);
  result.soil  = readAnalogMedian(SOIL_SENSOR_PIN);
  return result;
}

/**
 * @brief ポンプ制御
 * @param soilRaw 土壌センサ値
 */
void handlePump(int soilRaw) {
  digitalWrite(PUMP_PIN, HIGH);
  delay(PUMP_ON_MSEC);
  digitalWrite(PUMP_PIN, LOW);
}

/**
 * @brief WiFi接続 + UDPパケット送信
 * @param data センサデータ
 * @return 成功時 true
 */
bool sendUDP(const SensorData& data) {
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry++ < 30) delay(500);
  if (WiFi.status() != WL_CONNECTED) return false;

  udp.begin(WiFi.localIP(), udpPort);

  char packet[256];
  snprintf(packet, sizeof(packet),
           "Temp=%.2f,Hum=%.2f,Pres=%.2f,Light=%d,Soil=%d,Bus=%.2f,Current=%.2f,Power=%.2f",
           data.temp, data.hum, data.pres, data.light, data.soil,
           data.busVoltage, data.current_mA, data.power_mW);

  udp.beginPacket(udpAddress, udpPort);
  udp.write((uint8_t*)packet, strlen(packet));
  return udp.endPacket();
}

/**
 * @brief 起動処理 → センサ測定 → ポンプ制御 → UDP送信 → Deep Sleep
 */
void setup() {
  delay(INIT_ON_MSEC);
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(SOIL_SENSOR_PIN, INPUT);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);

  initSensors();

  SensorData data_before = readSensorsFiltered();

  bool pumpActivated = false;
  if (data_before.soil > SOIL_DRY_THRESHOLD) {
    handlePump(data_before.soil);
    pumpActivated = true;
    delay(100);  // 電圧・電流の安定待ち
  }

  SensorData data_after = readSensorsFiltered();

  if (pumpActivated) {
    // 駆動前後を送信（2回）
    sendUDP(data_before);
    delay(100);  // 送信間隔
    sendUDP(data_after);
  } else {
    // 1回だけ送信（駆動してない）
    sendUDP(data_before);
  }

  delay(DEEP_SLEEP_WAIT_MSEC);
  esp_sleep_enable_timer_wakeup(600e6); // 10分スリープ
  esp_deep_sleep_start();
}

void loop() {
  // 未使用
}
