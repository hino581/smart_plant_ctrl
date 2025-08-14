#include <Arduino.h>
#include <algorithm>
#include <Preferences.h>
#include "config.hpp"
#include "sensors.hpp"
#include "network.hpp"
#include "provision.hpp"

// リセット用ヘルパ
static void factoryResetAndReboot() {
  Preferences p;
  p.begin("plantmon", /*readOnly=*/false);  // NVSの "plantmon" 名前空間に合わせて
  p.clear();                                 // 名前空間ごと削除（設定初期化）
  p.end();
  delay(200);
  ESP.restart();                              // 初期化後に即再起動
}

// ポンプ制御
static void handlePump(const AppConfig& cfg) {
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, HIGH);
  delay(cfg.pumpOnMs);
  digitalWrite(PUMP_PIN, LOW);
}

void setup() {
  bool sendUDPisOK;
  char packet[256];

  Serial.begin(115200);
  pinMode(RESET_BTN_PIN, INPUT_PULLUP);
  if (digitalRead(RESET_BTN_PIN) == LOW) {  // LOW=押下
    factoryResetAndReboot();
  }
  AppConfig cfg;
  loadConfig(cfg);
  delay(cfg.initWaitMs);
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(SOIL_SENSOR_PIN, INPUT);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);

  sensorsInit();

  SensorData sensorData = readSensorsFiltered();
  if (sensorData.soil > cfg.soilDryThreshold) {
    handlePump(cfg);
    delay(100);
  }
  tryConnectWiFi(cfg);
  std::snprintf(packet, sizeof(packet),
      "Temp=%.2f,Hum=%.2f,Pres=%.2f,Light=%d,Soil=%d,Bus=%.2f,Current=%.2f,Power=%.2f",
      sensorData.temp, sensorData.hum, sensorData.pres, sensorData.light, sensorData.soil,
      sensorData.busVoltage, sensorData.current_mA, sensorData.power_mW);
  sendUDPisOK = sendUDP(cfg.udpAddr, cfg.udpPort, packet);

  if (sendUDPisOK) {
    // 成功時は毎回、短時間のAP窓を開ける（AP+STA）
    startProvisionWindowAPSTA(cfg);  // (1分)
  } else {
    // 失敗時は従来どおりフルAPプロビジョニング（1分）
    //startProvisionAP(cfg);
    startProvisionWindowAPSTA(cfg);  // (1分)
  }

  delay(cfg.deepSleepWaitMs);
  esp_sleep_enable_timer_wakeup((uint64_t)cfg.sleepSec * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}
