#!/usr/bin/env python

import paho.mqtt.client as mqtt
import time, json, os, glob, subprocess, logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from random import randint
import scanner_config as cfg

# Note, there are two topics
# SCAN_TOPIC {batch:[no|yes], format:[pdf|pdf_multi|png|jpg], x:[210], y:[297], resolution:[200|300|400|600] }
# REPORT_TOPIC msg

logger = logging.getLogger()
def init_log():
    global logger
    logger.setLevel(logging.DEBUG)

def remove_tmpdir_files():
    types = ('*.pdf', '*.png', '*.tiff', '*.jpg')
    files = []
    for filetype in types:
        files.extend(glob.glob(os.path.join(cfg.TMP_SCAN_DIR, filetype)))
    for f in files:
        os.remove(f)

def remove_files_list(files):
    for file in files:
        os.remove(file)

def execute_cmd(command):
    logger = logging.getLogger()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process.wait()
    ret_line = ""
    for line in process.stdout:
        if line:
            ret_line += line.decode("utf-8") + ' '
    ret_line = ret_line.replace('\n', ' ').replace('\r', '')
    logger.info('Return command :  %d %s' % (process.returncode, ret_line))
    return process.returncode, ret_line

def scan_cmd(filename, x, y, resolution):
    logger = logging.getLogger()
    command = "scanimage -d '%s' --mode=Color --format=tiff " %cfg.SANE_SCAN_ID
    command += " --resolution=" + resolution + " " + "-x " + x + " -y " + y + " > " + filename
    logger.info('Execute command :  %s' % (command))
    return execute_cmd(command)

def handle_scan(parameters):
    logger = logging.getLogger()
    scan_files = []
    retry = 0
    err = ""
    while True:
        filename = cfg.TMP_SCAN_DIR + '/' + str(len(scan_files)).zfill(3) + ".tiff"
        ret, err = scan_cmd(filename, parameters['x'], parameters['y'], parameters['resolution'])
        if ret != cfg.RET_OK and ret != cfg.RET_FEEDER_EMPTY: 
            logger.info('Scan unhandled error %d %s' % (ret, err))
            break
        elif ret == cfg.RET_OK:
            retry = 0
            scan_files.append(filename)
            log = "Scan %d OK" %len(scan_files)
            if parameters['batch'] != 'no':
                log += ". Wait for next scan..."
            logger.info('%s' % (log))
            send_msg(log)
        elif ret == cfg.RET_FEEDER_EMPTY: # feeder empty
            logger.info('timeout wait %d sec' %(cfg.TIMEOUT))
            retry += 1
            time.sleep(cfg.TIMEOUT)
    
        if ret == cfg.RET_OK and parameters['batch'] == 'no':
            logger.info('exit because of no batch defined')
            break
        elif retry > cfg.MAX_RETRY :
            logger.info('Max retry')
            break
    return scan_files, err

def convert(scan_files, parameters):
    output_files = []
    filename_prefix = cfg.TMP_SCAN_DIR + '/' + "scan_" + time.strftime("%d%m%Y-%H%M%S")
    convert_commands = []
    if parameters['format'] != 'pdf_multi':
        count=0
        for file in scan_files:
            output_name = filename_prefix + "_" + str(count).zfill(3) + "." + parameters['format']
            if parameters['format'] == 'pdf':
                command = "convert -compress jpeg "
            else:
                command = "convert " 
            command += file + " " + output_name
            convert_commands.append(command)
            output_files.append(output_name)
            count += 1
    else:
        output_name = filename_prefix + ".pdf"
        command = "convert -compress jpeg "
        for file in scan_files:
            command += file + " "
        command += output_name
        convert_commands.append(command)
        output_files.append(output_name)
    
    err = ""
    ret = 0
    for command  in convert_commands:
        logger.info('Execute command :  %s' % (command))
        ret, err = execute_cmd(command)
        if ret != 0:
            break
    
    if ret != 0:
        remove_files_list(scan_files)

    return ret, output_files, err

def on_message(client, userdata, message):
    if message.topic != cfg.SCAN_TOPIC:
        logger.info("Wrong topic")
        return

    raw_msg = message.payload.decode("utf-8")
    logger.info('Raw message received %s' %(raw_msg))
    tmp_parameters = {}
    if raw_msg :
        tmp_parameters = json.loads(raw_msg)
    parameters = {**cfg.default_parameters, **tmp_parameters}

    logger.info('Parameters %s' %(parameters))
    if (parameters['format'] == 'pdf_multi' or parameters['batch'] != 'yes') and cfg.HAS_SHEETFED == False:
        send_msg("Batch and multi-pages PDF not handled without sheetfed scanner.")
        return

    remove_tmpdir_files()

    send_msg("Wait for scan...")
    scan_files, err = handle_scan(parameters)
    logger.info('Scanned files : %s, err: %s' %(scan_files, err))
    if len(scan_files) == 0:
        send_msg("Scan err:%s" %(err))
        return
    
    output_files = []
    ret, output_files, err = convert(scan_files, parameters)
    logger.info('Convert return : %s, files: %s, err: %s ' %(ret, output_files, err))
    if ret != 0:
        send_msg("Convert error : %s" %err)
        return
    else:
        send_msg("Converted")
    
    for file in output_files:
        ret, err = cfg.user_action(file)
        if ret != 0:
            logger.info('User action err : %d %s' %(ret, err))
            break
    
    if ret != 0:
        send_msg("Transfert error : %s" %err)
        return

    remove_files_list(scan_files)
    remove_files_list(output_files)
    
    logger.info('Action done')
    send_msg("File(s) transfered")

def on_connect(client, userdata, flags, rc):
    logger = logging.getLogger()
    client.subscribe(cfg.SCAN_TOPIC)
    logger.info("Subscribe to topic %s" %cfg.SCAN_TOPIC)

def send_msg(msg):
    pub_client = create_mqtt_client("client_scanpub")
    pub_client.connect(cfg.BROKER_ADDRESS)
    pub_client.publish(cfg.REPORT_TOPIC, msg)
    pub_client.loop()

def create_mqtt_client(prefix):
    suffix = prefix + datetime.utcnow().strftime('%M%S%f')[:-3] + str(randint(0, 99999))
    return mqtt.Client(prefix + suffix)

def init_logger():
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    file_handler = RotatingFileHandler(cfg.LOG_FILE,  mode='a', maxBytes=1000000, backupCount=1, encoding='utf-8', delay=0)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def main():
    init_logger()
    logger = logging.getLogger()
    logger.info('Start scan')
    if not os.path.exists(cfg.TMP_SCAN_DIR):
        os.mkdir(cfg.TMP_SCAN_DIR)
    else:
        remove_tmpdir_files()

    sub_client = create_mqtt_client("client_scansub")
    sub_client.on_connect=on_connect
    sub_client.on_message=on_message 
    sub_client.connect(cfg.BROKER_ADDRESS)

    sub_client.loop_forever()

if __name__ == "__main__":
    main()
