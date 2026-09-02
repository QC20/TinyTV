# Monitoring

Diagnostics for the UPS HAT, run over SSH. None of this is needed for playback.

| Script | What it shows |
| --- | --- |
| `battery-monitor.py` | One reading: voltage, current, power, shunt voltage |
| `battery_watch.py` | The same on a 3-second loop, plus charge state and a runtime estimate |
| `status.py` | Full dashboard — battery, CPU load and temperature, GPU clock, RAM, disk, network throughput, top processes, and firmware throttle flags |

All three talk to the INA219 on the UPS HAT at I²C address `0x43`, with a 0.1 Ω
shunt. Capacity is hardcoded to 10600 mAh (2× 5300 mAh); change
`BATTERY_CAPACITY_MAH` if your pack differs.

Battery percentage is interpolated from voltage between 3.0 V and 4.2 V. That's
a rough approximation — lithium cells sit near 3.7 V for most of their discharge,
so the middle of the range reads low and the number moves in jumps.

```bash
pip3 install pi-ina219 psutil
python3 status.py
```

I²C needs to be enabled (`raspi-config` → Interface Options → I2C).
