#!/usr/bin/env python3
from ina219 import INA219, DeviceRangeError
import time

# Configure for low power measurements
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.4  # 400mA max - better resolution for Pi

ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x43)
ina.configure(voltage_range=ina.RANGE_16V,
              gain=ina.GAIN_1_40MV,  # Better for small currents
              bus_adc=ina.ADC_128SAMP,
              shunt_adc=ina.ADC_128SAMP)

# Battery specs
BATTERY_CAPACITY_MAH = 10600  # 2x 5300mAh
BATTERY_NOMINAL_V = 3.7
BATTERY_FULL_V = 4.2
BATTERY_EMPTY_V = 3.0

print("Advanced Battery Monitor")
print("=" * 60)

try:
    while True:
        try:
            bus_v = ina.voltage()
            current_ma = ina.current()
            power_mw = ina.power()
            shunt_mv = ina.shunt_voltage()
            
            # Determine state
            if current_ma < -5:
                state = "CHARGING"
            elif current_ma > 5:
                state = "DISCHARGING"
            else:
                state = "IDLE/FULL"
            
            # Calculate battery percentage (rough estimate based on voltage)
            if bus_v > BATTERY_EMPTY_V:
                battery_pct = ((bus_v - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V)) * 100
                battery_pct = min(100, max(0, battery_pct))
            else:
                battery_pct = 0
            
            # Estimate runtime (if discharging)
            if current_ma > 5:
                runtime_hours = BATTERY_CAPACITY_MAH / current_ma
                runtime_mins = runtime_hours * 60
                runtime_str = f"{int(runtime_hours)}h {int(runtime_mins % 60)}m"
            elif current_ma < -5:
                # Charging - estimate time to full
                remaining_mah = BATTERY_CAPACITY_MAH * (100 - battery_pct) / 100
                charge_hours = remaining_mah / abs(current_ma)
                charge_mins = charge_hours * 60
                runtime_str = f"Charge time: {int(charge_hours)}h {int(charge_mins % 60)}m"
            else:
                runtime_str = "N/A (idle)"
            
            print(f"\nVoltage: {bus_v:.3f}V | Current: {current_ma:7.1f}mA | Power: {power_mw:7.1f}mW")
            print(f"Shunt: {shunt_mv:.3f}mV | State: {state:12s} | Battery: ~{battery_pct:.0f}%")
            print(f"Runtime estimate: {runtime_str}")
            print("-" * 60)
            
            time.sleep(3)
            
        except DeviceRangeError as e:
            # sensor can throw if the reading is out of range; just report and retry
            print(f"DeviceRangeError: {e}")
            time.sleep(1)

except KeyboardInterrupt:
    # graceful shutdown on Ctrl-C
    print("\nExiting battery monitor")
