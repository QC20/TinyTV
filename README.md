# TinyTV


# Raspberry Pi + Waveshare 4" (800×480) HDMI LCD Setup

This guide walks you through the **exact steps** needed to get a Waveshare 4-inch HDMI LCD (800×480) working on a Raspberry Pi (headless), including Wi-Fi/SSH setup, display configuration, and touchscreen overlay. By following these instructions—along with the links below—you’ll be able to reproduce this configuration on your own Pi.

---

## 📋 Prerequisites

- **Raspberry Pi** (any model with HDMI output)
- **microSD card** (≥8 GB)
- **Waveshare 4″ HDMI LCD (800×480)**
- **micro USB power supply** (≥2 A recommended)
- **A computer** (Windows/macOS/Linux) with:
  - SD-card reader
  - Text editor (e.g., Sublime, VS Code, Notepad++)

---

## 🔧 1. Download & Flash Raspberry Pi OS

1. Download the latest Raspberry Pi OS image from the official Raspberry Pi website:
   - https://www.raspberrypi.com/software/ (choose “Raspberry Pi OS Lite” for a headless setup)

2. Flash the image to your microSD card using **Raspberry Pi Imager** or **BalenaEtcher**:
   - Raspberry Pi Imager: https://www.raspberrypi.com/software/
   - BalenaEtcher: https://www.balena.io/etcher/

3. Once flashing completes, eject and re-insert the microSD card. It should mount on your computer as a drive named `boot`.

---

## 🛰️ 2. Headless Wi-Fi & SSH Setup

> These two steps let your Pi connect to Wi-Fi on first boot and enable SSH access.

1. **Create `wpa_supplicant.conf`**
   In your preferred text editor, paste:
   ```conf
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1

   network={
       ssid="YOUR_WIFI_SSID"
       psk="YOUR_WIFI_PASSWORD"
   }
   ```
   Replace `YOUR_WIFI_SSID` and `YOUR_WIFI_PASSWORD` exactly (case-sensitive).

   Change `country=US` to your two-letter ISO country code if you’re not in the U.S. (e.g., GB, DE, DK).

   Save the file as `wpa_supplicant.conf` to the root of the `boot` partition (the same folder as `config.txt`).

2. **Create an empty `ssh` file** (no extension) in the root of the `boot` partition.

   On Windows: Right-click → New → Text Document → Rename to `ssh` (remove `.txt`).

   On macOS/Linux:
   ```bash
   touch /Volumes/boot/ssh
   ```
   This blank file tells Raspberry Pi OS to enable the SSH server on first boot.

---

## 🖥️ 3. Display Configuration (config.txt)

The Waveshare 4″ HDMI LCD requires a custom HDMI mode + optional touchscreen overlay. Edit the existing `config.txt` on the `boot` partition as follows:

1. Open `/boot/config.txt` in your text editor.

2. Scroll down to the bottom and add (or replace) these lines under the `[all]` section (create `[all]` if it isn’t already there):

   ```ini
   [all]
   # Use a custom HDMI mode for 800×480 @ 60 Hz
   hdmi_group=2
   hdmi_mode=87
   hdmi_cvt=800 480 60 6 0 0 0
   hdmi_drive=2

   # Rotate the display 90° clockwise (adjust if you want a different orientation)
   display_rotate=1

   # Enable GPIO 18 to control the backlight (Waveshare’s wiring)
   gpio=18=op,dh
   ```
   - `hdmi_group=2` + `hdmi_mode=87` + `hdmi_cvt` → forces Pi to output 800×480
   - `display_rotate=1` → rotates the screen upright (change to `2`/`3`/`0` as needed)
   - `gpio=18=op,dh` → configures GPIO 18 as an output and drives it HIGH at boot (powers the backlight)

3. Save and close `config.txt`.

---

## 💾 4. Touchscreen Overlay (.dtbo)

If your particular Waveshare model includes a resistive touchscreen controller (ADS7846), add the Device Tree overlay so the touchscreen works.

1. **Download the `.dtbo` file:**
   Official wiki for Waveshare 4″ HDMI LCD:
   https://www.waveshare.com/wiki/4inch_HDMI_LCD

   Under “Resources → Raspbian Driver,” locate and download `waveshare-ads7846.dtbo`.

2. **Copy `waveshare-ads7846.dtbo` into the Pi’s overlays folder:**
   Insert the SD card if it’s not already mounted.

   Copy `waveshare-ads7846.dtbo` to:
   ```bash
   /boot/overlays/
   ```

3. **Enable the overlay:**
   Edit `config.txt` again (the same file in `/boot/`), and add this line below your HDMI settings:

   ```ini
   dtoverlay=waveshare-ads7846,penirq=25,xmin=150,xmax=3900,ymin=100,ymax=3950,speed=50000
   ```
   This configures the ADS7846 touchscreen on GPIO 25 (`PENIRQ`) and calibrates X/Y ranges.

   Adjust `xmin`/`xmax`/`ymin`/`ymax` if you need further calibration.

4. Save/close `config.txt`.

---

## 🔌 5. Final Steps & Boot

1. Eject the microSD card safely from your computer.
2. Insert it into your Raspberry Pi.
3. Connect the OLED/HDMI cable from Pi → Waveshare LCD.
4. Connect your micro USB power (≥2 A).

The LCD’s backlight should turn on automatically. You should see boot text on the screen (e.g., kernel messages).

**SSH into your Pi** (if Wi-Fi is configured):

```bash
ssh pi@<YOUR_PI_IP_ADDRESS>
# Default password: raspberry
```
If you’re unsure of the Pi’s IP, attach an HDMI monitor or check your router’s DHCP list.

---

## 🧪 6. Verify & Troubleshoot

**No image on LCD:**
- Double-check that `hdmi_cvt=800 480 60 6 0 0 0` is correct and under `[all]`.
- Make sure `hdmi_drive=2` is present (enables HDMI sound/backlight).
- Verify `gpio=18=op,dh` if backlight stays off.
- Try a different HDMI cable or port.

**Touchscreen not responding:**
- Ensure `waveshare-ads7846.dtbo` is in `/boot/overlays/`.
- Confirm `dtoverlay=waveshare-ads7846,...` is at the bottom of `config.txt`.
- Check GPIO 25 (“PENIRQ”) wiring.
- For further calibration, see Waveshare’s ADS7846 documentation:
  https://www.waveshare.com/wiki/4inch_HDMI_LCD

**Headless/Wi-Fi issues:**
- Make sure `wpa_supplicant.conf` is in `/boot/`.
- Confirm SSID/PSK are correct (case-sensitive).
- Reboot Pi, then check router’s DHCP table for the Pi’s IP.

---

## 🔗 Reference Links

- **Waveshare 4″ HDMI LCD Wiki** (official driver & .dtbo downloads):
  https://www.waveshare.com/wiki/4inch_HDMI_LCD

- **Raspberry Pi OS Download & Imager**:
  https://www.raspberrypi.com/software/

- **Headless SSH & Wi-Fi Setup Guide** (Raspberry Pi Foundation):
  https://www.raspberrypi.com/documentation/computers/configuration.html#configuring-networking-ssh-and-headless-operation
