# Boot partition files

Copy these to the root of the SD card's `boot` partition before the Pi's first
boot. They are read once at startup and then ignored.

| File | Purpose |
| --- | --- |
| `wpa_supplicant.conf` | Wi-Fi credentials. **Fill in your own SSID and password** — the committed values are placeholders. |
| `ssh` | Empty file. Its presence enables the SSH server on first boot. |
| `waveshare-ads7846.dtbo` | Device tree overlay for the display's ADS7846 resistive touch controller. This one goes in `/boot/overlays/`, not the root. |

`config.txt` also needs the HDMI mode for the 800×480 panel — those lines are in
[../docs/pi-display-setup.md](../docs/pi-display-setup.md).
