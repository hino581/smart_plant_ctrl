#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <Adafruit_INA219.h>
#include <algorithm>  // std::sort, std::min
#include "config.hpp"
#include "sensors.hpp"

static Adafruit_BME280 bme;
static TwoWire INA_Wire = TwoWire(1);
static Adafruit_INA219 ina219(0x40);
static bool hasBME280 = false;
static bool hasINA    = false;

void sensorsInit() {
  Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
  hasBME280 = bme.begin(0x77) || bme.begin(0x76);
  INA_Wire.begin(INA_SDA_PIN, INA_SCL_PIN);
  hasINA = ina219.begin(&INA_Wire);
}

static int readAnalogMedian(int pin, int samples=5, int interval_ms=20) {
  samples = std::min(samples, 10);
  int values[10];
  for (int i=0;i<samples;i++){
    values[i] = analogRead(pin);
    delay(interval_ms);
  }
  std::sort(values, values+samples);
  return values[samples/2];
}

SensorData readSensorsFiltered(int samples, int interval_ms) {
  SensorData acc = {};
  for (int i=0;i<samples;i++){
    if (hasBME280) {
      acc.temp += bme.readTemperature();
      acc.hum  += bme.readHumidity();
      acc.pres += bme.readPressure()/100.0f;
    }
    if (hasINA) {
      acc.busVoltage += ina219.getBusVoltage_V();
      acc.current_mA += ina219.getCurrent_mA();
      acc.power_mW   += ina219.getPower_mW();
    }
    delay(interval_ms);
  }
  SensorData r;
  r.temp = acc.temp/samples;
  r.hum  = acc.hum/samples;
  r.pres = acc.pres/samples;
  r.busVoltage = acc.busVoltage/samples;
  r.current_mA = acc.current_mA/samples;
  r.power_mW   = acc.power_mW/samples;
  r.light = readAnalogMedian(LIGHT_SENSOR_PIN);
  r.soil  = readAnalogMedian(SOIL_SENSOR_PIN);
  return r;
}
