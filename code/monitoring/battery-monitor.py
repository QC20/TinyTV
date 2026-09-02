#!/usr/bin/env python3
from ina219 import INA219
from ina219 import DeviceRangeError

# INA219 at address 0x43
ina = INA219(0.1, address=0x43)
ina.configure()

try:
    print("Battery Monitor")
    print("=" * 40)
    print(f"Bus Voltage: {ina.voltage():.3f} V")
    print(f"Current: {ina.current():.1f} mA")
    print(f"Power: {ina.power():.1f} mW")
    print(f"Shunt Voltage: {ina.shunt_voltage():.3f} mV")
except DeviceRangeError as e:
    print(f"Error: {e}")