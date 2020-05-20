#!/usr/bin/python3
#requires python3-smbus

import smbus
from time import sleep

capacity_remain = 0
capacity_full = 1
capacity_avail = 2
capacity_avail_full = 3
capacity_remain_f = 4
capacity_remain_uf = 5
capacity_full_f = 6
capacity_full_uf = 7
capacity_design = 8

current_avg = 0
current_stby = 1
current_max = 2

soh_percent = 0

soc_filtered = 0
soc_unfiltered = 1

temp_battery = 0
temp_internal = 1

gpoutfunction_bat_low = 1
gpoutfunction_soc_int = 0

_userConfigControl = False
_sealFlag = False
_deviceAddress = 0x55
Timeout = 2000

def begin(channel):
	global bus
	bus = smbus.SMBus(channel)
	if deviceType() == 0x0421:
		return True
	return False

def readControlWord(function):
	bus.write_word_data(_deviceAddress, 0x00, function)
	return bus.read_word_data(_deviceAddress, 0x00)

def readWord(subAddress):
	return bus.read_word_data(_deviceAddress, subAddress)

def executeControlWord(function):
	try:
		bus.write_word_data(_deviceAddress, 0x00, function)
	except:
		return False
	return True

def flags():
	return readWord(0x06)

def enterConfig(userControl = True):
	if userControl:
		_userConfigControl = True
	if sealed():
		_sealFlag = True
		unseal()
	if executeControlWord(0x0013):
		timeout = Timeout
		while timeout > 0:
			if flags() & (1 << 4):
				break
			sleep(.001)
			timeout = timeout - 1
		if timeout > 0:
			return True
	return False

def softReset():
	return executeControlWord(0x0042)

def setCapacity(capacity):
	data = [(capacity >> 8) & 0xff, capacity & 0xff]
	return writeExtendedData(82, 10, data, 2)

def setDesignEnergy(energy):
	data = [(energy >> 8) & 0xff, energy & 0xff]
	return writeExtendedData(82, 12, data, 2)

def setTerminateVoltage(voltage):
	if voltage < 2500:
		voltage = 2500
	if voltage > 3700:
		voltage = 3700
	data = [(voltage >> 8) & 0xff, voltage & 0xff]
	return writeExtendedData(82, 16, data, 2)

def setTaperRate(rate):
	if rate > 2000:
		rate = 2000
	data = [(rate >> 8) & 0xff, rate & 0xff]
	return writeExtendedData(82, 27, data, 2)

def exitConfig(resim = True):
	if (resim):
		if softReset():
			timeout = Timeout
			while timeout > 0:
				if not (flags() & (1 << 4)):
					break
				sleep(.001)
				timeout = timeout - 1
			if timeout > 0:
				if _sealFlag:
					seal()
				return True
		return False
	else:
		return executeControlWord(0x0043)

def writeExtendedData(classID, offset, data, len):
	if len > 32:
		return False
	if _userConfigControl == False:
		enterConfig(False)
	if blockDataControl() == False:
		return False
	if blockDataClass(classID) == False:
		return False
	blockDataOffset(int(offset / 32))
	computeBlockChecksum()
	oldCsum = blockDataChecksum()
	for i in range(len):
		writeBlockData((offset % 32) + i, data[i])
	newCsum = computeBlockChecksum()
	writeBlockChecksum(newCsum)
	if _userConfigControl == False:
		exitConfig()
	return True

def writeBlockData(offset, data):
	address = offset + 0x40
	try:
		bus.write_byte_data(_deviceAddress, address, data)
	except:
		return False
	return True

def writeBlockChecksum(csum):
	try:
		bus.write_byte_data(_deviceAddress, 0x60, csum)
	except:
		return False
	return True

def readExtendedData(classID, offset):
	retData = 0
	if _userConfigControl == False:
		enterConfig(False)
	if blockDataControl == False:
		return False
	if blockDataClass(classID) == False:
		return False
	blockDataOffset(int(offset / 32))
	computeBlockChecksum()
	oldCsum = blockDataChecksum()
	retData = readBlockData(offset % 32)
	if _userConfigControl == False:
		exitConfig()
	return retData

def readBlockData(offset):
	address = offset + 0x40
	return bus.read_byte_data(_deviceAddress, address)

def SOC1SetThreshold():
	return readExtendedData(49, 0)

def SOC1ClrThreshold():
	return readExtendedData(49, 1)

def SOCFSetThreshold():
	return readExtendedData(49, 2)

def SOCFClrThreshold():
	return readExtendedData(49, 3)

def setSOC1Thresholds(set, clear):
	data = [set, clear]
	return writeExtendedData(49, 0, data, 2)

