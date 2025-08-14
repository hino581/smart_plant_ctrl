#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <cstdio>
#include <cstring>
#include "config.hpp"
#include "network.hpp"
#include "provision.hpp"

// 受信に使うポート＆時間
static WiFiUDP ctrlUdp;

static bool findStr(const char* json, const char* key, char* out, size_t cap) {
  String s(json);
  int i = s.indexOf(String("\"")+key+"\"");
  if (i<0) return false;
  i = s.indexOf(':', i); if (i<0) return false;
  int q1 = s.indexOf('\"', i+1), q2 = s.indexOf('\"', q1+1);
  if (q1<0 || q2<0) return false;
  String v = s.substring(q1+1, q2);
  v.toCharArray(out, cap);
  return true;
}

static bool findInt(const char* json, const char* key, int* out) {
  String s(json);
  int i = s.indexOf(String("\"")+key+"\"");
  if (i<0) return false;
  i = s.indexOf(':', i); if (i<0) return false;
  *out = s.substring(i+1).toInt();
  return true;
}

void startProvisionWindowAPSTA(AppConfig& cfg) {
    // 1. AP SSID生成
    uint8_t macAddr[6];
    esp_read_mac(macAddr, ESP_MAC_WIFI_SOFTAP);
    char apSsid[32];
    std::snprintf(apSsid, sizeof(apSsid), "PlantMon-%02X%02X", macAddr[4], macAddr[5]);
    const char* apPass = "plantmon";
    char macStr[18];
    std::snprintf(macStr, sizeof(macStr),
            "%02X:%02X:%02X:%02X:%02X:%02X",
            macAddr[0], macAddr[1], macAddr[2], macAddr[3], macAddr[4], macAddr[5]);

    // 2. JSONで現在設定＋AP情報を送信（STA経由）
    char announce[512];
    std::snprintf(announce, sizeof(announce),
        "{\"mac\":\"%s\",\"ap_ssid\":\"%s\",\"ap_pass\":\"%s\",\"ap_ip\":\"%s\","
        "\"soil\":%u,\"pump_ms\":%u,\"init_ms\":%u,"
        "\"dsw_ms\":%u,\"sleep_s\":%u,"
        "\"ssid\":\"%s\",\"pass\":\"%s\",\"uaddr\":\"%s\",\"uport\":%u}",
        macStr,
        apSsid,
        (apPass && apPass[0]) ? apPass : "",
        WiFi.localIP().toString().c_str(), // STA IPで送信
        cfg.soilDryThreshold,
        cfg.pumpOnMs,
        cfg.initWaitMs,
        cfg.deepSleepWaitMs,
        cfg.sleepSec,
        cfg.ssid,
        cfg.pass,
        cfg.udpAddr,
        cfg.udpPort
    );
    Serial.printf("[PROV] announce(JSON) -> %s:%u\n%s\n",
                  cfg.udpAddr, (unsigned)PRV_SND_RCV_UPORT, announce);

    if (!sendUDP(cfg.udpAddr, PRV_SND_RCV_UPORT, announce)) {
        Serial.println("[PROV] sendUDP() failed");
        return;
    }

    // 3. SoftAP起動
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(apSsid, apPass);
    WiFi.setTxPower(WIFI_POWER_MINUS_1dBm);

    // 4. サーバからの設定受信待ち
    ctrlUdp.begin((uint16_t)PRV_SND_RCV_UPORT);
    uint32_t t0 = millis();
    while (millis() - t0 < (uint32_t)PROVISION_WINDOW_MS) {
        int sz = ctrlUdp.parsePacket();
        if (sz > 0) {
            char buf[384];
            int n = ctrlUdp.read(buf, sizeof(buf) - 1);
            if (n < 0) n = 0;
            buf[n] = 0;

            Serial.printf("[PROV] recv(JSON): %s\n", buf);

            // JSONから設定を反映
            int v;
            char tmp[64];
            if (findInt(buf, "soil", &v))     cfg.soilDryThreshold = v;
            if (findInt(buf, "pump_ms", &v))  cfg.pumpOnMs = v;
            if (findInt(buf, "init_ms", &v))  cfg.initWaitMs = v;
            if (findInt(buf, "dsw_ms", &v))   cfg.deepSleepWaitMs = v;
            if (findInt(buf, "sleep_s", &v))  cfg.sleepSec = v;
            if (findStr(buf, "ssid", tmp, sizeof(tmp))) std::strncpy(cfg.ssid, tmp, sizeof(cfg.ssid));
            if (findStr(buf, "pass", tmp, sizeof(tmp))) std::strncpy(cfg.pass, tmp, sizeof(cfg.pass));
            if (findStr(buf, "uaddr", tmp, sizeof(tmp))) std::strncpy(cfg.udpAddr, tmp, sizeof(cfg.udpAddr));
            if (findInt(buf, "uport", &v))    cfg.udpPort = v;

            saveConfig(cfg);
            break; // 受信したら終了
        }
        delay(10);
    }

    // 5. 後片付け
    ctrlUdp.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_STA);
}
