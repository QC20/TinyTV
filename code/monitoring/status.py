#!/usr/bin/env python3
from ina219 import INA219, DeviceRangeError
import time
import os
import psutil
import subprocess
import socket
from datetime import datetime
import zoneinfo

# =============================================================================
# HARDWARE CONFIGURATION (INA219 Battery HAT)
# =============================================================================
SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.4
INA219_ADDRESS = 0x43
BATTERY_CAPACITY_MAH = 10600
BATTERY_FULL_V = 4.2
BATTERY_EMPTY_V = 3.0

ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=INA219_ADDRESS)
ina.configure(voltage_range=ina.RANGE_16V,
              gain=ina.GAIN_1_40MV,
              bus_adc=ina.ADC_128SAMP,
              shunt_adc=ina.ADC_128SAMP)

# Copenhagen Timezone
try:
    cph_tz = zoneinfo.ZoneInfo("Europe/Copenhagen")
except:
    cph_tz = None

# =============================================================================
# DATA GATHERING HELPERS
# =============================================================================
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000.0
    except: return 0.0

def get_size(bytes_val):
    for unit in ['', 'K', 'M', 'G', 'T']:
        if bytes_val < 1024: return f"{bytes_val:.1f}{unit}B"
        bytes_val /= 1024

def get_vcgencmd(cmd):
    try:
        return subprocess.check_output(f"vcgencmd {cmd}", shell=True).decode("utf-8").strip().split("=")[-1]
    except: return "N/A"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "Offline"

def get_wifi_signal():
    try:
        with open("/proc/net/wireless", "r") as f:
            lines = f.readlines()
            if len(lines) > 2:
                return f"{lines[2].split()[3].replace('.', '')} dBm"
    except: pass
    return "N/A"

# Baseline for Network
last_net_io = psutil.net_io_counters()
last_time = time.time()

# =============================================================================
# MAIN MONITORING LOOP
# =============================================================================
try:
    while True:
        curr_time = time.time()
        dt_now = datetime.now(cph_tz) if cph_tz else datetime.now()
        elapsed = curr_time - last_time
        
        # 1. BATTERY TELEMETRY
        bus_v = ina.voltage()
        current_ma = ina.current()
        power_mw = ina.power()
        shunt_mv = ina.shunt_voltage()
        bat_pct = max(0, min(100, ((bus_v - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V)) * 100))
        
        # 2. PERFORMANCE DATA
        cpu_usage_total = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        cpu_temp = get_cpu_temp()
        load_avg = os.getloadavg()
        cpu_freq = psutil.cpu_freq().current
        gpu_freq_raw = get_vcgencmd("measure_clock gpu")
        gpu_mhz = int(gpu_freq_raw)//1000000 if gpu_freq_raw != "N/A" else 0
        throttled = get_vcgencmd("get_throttled")
        
        # 3. RESOURCE DATA
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')
        io_wait = getattr(psutil.cpu_times_percent(), 'iowait', 0.0)
        
        # 4. TOP PROCESSES
        procs = [p.info for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent'])]
        top_cpu = max(procs, key=lambda p: p['cpu_percent'])
        top_mem = max(procs, key=lambda p: p['memory_percent'])
        
        # 5. NETWORK
        net_io = psutil.net_io_counters()
        dl_speed = (net_io.bytes_recv - last_net_io.bytes_recv) / elapsed
        ul_speed = (net_io.bytes_sent - last_net_io.bytes_sent) / elapsed

        # --- CALCULATE POWER STATE ---
        if current_ma > 5:
            p_state = "DISCHARGING 🔋"
            rem_mah = (bat_pct / 100) * BATTERY_CAPACITY_MAH
            hours = rem_mah / current_ma
            time_msg = f"{int(hours)}h {int((hours*60)%60)}m left"
        elif current_ma < -5:
            p_state = "CHARGING ⚡"
            to_fill = BATTERY_CAPACITY_MAH * (100 - bat_pct) / 100
            hours = to_fill / abs(current_ma)
            time_msg = f"{int(hours)}h {int((hours*60)%60)}m to full"
        else:
            p_state = "IDLE/BALANCED ✅"
            time_msg = "Stable"

        # --- DISPLAY OUTPUT ---
        os.system('clear')
        print("=" * 68)
        print(f" PI-DASHBOARD ULTIMATE | {dt_now.strftime('%Y-%m-%d %H:%M:%S')} | 1.0s")
        print("=" * 68)

        # BATTERY SECTION
        print(f"POWER & BATTERY:")
        print(f"  Status:       {p_state:<20} | Net Flow:   {abs(current_ma):7.1f} mA")
        print(f"  Level:        {bat_pct:5.1f}% {'(LOW BATTERY!)' if bat_pct < 15 else ''}")
        print(f"  Voltage:      {bus_v:6.3f} V             | Power Draw: {power_mw:7.1f} mW")
        print(f"  Estimate:     {time_msg:<20} | Shunt:      {shunt_mv:7.3f} mV")
        print("-" * 68)

        # COMPUTE SECTION
        print(f"CPU & THERMALS:")
        print(f"  Total Usage:  {cpu_usage_total:5.1f}%             | Temperature: {cpu_temp:5.1f}°C")
        if cpu_temp > 80: print("  >> WARNING: CPU TEMPERATURE CRITICAL! <<")
        
        core_str = "  Cores:        " + " ".join([f"[{int(c)}%]" for c in cpu_cores])
        print(core_str)
        print(f"  Frequency:    {int(cpu_freq)} MHz (CPU)     | {gpu_mhz:4} MHz (GPU)")
        print(f"  Load (Queue): 1m:{load_avg[0]:.2f} 5m:{load_avg[1]:.2f} 15m:{load_avg[2]:.2f}")
        print(f"  IO Wait:      {io_wait:5.1f}% (Disk Latency)")
        print("-" * 68)

        # RESOURCES SECTION
        print(f"SYSTEM RESOURCES:")
        print(f"  RAM Usage:    {ram.percent:5.1f}%  ({get_size(ram.used)} / {get_size(ram.total)})")
        print(f"  Swap Usage:   {swap.percent:5.1f}%  ({get_size(swap.used)} / {get_size(swap.total)})")
        print(f"  Disk Space:   {disk.percent:5.1f}%  ({get_size(disk.used)} / {get_size(disk.total)})")
        print(f"  Top CPU:      {top_cpu['name'][:15]} ({top_cpu['cpu_percent']}%)")
        print(f"  Top Memory:   {top_mem['name'][:15]} ({top_mem['memory_percent']:.1f}%)")
        print("-" * 68)

        # NETWORK & HEALTH
        print(f"NETWORK & FIRMWARE HEALTH:")
        print(f"  IP Address:   {get_ip():<15}      | WiFi Signal: {get_wifi_signal()}")
        print(f"  Network:      DL: {get_size(dl_speed)}/s      | UL: {get_size(ul_speed)}/s")
        
        h_status = "HEALTHY" if throttled == "0x0" else f"ISSUE ({throttled})"
        print(f"  Firmware:     {h_status}")
        if throttled != "0x0":
            f_val = int(throttled, 16)
            if f_val & 0x1:     print("  >> ALERT: Under-voltage NOW! Check Power/Cable.")
            if f_val & 0x20000: print("  >> ALERT: Under-voltage previously recorded.")

        print("=" * 68)
        print(" Press Ctrl+C to Exit...")

        # Update baseline
        last_net_io = net_io
        last_time = curr_time
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\n\nMonitor closed.")
