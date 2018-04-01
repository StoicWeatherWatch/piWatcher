# Stoic Weather Watch
# Reads the calibration data from a BME280 connected to an R Pi

import smbus

bus = smbus.SMBus(1)

Address = 0x77

BME280_CAL1_BLK_REG    = int("E1",16)
BME280_CAL1_BLK_LEN    = 8
BME280_CAL2_BLK_REG    = int("88",16)
BME280_CAL2_BLK_LEN    = 26

def ReadI2CReg(Reg):
  Value = bus.read_byte_data(Address, Reg)
  return Value

def ReadBME280Cal():
  for Reg in range(BME280_CAL2_BLK_REG, BME280_CAL2_BLK_REG + BME280_CAL2_BLK_LEN - 1):
    Value = ReadI2CReg(Reg)
    print("Reg %X  :   %X" %(Reg,Value))
  
ReadBME280Cal()
  