def computeBlockChecksum():
	data = []
	csum = 0
	for i in range(32):
		data.append(bus.read_byte_data(_deviceAddress, 0x40 + i))
	for i in range(32):
		csum += data[i]
	csum = 255 - (csum & 0xff)
	return csum

def blockDataChecksum():
	return bus.read_byte_data(_deviceAddress, 0x60)

def blockDataControl():
	try:
		bus.write_byte_data(_deviceAddress, 0x61, 0x00)
	except:
		return False
	return True

def blockDataClass(id):
	try:
		bus.write_byte_data(_deviceAddress, 0x3e, id)
	except:
		return False
	return True

def blockDataOffset(offset):
	try:
		bus.write_byte_data(_deviceAddress, 0x3f, offset)
	except:
		return False
	return True

def voltage():
	return readWord(0x04)

def deviceType():
	return readControlWord(0x0001)

def status():
	return readControlWord(0x0000)

def sealed():
	stat = status()
	if stat & (1 << 13):
		return True
	return False

def seal():
	return readControlWord(0x0020)

def unseal():
	if readControlWord(0x8000):
		return readControlWord(0x8000)
	return False

def capacity(type = 0):
	capacity = 0
	if type == 0:
		capacity = readWord(0x0c)
	elif type == 1:
		capacity = readWord(0x0e)
	elif type == 2:
		capacity = readWord(0x08)
	elif type == 3:
		capacity = readWord(0x0a)
	elif type == 4:
		capacity = readWord(0x2a)
	elif type == 5:
		capacity = readWord(0x28)
	elif type == 6:
		capacity = readWord(0x2e)
	elif type == 7:
		capacity = readWord(0x2c)
	elif type == 8:
		capacity = readWord(0x3c)
	return capacity

def current(type = 0):
	current = 0
	if type == 0:
		current = readWord(0x10)
	elif type == 1:
		current = readWord(0x12)
	elif type == 2:
		current = readword(0x14)
	return current

def power():
	return readWord(0x18)

def soh(type = 0):
	sohRaw = readWord(0x20)
	sohStatus = sohRaw >> 8
	sohPercent = sohRaw & 0xff

	if (type == 0):
		return sohPercent
	else:
		return sohStatus

def temperature(type = 0):
	temp = 0
	if type == 0:
		temp = readWord(0x02)
	elif type == 1:
		temp = readWord(0x1e)
	return temp

def soc(type = 0):
	socRet = 0
	if type == 0:
		socRet = readWord(0x1c)
	elif type == 1:
		socRet = readWord(0x30)
	return socRet

def setSOCFThresholds(set, clear):
	data = [set, clear]
	return writeExtendedData(49, 2, data, 2)

def opConfig():
	return readWord(0x3a)

def GPOUTPolarity():
	opConfigRegister = opConfig()
	return (opConfigRegister & (1 << 11))

def writeOpConfig(value):
	data = [(value >> 8) & 0xff, value & 0xff]
	return writeExtendedData(64, 0, data, 2)

def setGPOUTPolarity(activeHigh):
	oldOpConfig = opConfig()
	if ((activeHigh and (oldOpConfig & (1 << 11))) or (not activeHigh and not (oldOpConfig & (1 << 11)))):
		return True
	newOpConfig = oldOpConfig
	if activeHigh:
		newOpConfig |= (1 << 11)
	else:
		newOpConfig &= ~(1 << 11)
	return writeOpConfig(newOpConfig)

def GPOUTFunction():
	opConfigRegister = opConfig()
	return (opConfigRegister & (1 << 2))

def setGPOUTFunction(function):
	oldOpConfig = opConfig()
	if ((function and (oldOpConfig & (1 << 2))) or (not function and not (oldOpConfig & (1 << 2)))):
		return True
	newOpConfig = oldOpConfig
	if function:
		newOpConfig |= (1 << 2)
	else:
		newOpConfig &= ~(1 << 2)
	return writeOpConfig(newOpConfig)

def socFlag():
	flagState = flags()
	return flagState & (1 << 2)

def socfFlag():
	flagState = flags()
	return flagState & (1 << 1)

def itporFlag():
	flagState = flags()
	return flagState & (1 << 5)

def fcFlag():
	flagState = flags()
	return flagState & (1 << 9)

def chgFlag():
	flagState = flags()
	return flagState & (1 << 8)

def dsgFlag():
	flagState = flags()
	return flagState & (1 << 0)

def sociDelta():
	return readExtendedData(82, 26)

def setSOCIDelta(delta):
	soci = delta
	if delta > 100:
		soci = 100
	if delta < 0:
		soci = 0
	return writeExtendedData(82, 26, [soci], 1)

def pulseGPOUT():
	return executeControlWord(0x0023)
