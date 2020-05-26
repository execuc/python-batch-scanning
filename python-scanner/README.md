# Python batch scanning script

**Note:** A flatbed scanner can be used but in this case, script does not manage batch scanning and multi-pages PDF. The script was developed using a Brother DS-620 sheetfed scanner. It may need to be modified to work with other scanners.

## How it works

Python script receives the scan order via an MQTT message with the following parameters:
 * **batch**: *[no|yes]* **=>** Enable batch mode or not. If *yes*, sheetfed scanner waits until the user no longer puts paper to scan (+ timeout)/
 * **format**: *[pdf|pdf_multi|png|jpg]* **=>** Document output format. If *pdf_multi* is selected then script waits for no paper (+timeout) and then combine all scans to give a multi-pages PDF (whatever *batch* parameters).
 * **resolution**: *[200|300|400|600]* => scan resolution in dpi.
 * **x**: *[210]*, **y**:*[297]* width,height in millimeters of the scanned document.

Once the document(s) has been scanned, *user_action* function is called to process the file. This function has to be implement to know what to do with them. For example, copying to a specific directory or sending to a cloud.

**Warning**: Do not use **batch** or *pdf_multi* mode in the case of a flatbed scanner because the python script will scan undefinitely because the scanner never returns the SANE code *Document feeder out of documents*.

**There are two python files:**
  * *scanner.py*: main script.
  * *scanner_config.py*: configuration files with user_action to implement.

## Configuration 
### Get sane scanner ID
Before starting, identify your scanner using the *scanimage --help* command:
```bash
$ scanimage --help
Usage: scanimage [OPTION]...
*[.....]*
Start image acquisition on a scanner device and write image data to
standard output.
*[.....]*
Type "scanimage --help -d DEVICE'' to get list of all options for DEVICE.

List of available devices:
    dsseries:usb:0x04F9:0x60E0
```
In this case, the identifier is ** dsseries: usb: 0x04F9: 0x60E0 ** (corresponds to a Brother DS620 in this example).  
This value is to be set for the value **SANE_SCAN_ID** of the configuration file.

### Empty feeder return code
The script manages a timeout when the sheetfed scanner runs out of paper so that the user insert a new one. This functionality is useful when there is no automatic document feeder and the user has to put document one by one. 
To make it work, the script must recognizes the SANE error code: *Document feeder out of documents*/  
In the case of the Brother DS-620, this code is **7**. Please check that it is the same with yours.  

Without document in the scanner feeder, please launch these commands from the bash (with the right scanner ID) :

```bash
scanimage -d "dsseries:usb:0x04F9:0x60E0" --format tiff > rawr.tiff
```
The command should return this:
```bash
scanimage: sane_start: Document feeder out of documents
```
To get the error code, type:
```bash
echo $?
```
Which returns ** 7 ** in the case of the DS620 scanner. It may be the same error code for all scanners.  
This value is to be set for the value * RET_FEEDER_EMPTY * of the configuration file.

## Configuration file

You must configure the script by modifying at least these constants in scanner_config.py:
 * **BROKER_ADDRESS**: your MQTT broker address
 * **TMP_SCAN_DIR**: directory path to temporarily store the scanned images. The script must have permission to write to it. **Warning** the directory will be emptied by the script, so do not store anything else in it. 
 * **LOG_FILE**: path to the log file.
 * **SANE_SCAN_ID** et **RET_FEEDER_EMPTY**: use values determined above.

## User action
In *scanner_config.py* file **user_action(file)** function has to be impletement in order to specify the desired action.
**file** parameters represents the absolute path of the file to be processed.

Two functions are provided for the example, and can be called as sub function from *user_action* function :
 * *send_to_webDAV(file)*: to copy to a local disk
 * *copy_to_disk(file)*: to send to a webDAV cloud as nextcloud.


## Run script

On debian, install these packages : *python3-paho-mqtt*, *imagemagick*

Run the script with : *python3 scanner.py*

Put a document in the scanner and choose a method to send an order via mqtt :

### Use mosquitto MQTT shell client

Install mosquitto client package (*mosquitto-clients* for debian). These command must be adapted with the right mqtt address and topics.
On a first shell, subscribe to the report topic:
```
mosquitto_sub -h 192.168.1.15 -t "scanner/ds620/report"
```
On a second shell, send order with :
```
mosquitto_pub -h 192.168.1.15 -t "scanner/ds620/scan" -m '{"batch":"no", "format":"pdf"}'
```

Normally the scanner should start scanning. Information should appear in the first shell.
If that doesn't work, you have to look at the logs (file defined in the configuration file).

### Use MQTT Dash android application

With this application, configure your MQTT server ip address and create 4 widgets :
 * Scan report (test): topic scanner/ds620/report, disable publishing, small text
 * PDF multi (switch) : topic scanner/ds620/scan, enable publishing, On=Off = {"batch":yes", "format":"pdf_multi"}, Icon: cloud upload
 * PDF batch (switch) : topic scanner/ds620/scan, enable publishing, On=Off = {"batch":yes", "format":"pdf"}, Icon: cloud upload
 * PDF single (switch) : topic scanner/ds620/scan, enable publishing, On=Off = {"batch":no", "format":"pdf"}, Icon: cloud upload

### Use M5stack micro-controller

M5stack is a ESP32 (wifi) packaged with LCD and buttons. The [../m5stack-arduino-client](/m5stack-arduino-client/) directory contains a HMI interface for this scanner script usinf this micro-controller.

## Use it as Debian Daemon

As root, copy the *scanner.py* and *scanner_config.py* to */root/* with permissions 700.

Then create the file: /lib/systemd/system/auto_scanner_daemon.service:

```
[Unit]
Description=Automatic scanner daemon
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/scanner.py
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
```

Then reload daemon enumeration: *systemctl daemon-reload*.
To enable service: *systemctl enable auto_scanner_daemon.service* 
To start service: *systemctl start auto_scanner_daemon.service* 
To get the status: *systemctl status auto_scanner_daemon.service* 










