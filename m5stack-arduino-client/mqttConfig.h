#ifndef SCAN_MQTT_CONFIG_H
#define SCAN_MQTT_CONFIG_H

const char* SSIDNAME = "XXX";
const char* PASSWORD = "XXXXX";
const char* MQTT_SERVER = "127.0.0.1";
const int   MQTT_PORT = 1883;
const char* MQTT_CLIENT_NAME = "esp32client_0";

const char* TOPIC_SCAN = "scanner/ds620/scan";
const char* TOPIC_REPORT = "scanner/ds620/report";

#endif
