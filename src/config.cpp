#include <Arduino.h>
#include <Preferences.h>
#include "config.hpp"

const char* DEF_WIFI_SSID = "Fight Club";
const char* DEF_WIFI_PASS = "soap1999";
const char* DEF_UDP_ADDR  ="192.168.0.165";
const char* DEF_PSK  ="plant-psk";

static Preferences prefs;

void loadConfig(AppConfig& cfg) {
  prefs.begin("plantmon", true);
  // 制御しきい値
  cfg.soilDryThreshold = prefs.getUShort("soil", DEF_SOIL_DRY_THRESHOLD);
  cfg.pumpOnMs         = prefs.getUShort("pump", DEF_PUMP_ON_MS);
  cfg.initWaitMs       = prefs.getUShort("init", DEF_INIT_WAIT_MS);
  cfg.deepSleepWaitMs  = prefs.getUShort("dsw",  DEF_DEEP_SLEEP_WAIT_MS);
  cfg.sleepSec         = prefs.getUInt  ("slps", DEF_SLEEP_SEC);
  // 通信設定
  cfg.udpPort = prefs.getUShort("uport", SENSOR_SND_UPORT);
  Serial.printf("soilDryThreshold     : %lu\n", (unsigned long)cfg.soilDryThreshold);
  Serial.printf("pumpOnMs             : %lu\n", (unsigned long)cfg.pumpOnMs);
  Serial.printf("initWaitMs           : %lu\n", (unsigned long)cfg.initWaitMs);
  Serial.printf("deepSleepWaitMs      : %lu\n", (unsigned long)cfg.deepSleepWaitMs);
  Serial.printf("sleepSec             : %lu\n", (unsigned long)cfg.sleepSec);
  Serial.printf("udpPort              : %lu\n", (unsigned long)cfg.udpPort);
  // WiFi設定
  String s = prefs.getString("ssid",   DEF_WIFI_SSID);
  String p = prefs.getString("pass",   DEF_WIFI_PASS);
  String a = prefs.getString("uaddr",  DEF_UDP_ADDR);
  String k = prefs.getString("psk",    DEF_PSK);
  Serial.printf("ssid : %s\n", s.c_str());
  Serial.printf("pass : %s\n", p.c_str());
  Serial.printf("uaddr: %s\n", a.c_str());
  Serial.printf("psk  : %s\n", k.c_str());
  s.toCharArray(cfg.ssid, sizeof(cfg.ssid));
  p.toCharArray(cfg.pass, sizeof(cfg.pass));
  a.toCharArray(cfg.udpAddr, sizeof(cfg.udpAddr));
  k.toCharArray(cfg.psk, sizeof(cfg.psk));
  prefs.end();
}

void saveConfig(const AppConfig& cfg) {
  prefs.begin("plantmon", false);
  prefs.putUShort("soil",  cfg.soilDryThreshold);
  prefs.putUShort("pump",  cfg.pumpOnMs);
  prefs.putUShort("init",  cfg.initWaitMs);
  prefs.putUShort("dsw",   cfg.deepSleepWaitMs);
  prefs.putUInt  ("slps",  cfg.sleepSec);
  prefs.putString("ssid",  cfg.ssid);
  prefs.putString("pass",  cfg.pass);
  prefs.putString("uaddr", cfg.udpAddr);
  prefs.putUShort("uport", cfg.udpPort);
  prefs.putString("psk",   cfg.psk);
  prefs.end();
}
