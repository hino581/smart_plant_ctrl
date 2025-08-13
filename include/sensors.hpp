#pragma once
#include "config.hpp"

void sensorsInit();
SensorData readSensorsFiltered(int samples=5, int interval_ms=100);
