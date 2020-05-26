#!/usr/bin/env python

import requests, logging, os, shutil

# MQTT server address
BROKER_ADDRESS = '127.0.0.1'
# MQTT scan order topic
SCAN_TOPIC = 'scanner/dev/scan'
# MQTT scan log topic
REPORT_TOPIC = 'scanner/dev/report'

#Sane scanner id
SANE_SCAN_ID = 'dsseries:usb:0x04F9:0x60E0' # For brother ds-620
HAS_SHEETFED = True # False for flat bed, then batch and multi-pages pdf are disabled.
# SANE code for the brother ds620 scanner. 
RET_OK = 0 # SANE return value after a scan
RET_FEEDER_EMPTY = 7 # Important, use value returned by SANE with your scanner !

# In batch scan mode, script waits a maximum of TIMEOUT * MAX-RETRY second between each scan.
# After, batch is stopped and the user action is launched.
TIMEOUT = 2 # Seconds between to after a failed scan due of an empty feeder
MAX_RETRY = 10 # Max scan retry due to an empty feeder error.

# Defaults scan parameters
default_parameters = {'batch': 'no', 'format':'pdf', 'x':'210', 'y': '297', 'resolution':'300'}

# Tmp directory used to store raw image
# Warning: the directory will be emptied by the script, so do not store anything else in it. 
TMP_SCAN_DIR = '/tmp/scan_tmp'

# Log file
LOG_FILE = '/tmp/scan_daemon.log'


def user_action(file):
    # Need to be implemented, example: 
    return copy_to_disk(file) 
    #return send_to_webDAV(file)

LOCAL_DIR = "/tmp/"
def copy_to_disk(file):
    err = ''
    ret = 0
    try:
        shutil.copy(file, LOCAL_DIR)
    except IOError as e:
        err = str(e)
        ret = 1
    return ret, err

# Example of document processing
# Set the right address and account
def send_to_webDAV(file):
    filename_w_ext = os.path.basename(file)
    filename, file_extension = os.path.splitext(filename_w_ext)
    headers = {'Slug': filename}
    if file_extension.lower() == 'pdf':
        headers['Content-type'] = 'application/pdf'
    elif file_extension.lower() == 'jpg':
        headers['Content-type'] = 'image/jpeg'
    elif file_extension.lower() == 'png':
        headers['Content-type'] = 'image/png'

    ret = 0
    err = ''
    try:
        requests.put(url='https://XX.XX.XX.XX/remote.php/dav/files/scans/' + filename_w_ext, data=open(file, 'rb'), headers=headers, auth=('user', 'XXXXXXXX'), verify=False)
    except requests.exceptions.RequestException as e:
        err = str(e)
        ret = 1
    return ret, err

