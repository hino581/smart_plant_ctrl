#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <cstdio>
#include <cstring>
#include "config.hpp"
#include "network.hpp"

static WiFiUDP udp;

bool tryConnectWiFi(const AppConfig& cfg) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(cfg.ssid, cfg.pass);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis()-t0 < WIFI_CONNECT_TIMEOUT_MS) {
    delay(200);
  }
  return WiFi.status() == WL_CONNECTED;
}

void reportConfigToServer(const AppConfig& cfg) {
  WiFiUDP u;
  u.beginPacket(cfg.udpAddr, 12346);
  uint8_t mac[6]; WiFi.macAddress(mac);
  char packet[256];

  std::snprintf(packet, sizeof(packet),
      "type=config,"
      "mac=%02X:%02X:%02X:%02X:%02X:%02X,"
      "ssid=%s,"
      "udpAddr=%s,"
      "udpPort=%u,"
      "soil=%u,"
      "pump_ms=%u,"
      "init_ms=%u,"
      "dsw_ms=%u,"
      "sleep_s=%u",
      mac[0], mac[1], mac[2], mac[3], mac[4], mac[5],
      cfg.ssid, cfg.udpAddr, cfg.udpPort,
      cfg.soilDryThreshold, cfg.pumpOnMs, cfg.initWaitMs, cfg.deepSleepWaitMs, cfg.sleepSec
  );
  u.write(reinterpret_cast<const uint8_t*>(packet), std::strlen(packet));
  u.endPacket();
}

bool sendUDP(const char* host, uint16_t port, const void* payload, size_t length) {
    if (!WiFi.isConnected()) {
        Serial.println("[sendUDP] WiFi not connected");
        return false;
    }

    if (length == 0 && payload != nullptr) {
        // 長さ未指定なら文字列とみなして strlen()
        length = std::strlen(reinterpret_cast<const char*>(payload));
    }

    if (!udp.beginPacket(host, port)) {
        Serial.println("[sendUDP] beginPacket() failed");
        return false;
    }

    udp.write(reinterpret_cast<const uint8_t*>(payload), length);
    return udp.endPacket();
}