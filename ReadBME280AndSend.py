#!/usr/bin/env python
# Read BME280 Calibration Data
# Version 0.0.1
# 2018-04-01
# Stoic Weather Watch
# Reads TPH data from a BME280 connected to an R Pi and sends it to Stoic

import smbus
import csv
import time

from twisted.internet import reactor, defer, endpoints
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.protocols.amp import AMP
from SW_RemoteWatcher import IndoorPiA

bus = smbus.SMBus(1)

I2CADDRESS = 0x77

CAL_FILE_IN = "CalDictBME280.csv"

LOG_FILE_OUT = "LogBME280.txt"

DELAY_FOR_DAQ       =    int(5)

BME280_DATASTART_REG  =    int("0xF7",16)

BME280_DATA_LEN       =    int(8)

# Used by InitializeBME280
BME280_RESET_REG   =    int("E0",16)
BME280_CONFIG_REG  =    int("F5",16)
BME280_CTLHUM_REG  =    int("F2",16)
BME280_CTLMESR_REG =    int("F4",16)

BME280_RESET_CMD   =    int("B6",16)
BME280_CONFIG_CMD  =    int("F4",16)
BME280_CTLHUM_CMD  =    int("03",16)
BME280_CTLMESR_CMD =    int("6E",16)

BME280_MODE_MASK   =    int("03",16)


def ReadCalibrationDict():
    with open(CAL_FILE_IN, 'r') as csv_file:
        reader = csv.reader(csv_file)
        CalDict = dict(reader)

    for key in CalDict:
        CalDict[key] = long(CalDict[key])
    
    return CalDict

def WriteLogEntry(Entry):
    with open(LOG_FILE_OUT, 'a') as log_file:
        timeStr = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
        log_file.write(timeStr + "  " + Entry + "\n")
        
def ReadI2CRegByte(Reg):
    Value = bus.read_byte_data(I2CADDRESS, Reg)
    return Value

def WriteI2CRegByte(Reg,Data):
    bus.write_byte_data(I2CADDRESS, Reg, Data)

def InitializeBME280():
    # Send reset
    WriteI2CRegByte(BME280_RESET_REG,BME280_RESET_CMD)
    
    # Verify sleep mode
    RegIn = ReadI2CRegByte(BME280_CTLMESR_CMD)

    if((RegIn & BME280_MODE_MASK) > 0):
        WriteLogEntry("Error BME280 Not in Sleep Mode")
    
    # Configure the sensor
    WriteI2CRegByte(BME280_CONFIG_REG,BME280_CONFIG_CMD)
    WriteI2CRegByte(BME280_CTLHUM_REG,BME280_CTLHUM_CMD)
    WriteI2CRegByte(BME280_CTLMESR_REG,BME280_CTLMESR_CMD)

def InstructBME280ToAcquireData():
    WriteI2CRegByte(BME280_CTLMESR_REG,BME280_CTLMESR_CMD)
    
def RetrieveDataFromBME280():
    DataRaw = bus.read_i2c_block_data(I2CADDRESS, BME280_DATASTART_REG, BME280_DATA_LEN)
    print(DataRaw)
    
    return DataRaw

def ObtainDataFromBME280():
    """
    Runs both RetrieveDataFromBME280 and InstructBME280ToAcquireData with delay between
    """
    InstructBME280ToAcquireData()

    time.sleep(DELAY_FOR_DAQ)

    DataRaw = RetrieveDataFromBME280()
    
    return DataRaw


def sensor_parse_BME280_TFine(DataRaw, CalDict):
    """

        
    The BME280 calibration produces a value called TFine which is used in later calibrations. 
    TFine is returned by this function.
        
    Input is 3 bytes from the full data set. Only 20 bits have meaning
    """
    
        
    RawTemp = (long(DataRaw[3]) << 12) + (long(DataRaw[4]) << 4) + (long(DataRaw[5]) >> 4)
        
        
    # This mess comes from the data sheet. Someone must like LISP
    var1  = ( ((RawTemp>>3) - (CalDict["T1"]<<1)) * (CalDict["T2"]) ) >> 11

    var2  = (( ( ((RawTemp>>4) - (CalDict["T1"])) * ((RawTemp>>4) - (CalDict["T1"])) ) >> 12) * (CalDict["T3"]) ) >> 14

    TFine = var1 + var2

    # The limits for the sensor are -40 to 85 C. Equivalent to an output of -4000 or 8500
    if (TFine < -204826):
        WriteLogEntry("Stoic sensor_parse_BME280_TFine T less than min. Reporting None")
        return None
    elif (TFine > 435174):
        WriteLogEntry("Stoic sensor_parse_BME280_TFine T greater than max. Reporting None")
        return None

    return TFine
    
