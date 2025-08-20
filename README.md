# smart_plant_ctrl

Firmware for **M5Stack AtomS3 Lite** that powers the solar-driven smart plant management system.  
This software handles sensor readings, automatic irrigation, and power-efficient operation.

## Features
- 🌱 Soil moisture monitoring (M5Stack Watering Unit)
- 🌡️ Temperature, humidity, and pressure sensing (Grove BME280)
- 💡 Light level monitoring (Grove Light Sensor)
- 🔋 Power consumption monitoring (Grove INA219)
- 🚰 Automatic water pump control when soil is too dry
- 📡 Wi-Fi communication via UDP (data sent every 10 minutes)
- 💤 Deep Sleep mode for low power consumption
- ☀️ Operates with solar panel + 18650 Li-ion battery

## Hardware Requirements
- M5Stack AtomS3 Lite (ESP32-S3)
- M5Stack Watering Unit
- Grove BME280
- Grove Light Sensor
- Grove INA219
- ExtPortForATOM (for multiple Grove sensors)
- Solar Power Management (SPM) + 18650 Li-ion battery

## Development
- **Language**: Arduino (C++)
- **Environment**: PlatformIO + VSCode

## Communication
- Protocol: UDP
- Interval: Every 10 minutes (configurable)
- Destination: Raspberry Pi running `smart_plant_monitor`

## License
MIT
