#!/usr/bin/env python
# Read BME280 Calibration Data
# Version 0.0.1
# 2018-04-01
# Stoic Weather Watch
# Reads TPH data from a BME280 connected to an R Pi and sends it to Stoic

import smbus
import csv
import time

bus = smbus.SMBus(1)

I2CADDRESS = 0x77

CAL_FILE_IN = "BME280CalDict.csv"

LOG_FILE_OUT = "BME280Log.txt"

# Used by InitializeBME280
BME280_RESET_REG  =    int("E0",16)
BME280_RESET_CMD  =    int("B6",16)


def ReadCalibrationDict():
    with open(CAL_FILE_IN, 'r') as csv_file:
        reader = csv.reader(csv_file)
        CalDict = dict(reader)

    for key in mydict:
        CalDict[key] = long(CalDict[key])
    
    return CalDict

def WriteLogEntry(Entry):
    with open(LOG_FILE_OUT, 'a') as log_file:
        timeStr = strftime("%Y-%m-%d-%H-%M-%S", gmtime())
        log_file.write(timeStr + "  " + Entry)

def InitializeBME280():
    # Send reset
    I2CBuss.write(SensorAddress,(byte)BME280_RESET_REG, (byte)BME280_RESET_CMD);
    

CalDict = ReadCalibrationDict()