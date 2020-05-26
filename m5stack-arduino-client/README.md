# Python batch scanning arduino client

Arduino HMI controlling python script of [python-scanner/](/python-scanner/)

<p align="center">
<img src="doc/m5stack_app.png" width="500">
</p>


It works on M5stack core which is a packaged esp32 with lcd and buttons.

## Libraries
Based on these arduino librairies:
 * m5stack core library
 * [M5ez 2.2.0](https://github.com/ropg/M5ez): HMI for m5stack.
 * [EspMQTTClient 1.8.0](https://github.com/plapointe6/EspMQTTClient): mqtt client for esp32.


## Files

There are two files :
 * *m5stack-arduino-client.ino*: main arduin program.
 * *mqttConfig.h*: MQTT client configuration.


## Parameters

MQTT client configuration has to be modified in *mqttConfig.h*:
```
const char* SSIDNAME = "XXX";
const char* PASSWORD = "XXXXX";
const char* MQTT_SERVER = "127.0.0.1";
const int   MQTT_PORT = 1883;
const char* MQTT_CLIENT_NAME = "esp32client_0";

const char* TOPIC_SCAN = "scanner/ds620/scan";
const char* TOPIC_REPORT = "scanner/ds620/report";
```

It must define the same MQTT parameters as the python scanner script.

## Compilation and uploading

From Arduino IDE, select M5Stack-Core-ESP32, then compile and upload.