def sensor_parse_BME280_Temperature(TFine):
    """
    Takes in TFine and output tempreature in C
    """
    if TFine == None:
        return None
        
    Temperature = float((TFine * 5 ) >> 8)/float(100.0)
        
    return Temperature

def sensor_parse_BME280_Humidity(DataRaw, CalDict, TFine):
    """
    
    Formulae are based on BME280 Data sheet. 
    Output is realtive humidity as a percentage
    """
    
    RawHum = (long(DataRaw[6]) << 8) + (long(DataRaw[7]))

    
    # // Returns humidity in %RH as unsigned 32 bit integer in Q22.10 format (22 integer and 10 fractional bits). 
    #// Output value of 47445 represents 47445/1024 = 46.333 %RH 

    #    var1 = (TFine - ((BME280_S32_t)76800));
    var1 = TFine - long(76800)
    
    # var1 = (((((adc_H << 14) - (((BME280_S32_t)dig_H4) << 20) - (((BME280_S32_t)dig_H5) * var1)) + ((BME280_S32_t)16384)) >> 15)
    #* ((( ((((var1 * ((BME280_S32_t)dig_H6)) >> 10) * (((var1 * ((BME280_S32_t)dig_H3)) >> 11) + ((BME280_S32_t)32768))) >> 10) 
    #       + ((BME280_S32_t)2097152)) * ((BME280_S32_t)dig_H2) + 8192) >> 14));  
    var1 = ( ((((RawHum << 14) 
                - (CalDict["H4"] << 20) 
                - (CalDict["H5"] * var1)) 
                + long(16384)) >> 15) 
                * ((( ( (( (var1 * CalDict["H6"]) >> 10) 
                         * (((var1 * (CalDict["H3"])) >> 11) + long(32768))) >> 10) 
                         + long(2097152)) * CalDict["H2"]
                         + long(8192)) >> 14) )
    
    
    #var1 = (var1 - (((((var1 >> 15) * (var1 >> 15)) >> 7) * ((BME280_S32_t)dig_H1)) >> 4));
    var1 = (var1 - ( ( (((var1 >> 15) * (var1 >> 15)) >> 7) * CalDict["H1"] ) >> 4 ))
    
    #var1 = (var1 < 0 ? 0 : var1);   
    # If ? Then : else
    if var1 < 0:
        var1 = 0
    # Else no change
    
    #var1 = (var1 > 419430400 ? 419430400 : var1);   
    if var1 > long(419430400):
        var1 = long(419430400)
    # Else no change
    
    H = var1 >> 12
    
    
    # Hum = float(H) / float(1024)
    # Because we like complexity.      12345678901234567890121234567890
    Hum = float(H >> 10) + (float(H & 0b00000000000000000000001111111111) / float(1024))

    return Hum

