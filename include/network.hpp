#pragma once
#include "config.hpp"

bool tryConnectWiFi(const AppConfig& cfg);
bool sendUDP(const char* host, uint16_t port, const void* payload, size_t length = 0);
void reportConfigToServer(const AppConfig& cfg);
