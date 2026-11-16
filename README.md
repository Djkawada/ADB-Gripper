# ADB Gripper (Rust Edition)

**ADB Gripper** is a fast, native, cross-platform Rust GUI application (`eframe` / `egui`) for managing Android devices via the Android Debug Bridge (ADB).

## Features

* **Cross-Platform Native Binary:** Single lightweight executable for **Windows**, **Linux** (Wayland & X11), and **macOS** — no Python or Tk runtime required.
* **Device Management:** List USB/TCP-IP devices, connect via IP (`adb connect`), view Manufacturer, Model, Commercial Name, Android Version, and Battery Level.
* **Device Control:** Reboot to System, Recovery, Bootloader, or Power Off.
* **App Management:** Install APKs, list User or All apps, inspect package details & permissions, and uninstall/disable selected apps.
* **Bloatware Advisor:** Automatically reads the device manufacturer/brand (Xiaomi/Redmi/POCO, Samsung, OnePlus, OPPO, Realme, Huawei, Honor, Motorola, and common preloads) and separates **Safe to Remove Without Risk** apps from **Remove with Caution** apps with full effect explanations.
* **Logcat Viewer:** Real-time logcat streaming with clear & save support.

## Prerequisites

* **Android SDK Platform-Tools (`adb`)** installed and available in your system `PATH`.

## Build & Run from Source

```bash
git clone -b rust https://github.com/Djkawada/ADB-Gripper.git
cd ADB-Gripper
cargo build --release
./target/release/adb-gripper
```

*(On Debian/Ubuntu Linux, install GUI dev headers first: `sudo apt install libgtk-3-dev libxkbcommon-dev libwayland-dev libgl1-mesa-dev pkg-config`.)*

## License

Licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).
