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

static bool handleProvisionPacket(const char* buf, AppConfig& cfg, WiFiUDP& udp) {
  // PSKチェック:contentReference[oaicite:4]{index=4}
  char inKey[32] = "";
  findStr(buf, "key", inKey, sizeof(inKey));
  if (std::strcmp(inKey, cfg.psk) != 0) {
    const char* nack = "{\"ack\":0,\"err\":\"psk\"}";
    udp.beginPacket(udp.remoteIP(), udp.remotePort());
    udp.write(reinterpret_cast<const uint8_t*>(nack), std::strlen(nack));
    udp.endPacket();
    return false; // 未処理
  }

  bool needReboot = false; int v;
  if (findInt(buf,"soil",&v))     cfg.soilDryThreshold = v;
  if (findInt(buf,"pump_ms",&v))  cfg.pumpOnMs = v;
  if (findInt(buf,"init_ms",&v))  cfg.initWaitMs = v;
  if (findInt(buf,"dsw_ms",&v))   cfg.deepSleepWaitMs = v;
  if (findInt(buf,"sleep_s",&v))  cfg.sleepSec = static_cast<uint32_t>(v);

  char s[32], p[64], a[16];
  if (findStr(buf,"ssid", s, sizeof(s))) { std::strncpy(cfg.ssid, s, sizeof(cfg.ssid)); needReboot=true; }
  if (findStr(buf,"pass", p, sizeof(p))) { std::strncpy(cfg.pass, p, sizeof(cfg.pass)); needReboot=true; }
  if (findStr(buf,"uaddr",a, sizeof(a))) { std::strncpy(cfg.udpAddr, a, sizeof(cfg.udpAddr)); }
  if (findInt(buf,"uport",&v))           { cfg.udpPort = static_cast<uint16_t>(v); }

  saveConfig(cfg); // NVS保存:contentReference[oaicite:5]{index=5}

  // ACK（適用後の現状値を返す）:contentReference[oaicite:6]{index=6}
  char ack[256];
  std::snprintf(ack, sizeof(ack),
    "{\"ack\":1,\"ssid\":\"%s\",\"uaddr\":\"%s\",\"uport\":%u,"
    "\"soil\":%u,\"pump_ms\":%u,\"init_ms\":%u,\"dsw_ms\":%u,\"sleep_s\":%u}",
    cfg.ssid, cfg.udpAddr, cfg.udpPort,
    cfg.soilDryThreshold, cfg.pumpOnMs, cfg.initWaitMs, cfg.deepSleepWaitMs, cfg.sleepSec);
  udp.beginPacket(udp.remoteIP(), udp.remotePort());
  udp.write(reinterpret_cast<const uint8_t*>(ack), std::strlen(ack));
  udp.endPacket();

  if (needReboot) { delay(300); WiFi.softAPdisconnect(true); ESP.restart(); }
  return true; // 処理成功
}

// ====== 起動時のフルAPプロビジョニング（1分）を共通ハンドラで書き換え:contentReference[oaicite:7]{index=7} ======
void startProvisionAP(AppConfig& cfg) {
  WiFi.mode(WIFI_AP);
  uint8_t m[6];
  esp_read_mac(m, ESP_MAC_WIFI_SOFTAP);
  char apSsid[32]; std::snprintf(apSsid, sizeof(apSsid), "PlantMon-%02X%02X", m[4], m[5]);
  WiFi.softAP(apSsid, "plantmon");
  WiFi.setTxPower(WIFI_POWER_MINUS_1dBm);
  ctrlUdp.begin((uint16_t) PRV_SND_RCV_PORT);

  uint32_t t0 = millis();
  while (millis()-t0 < (uint32_t) PROVISION_WINDOW_MS) {
    int sz = ctrlUdp.parsePacket();
    if (sz > 0) {
      char buf[384]; int n = ctrlUdp.read(buf, sizeof(buf)-1); buf[n]=0;
      if (handleProvisionPacket(buf, cfg, ctrlUdp)) {
        // ★1回適用したら即クローズ
        break;
      }
    }
    delay(10);
  }
  ctrlUdp.stop();
  WiFi.softAPdisconnect(true);
}

void startProvisionWindowAPSTA(AppConfig& cfg) {
    // 1. AP SSID生成
    uint8_t m[6];
    esp_read_mac(m, ESP_MAC_WIFI_SOFTAP);
    char apSsid[32];
    std::snprintf(apSsid, sizeof(apSsid), "PlantMon-%02X%02X", m[4], m[5]);
    const char* apPass = "plantmon";

    // 2. JSONで現在設定＋AP情報を送信（STA経由）
    char announce[512];
    std::snprintf(announce, sizeof(announce),
        "{\"ap_ssid\":\"%s\",\"ap_pass\":\"%s\",\"ap_ip\":\"%s\","
        "\"soil\":%u,\"pump_ms\":%u,\"init_ms\":%u,"
        "\"dsw_ms\":%u,\"sleep_s\":%u,"
        "\"uaddr\":\"%s\",\"uport\":%u}",
        apSsid,
        (apPass && apPass[0]) ? apPass : "",
        WiFi.localIP().toString().c_str(), // STA IPで送信
        cfg.soilDryThreshold,
        cfg.pumpOnMs,
        cfg.initWaitMs,
        cfg.deepSleepWaitMs,
        cfg.sleepSec,
        cfg.udpAddr,
        cfg.udpPort
    );
    Serial.printf("[PROV] announce(JSON) -> %s:%u\n%s\n",
                  cfg.udpAddr, (unsigned)PRV_SND_RCV_PORT, announce);

    if (!sendUDP(cfg.udpAddr, PRV_SND_RCV_PORT, announce)) {
        Serial.println("[PROV] sendUDP() failed");
        return;
    }

    // 3. SoftAP起動
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(apSsid, apPass);
    WiFi.setTxPower(WIFI_POWER_MINUS_1dBm);

    // 4. サーバからの設定受信待ち
    ctrlUdp.begin((uint16_t)PRV_SND_RCV_PORT);
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
