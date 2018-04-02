#!/usr/bin/env python
# Read BME280 Calibration Data
# Version 0.0.1
# 2018-04-01
# Stoic Weather Watch
# Reads the calibration data from a BME280 connected to an R Pi

import smbus
import csv

bus = smbus.SMBus(1)

I2CADDRESS = 0x77

BME280_CAL1_BLK_REG    = int("E1",16)
BME280_CAL1_BLK_LEN    = 8
BME280_CAL2_BLK_REG    = int("88",16)
BME280_CAL2_BLK_LEN    = 27

FILE_OUT = "BME280CalDict.csv"

def ReadI2CReg(Reg):
    Value = bus.read_byte_data(I2CADDRESS, Reg)
    return Value

def ReadBME280CalReg():
    """
    This returns a dictionary of calibration registry values
    """
    RegDict = dict()
    
    for Reg in range(BME280_CAL2_BLK_REG, BME280_CAL2_BLK_REG + BME280_CAL2_BLK_LEN - 1):
        Value = ReadI2CReg(Reg)
        RegDict["2."+str(Reg - BME280_CAL2_BLK_REG)] = Value
        #print("Reg %X  :   %X" %(Reg,Value))
        
    for Reg in range(BME280_CAL1_BLK_REG, BME280_CAL1_BLK_REG + BME280_CAL1_BLK_LEN - 1):
        Value = ReadI2CReg(Reg)
        RegDict["1."+str(Reg - BME280_CAL1_BLK_REG)] = Value
        #print("Reg %X  :   %X" %(Reg,Value))
        
    return RegDict

def BoschHEXHEX2UnsignedLong(msb,lsb):
    """
    BME 280 has funky ways to storing values. This takes two bytes and makes an unsigned long
    """

    return  ((long(msb) << 8) + long(lsb))
            
def BoschHEXHEX2SignedLong(msb,lsb):
    """
    BME 280 has funky ways to storing values. This takes two bytes and makes a signed long
    """
            
    if((long(msb) >> 7) == 1):
        sign = long(-1)
    else:
        sign = long(1)

    return (sign * (((long(msb) & 0b01111111) << 8) + long(lsb)))
    
def CalcCalValues(CalRegDict):
    """
    Converts the raw registry values into the calibration values
    """
    CalDict = dict()
    #  Data sheet T1 unsigned 
    CalDict["T1"] = BoschHEXHEX2UnsignedLong(CalRegDict.get("2.1"),CalRegDict.get("2.0"))
    #  Data sheet T2 signed 
    CalDict["T2"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.3"),CalRegDict.get("2.2"))
    #  Data sheet T3 Signed
    CalDict["T3"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.5"),CalRegDict.get("2.4"))
    #  Data sheet P1 Unsigned
    CalDict["P1"] = BoschHEXHEX2UnsignedLong(CalRegDict.get("2.7"),CalRegDict.get("2.6"))
    #  Data sheet P2 signed
    CalDict["P2"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.9"),CalRegDict.get("2.8"))
    #  Data sheet P3 signed
    CalDict["P3"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.11"),CalRegDict.get("2.10"))
    #  Data sheet P4 signed
    CalDict["P4"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.13"),CalRegDict.get("2.12"))
    #  Data sheet P5 signed
    CalDict["P5"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.15"),CalRegDict.get("2.14"))
    #  Data sheet P6 signed
    CalDict["P6"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.17"),CalRegDict.get("2.16"))
    #  Data sheet P7 signed
    CalDict["P7"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.19"),CalRegDict.get("2.18"))
    #  Data sheet P8 signed 
    CalDict["P8"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.21"),CalRegDict.get("2.20"))
    #  Data sheet P9 signed
    CalDict["P9"] = BoschHEXHEX2SignedLong(CalRegDict.get("2.23"),CalRegDict.get("2.22"))
    #  Data sheet H1 unsigned single byte memory A1
    #   A0 is skipped
    CalDict["H1"] = BoschHEXHEX2UnsignedLong("00",CalRegDict.get("2.25"))
    #  Data sheet H2 signed memory E1 and E2
    CalDict["H2"] = BoschHEXHEX2SignedLong(CalRegDict.get("1.1"),CalRegDict.get("1.0"))
    #  Data sheet H3 unsigned single byte memory E3
    CalDict["H3"] = BoschHEXHEX2UnsignedLong("00",CalRegDict.get("1.2"))
    #  Data sheet H4 signed 12 bits. E4 holds the most significant 8 and the least significant 4 are the low 4 of E5
    sign = -1 if (long(CalRegDict.get("1.3")) >> 7 == 1) else 1
    CalDict["H4"] = (long(sign) * (((long(CalRegDict.get("1.3")) & 0b01111111) << 4) + (long(CalRegDict.get("1.4")) & 0b00001111) ))
    #  Data sheet H5 signed 12 bits. E5 holds the least significant 4 bits in its high 4 and E6 holds the most significant bits
    sign = -1 if (long(CalRegDict.get("1.5")) >> 7 == 1) else 1
    CalDict["H5"] = (long(sign) * (((long(CalRegDict.get("1.5")) & 0b01111111) << 4) + (long(CalRegDict.get("1.4")) >> 4) ))
    #  Data sheet H6 signed byte E7
    sign = -1 if (long(CalRegDict.get("1.6")) >> 7 == 1) else 1
    CalDict["H6"] = long(sign) * (long(CalRegDict.get("1.6")) & 0b01111111)
    
    return CalDict

def WriteCalDictToFile(CalDict):
    with open(FILE_OUT, 'w') as csv_file:
        writer = csv.writer(csv_file)
        for key, value in CalDict.items():
            writer.writerow([key, value])
        
  
RegDict = ReadBME280CalReg()

CalDict = CalcCalValues(RegDict)

WriteCalDictToFile(CalDict)

with open(FILE_OUT, 'r') as csv_file:
    reader = csv.reader(csv_file)
    mydict = dict(reader)

# Does nto work
# map(long,mydict.itervalues())

for key in mydict:
    mydict[key] = long(mydict[key])

print(mydict)

print(mydict["H6"] + mydict["H5"])