def sensor_parse_BME280_Pressure(DataRaw, CalDict, TFine):
    """

    
    Pressure arrives as 3 hex bytes.
    Byte struction MSB xxxx xxxx LSB xxxx xxxx XLSB xxxx 0000
    
    Output in units of hPa (Same as mbar)
    Near as I can tell from the data sheet, the output is pressure. Not compensented for altitude. (How could it be? 
    The sensor does not know its altitude)
    """
    
    #logdbg("Stoic sensor_parse_BME280_Pressure  HEX in %s" % DataHex)
    
    RawPressure = (long(DataRaw[0]) << 12) + (long(DataRaw[1]) << 4) + (long(DataRaw[2]) >> 4)
    
    #logdbg("Stoic sensor_parse_BME280_Pressure  RawPressure %d" % RawPressure)
    #logdbg("Stoic sensor_parse_BME280_Pressure  RawPressure %X" % RawPressure)
    
    
    # TEST Line
    #logdbg("self.stoic_Cal_dict[BME280ID+'_CAL_P6''] %d" % CalDict["P6"])
    #logdbg("self.stoic_Cal_dict[BME280ID+'_CAL_P6''] type  %s" % type(CalDict["P6"]))

    #var1 = ((BME280_S64_t)t_fine) - 128000;
    var1 = TFine - long(128000)
    
    #var2 = var1 * var1 * (BME280_S64_t)dig_P6;
    var2 = var1 * var1 * CalDict["P6"]
    
    #var2 = var2 + ((var1*(BME280_S64_t)dig_P5)<<17);
    var2 = var2 + ( (var1*CalDict["P5"]) << 17)
    
    #var2 = var2 + (((BME280_S64_t)dig_P4)<<35);
    var2 = var2 + ((CalDict["P4"]) << 35)
    
    #var1 = ((var1 * var1 * (BME280_S64_t)dig_P3)>>8) + ((var1 * (BME280_S64_t)dig_P2)<<12);
    var1 = ((var1 * var1 * CalDict["P3"]) >> 8) + ((var1 * CalDict["P2"]) << 12)
    
    #var1 = (((((BME280_S64_t)1)<<47)+var1))*((BME280_S64_t)dig_P1)>>33;
    var1 = ( ( (long(1)<<47) + var1 ) * (CalDict["P1"]) ) >> 33
    
    #if (var1 == 0) {return 0; // avoid exception caused by division by zero}
    # This avoides a division by zero
    if(var1 == 0):
        return 0
    # TODO When will this actually be zero. Should it return none?
    
    #p = 1048576-adc_P;
    p = long(1048576) - RawPressure
    
    
    #p = (((p<<31)-var2)*3125)/var1;
    p = ( ((p<<31)-var2 ) * long(3125) ) / var1
    
    
    #var1 = (((BME280_S64_t)dig_P9) * (p>>13) * (p>>13)) >> 25;
    var1 = ((CalDict["P9"]) * (p>>13) * (p>>13)) >> 25
    
    #var2 = (((BME280_S64_t)dig_P8) * p) >> 19;
    var2 = ((CalDict["P9"]) * p) >> 19
    
    #p = ((p + var1 + var2) >> 8) + (((BME280_S64_t)dig_P7)<<4);
    p = ((p + var1 + var2) >> 8) + (CalDict["P7"] << 4)
    
# p is integer pressure. p / 256  gives Pa.  (p / 256) / 100 gives hPa
    #logdbg("Stoic sensor_parse_BME280_Pressure  Integer Pressure %d" % p)
    #logdbg("Stoic sensor_parse_BME280_Pressure  Integer Pressure %X" % p)
    
    # Units of hPa or mbar (same thing)
    Pressure = float(p) / float(25600.0)

    #logdbg("Stoic sensor_parse_BME280_Pressure Pressure %f" % Pressure)

    return Pressure
    
def CalcTPH(DataRaw,CalDict):
    TFine = sensor_parse_BME280_TFine(DataRaw, CalDict)
    if TFine == None:
        return None
    
    print(TFine)
    
    Temperature = sensor_parse_BME280_Temperature(TFine)
    
    print(Temperature)
    
    Humidity = sensor_parse_BME280_Humidity(DataRaw, CalDict, TFine)
    
    print(Humidity)
    
    Pressure = sensor_parse_BME280_Pressure(DataRaw, CalDict, TFine)
    
    print(Pressure)
    
    Temperature = round(Temperature,2)
    Humidity = round(Humidity,2)
    Pressure = round(Pressure,2)
    
    DataDict = dict()
    DataDict["Temperature"] = Temperature
    DataDict["Humidity"] = Humidity
    DataDict["Pressure"] = Pressure
    
    return DataDict


# Main
CalDict = ReadCalibrationDict()

InitializeBME280()

DataRaw = ObtainDataFromBME280()

# Test Line
for value in DataRaw:
     WriteLogEntry(str(value))
     

DataDict = CalcTPH(DataRaw,CalDict)

# now for the hard part
# http://twistedmatrix.com/documents/current/core/examples/

def SendData(DataDict):
    # TODO add soft coding for the IP and port
    destination = TCP4ClientEndpoint(reactor, '192.168.0.7', 1212)
    ReceiveConformationDeferred = connectProtocol(destination, AMP())
    
    # This runs to send the data
    def connected(ampProto):
        return ampProto.callRemote(IndoorPiA, TA=DataDict["Temperature"], PA=DataDict["Pressure"], HA=DataDict["Humidity"])
    ReceiveConformationDeferred.addCallback(connected)
    def summed(result):
        return result['cksu']
    ReceiveConformationDeferred.addCallback(summed)


    def done(result):
        print('Done sending data to Stoic:', result)
        reactor.stop()
    defer.DeferredList([ReceiveConformationDeferred]).addCallback(done)


SendData(DataDict)
reactor.run()



