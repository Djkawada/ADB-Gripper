# ADB Gripper

![GitHub Release](https://img.shields.io/github/v/release/Djkawada/ADB-Gripper)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/Djkawada/ADB-Gripper/build.yml)
![License](https://img.shields.io/github/license/Djkawada/ADB-Gripper)
![Downloads](https://img.shields.io/github/downloads/Djkawada/ADB-Gripper/total)

![unnamed](https://github.com/user-attachments/assets/3932e1c9-c73a-49c4-8439-aff8800ca67c)

**ADB Gripper** is a simple, modern, and cross-platform GUI application designed to simplify the management of Android devices via the Android Debug Bridge (ADB).

## About

ADB Gripper provides a user-friendly interface to perform common ADB operations without the need for command-line interaction. Whether you need to reboot a device, install an APK, or manage apps, ADB Gripper makes it easy.

## Features

*   **Cross-Platform:** Native support for **Windows**, **Linux**, and **macOS**.
*   **Device Management:**
    *   List connected devices (USB and TCP/IP).
    *   Connect to devices via IP address (`adb connect`).
    *   View detailed device info (Model, Android Version, Battery Level).
*   **Device Control:**
    *   Reboot to System, Recovery, or Bootloader.
    *   Power off device.
*   **App Management:**
    *   Install APK files.
    *   List installed applications (User apps or System apps).
    *   Uninstall or Disable applications.
    *   View detailed app information (Package name, Version, Permissions, etc.).
*   **Logcat Viewer:** Real-time logcat streaming with save functionality.

![Capture d’écran 2025-05-13 155901](https://github.com/user-attachments/assets/3c5b0ca6-aaa1-4da8-a365-47119fb72998)

## Prerequisites

To use ADB Gripper, you must have **ADB** installed and configured:

1.  **Android SDK Platform-Tools:** Ensure `adb` is installed.
    *   *Windows Users:* You can use my [ADB Path Checker Installer](https://github.com/Djkawada/ADB-Path-Checker-Installer) to easily set this up.
    *   *Linux/macOS Users:* Install via your package manager (e.g., `sudo apt install android-tools` on Ubuntu/Debian, `brew install android-platform-tools` on macOS).
2.  **System PATH:** The `adb` executable must be in your system's PATH environment variable.

## Installation

### 📥 Download Binary (Recommended)

No installation required! Simply download the latest executable for your operating system from the **[Releases Page](https://github.com/Djkawada/ADB-Gripper/releases)**.

*   **Windows:** `ADB-Gripper-Windows.exe`
*   **Linux:** `ADB-Gripper-Linux` (Make executable with `chmod +x ADB-Gripper-Linux`)
*   **macOS:** `ADB-Gripper-MacOS`

### 🐍 Run from Source

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Djkawada/ADB-Gripper.git
    cd ADB-Gripper
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: On Linux, you may also need `python3-tk`)*
3.  **Run the app:**
    ```bash
    python main_app.py
    ```

### 🐧 Arch Linux (AUR)

If you are on Arch Linux, you can install it from the AUR:

```bash
yay -S adb-gripper
```

## Building

To build the executable yourself using PyInstaller:

1.  Install PyInstaller: `pip install pyinstaller`
2.  Run the build command for your platform:

    **Windows:**
    ```bash
    pyinstaller --noconfirm --onefile --windowed --icon "mon_icone.ico" --name "ADB-Gripper-Windows" --collect-all customtkinter main_app.py
    ```

    **Linux/macOS:**
    ```bash
    pyinstaller --noconfirm --onefile --windowed --name "ADB-Gripper-Linux" --collect-all customtkinter main_app.py
    ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.