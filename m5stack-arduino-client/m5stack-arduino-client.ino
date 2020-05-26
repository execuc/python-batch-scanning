#include <M5Stack.h>
#include <M5ez.h>
#include <Preferences.h>
#include "EspMQTTClient.h"
#include "mqttConfig.h"


TaskHandle_t MqttTask = 0;
QueueHandle_t  scanOrderMsg=NULL;
const uint8_t scanOderMsgSize=100;
QueueHandle_t  scanReportMsg=NULL;
const uint8_t scanReportMsgSize=200;

EspMQTTClient client(
  SSIDNAME,
  PASSWORD,
  MQTT_SERVER,    
  MQTT_CLIENT_NAME,
  MQTT_PORT
);

void MqttCoreTask( void * pvParameters ){
 // Noten on ESP32 portTICK_PERIOD_MS = 10
  char opts[scanOderMsgSize];
   client.enableDebuggingMessages();
   
    while(true){
        // Call MQTT library processing loop
        client.loop();
        if(xQueueReceive(scanOrderMsg, opts, 0)){
          Serial.println(opts);
          client.publish(TOPIC_SCAN, opts);
        }
        vTaskDelay(100/portTICK_PERIOD_MS); //wait 100ms;
    }
}

void setup() {
  Serial.begin(115200);

  // Add battery icon on LCD header, see M5ez library
  Preferences prefs;
  prefs.begin("M5ez");
  prefs.putBool("battery_icon_on", true);
  prefs.end();

  // Create FreeRTOS queues for threads communication
  scanOrderMsg = xQueueCreate(1,sizeof(char) * scanOderMsgSize);
  scanReportMsg = xQueueCreate(3,sizeof(char) * scanReportMsgSize);
  // Wait for 1 second
  vTaskDelay(1000/portTICK_PERIOD_MS);
  // Create task for MQTT processing
  xTaskCreatePinnedToCore(
                    MqttCoreTask,   /* Function to implement the task */
                    "MqttTask", /* Name of the task */
                    10000,      /* Stack size in words */
                    NULL,       /* Task input parameter */
                    1,          /* Priority of the task */
                    &MqttTask,       /* Task handle. */
                    0);  /* Core where the task should run */
  // Start LCD library
  ez.begin();
}

void onConnectionEstablished() {
  Serial.println("onConnectionEstablished");
  client.subscribe(TOPIC_REPORT, [](const String & payload) {
    char payloadChar[scanReportMsgSize];
    payload.toCharArray(payloadChar, payload.length()+1);
    xQueueSend(scanReportMsg, payloadChar, 0);
  });
}

void loop() {
  ezMenu myMenu("Main menu");
  myMenu.txtSmall();
  myMenu.addItem("Scan");
  myMenu.addItem("Misc");
  myMenu.addItem("---------------");
  myMenu.addItem("Power off");
  while (true) {
    myMenu.runOnce();
    if(myMenu.pickName() == "Scan") {
      scanMenu();
    } else if(myMenu.pickName() == "Misc") {
      Serial.println("Misc");
    } else if(myMenu.pickName() == "Power off") {
      m5.powerOFF();
    }
  }
}

const String SCAN_TYPE[] = {"pdf", "pdf_multi", "png", "jpg"};
const uint8_t MAX_TYPE = sizeof(SCAN_TYPE)/sizeof(String);
const String SCAN_FORMAT[] = {"A4", "A5", "10x15", "15x10"};
const uint8_t MAX_FORMAT = sizeof(SCAN_FORMAT)/sizeof(String);
const String SCAN_RES[] = {"200", "250", "300", "400", "600"};
const uint8_t MAX_RES = sizeof(SCAN_RES)/sizeof(String);

String type = SCAN_TYPE[0];
String format = SCAN_FORMAT[0];
String res = SCAN_RES[2];

void scanMenu() {
  while(true) {
    ezMenu myMenu("Scan menu");
    myMenu.txtSmall();
    myMenu.addItem("Type: " + type, NULL, scanOptions);
    myMenu.addItem("Format:" + format, NULL, scanOptions);
    myMenu.addItem("Res:" + res, NULL, scanOptions);
    myMenu.addItem("---------------");
    myMenu.addItem("Scan", NULL, scanStart);
    if(type != "pdf_multi") {
      myMenu.addItem("Scan batch", NULL, scanStart);
    }
    myMenu.addItem("---------------");
    myMenu.addItem("Back to menu");
    myMenu.runOnce();
    if(myMenu.pickName().substring(0,4) == "Back") {
      break;
    }
  }
}

bool scanStart(ezMenu* callingMenu) {
  const String actionStr = callingMenu->pickCaption();
  bool isBatch = actionStr == "Scan batch";

  if(!client.isConnected()) {
    ez.msgBox(actionStr, "Error: Not connected to MQTT", "OK", true);
    return true;
  }
  String opts = "{\"batch\":";
  if(isBatch && format != "pdf_multi")
    opts += "\"yes\",";
  else
    opts += "\"no\",";
  opts += "\"format\":\"" + type + "\",";
  if(format == "A4")
    opts += "\"x\":\"210\",\"y\":\"297\",";
  else if (format == "A5")
    opts += "\"x\":\"148\",\"y\":\"210\",";
  else if (format == "10x15")
    opts += "\"x\":\"100\",\"y\":\"150\",";
  else if (format == "15x10")
    opts += "\"x\":\"150\",\"y\":\"100\",";
  opts += "\"resolution\":\"" + res + "\"}";
  
  ez.msgBox(actionStr, "Start " + actionStr, "OK", false);
  char optChar[scanOderMsgSize];
  opts.toCharArray(optChar, opts.length()+1) ;
  if(!xQueueSend(scanOrderMsg, optChar, 0)){
    ez.msgBox(actionStr, "Error: full queue", "OK", true);
    return true;
  }
  
  while(true) {
    char payloadChar[scanReportMsgSize];
    if(ez.buttons.poll() == "OK") {
      break;
    }

    if(xQueueReceive(scanReportMsg, payloadChar, 0)){
      ez.msgBox(actionStr, payloadChar, "OK", false);
    }
  }
}

bool scanOptions(ezMenu* callingMenu) {
  const String strOptions = callingMenu->pickCaption().substring(0,3);
  const String *optStr = NULL;
  const uint8_t *optSize = 0;
  String *output = NULL;
  if(strOptions == "Typ") {
    optStr = SCAN_TYPE;
    optSize = &MAX_TYPE;
    output = &type;
  } else if(strOptions == "For") {
    optStr = SCAN_FORMAT;
    optSize = &MAX_FORMAT;
    output = &format;
  } else if(strOptions == "Res") {
    optStr = SCAN_RES;
    optSize = &MAX_RES;
    output = &res;
  }

  ezMenu myMenu(callingMenu->pickCaption());
  for(uint8_t it=0; it < *optSize; it++) {
    myMenu.addItem(optStr[it]);  
  }
  
  myMenu.runOnce();
  *output = myMenu.pickName();
  return true;
}
