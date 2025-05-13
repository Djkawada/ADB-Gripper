# ADB Gripper![unnamed](https://github.com/user-attachments/assets/3932e1c9-c73a-49c4-8439-aff8800ca67c)


A simple and modern GUI application for Windows, designed to facilitate the management of your Android devices via Android Debug Bridge (ADB).

## About

ADB Gripper offers a user-friendly interface to perform common operations via ADB without needing to use the command line. Connect your devices and manage them easily.

## Features

* Lists connected Android devices via USB or TCP/IP (`adb devices`).
* Allows connecting to a device by its IP address and port (`adb connect`).
* Displays basic information about the selected device (model, Android version, battery level).
* "Device Control" Tab:
    * Reboot device normally (`adb reboot`).
    * Reboot to Recovery mode (`adb reboot recovery`).
    * Reboot to Bootloader mode (`adb reboot bootloader`).
    * Power off the device (`adb shell reboot -p`).
 ![Capture d’écran 2025-05-13 155901](https://github.com/user-attachments/assets/3c5b0ca6-aaa1-4da8-a365-47119fb72998)
* "App Management" Tab:
    * Install an APK file on the selected device (`adb install`).
    * List installed applications (user apps or all apps).
    * Uninstall selected applications (`adb uninstall --user 0`).
    * Disable selected applications (useful for non-uninstallable system apps, uses `adb shell pm disable-user`).
![Capture d’écran 2025-05-13 160008](https://github.com/user-attachments/assets/02949f2e-7650-45ae-98ae-4bfc4bd6c2b3)
<img width="668" alt="Capture d’écran 2025-05-13 160043" src="https://github.com/user-attachments/assets/3b80dd37-cb0e-47e2-af94-ba9e0de150a9" />

## Prerequisites

To use ADB Gripper, you **must** have:

1.  **Android SDK Platform-Tools:** This package contains the `adb` tool.
    * **Mandatory Requirement:** You can install the Platform Tools and ensure ADB is correctly added to your system's PATH by using my dedicated installer project available on GitHub: **[ADB Path Checker Installer](https://github.com/Djkawada/ADB-Path-Checker-Installer)**. Please visit the repository and follow the instructions there to get ADB properly set up on your system.
2.  **ADB configured in your system's PATH:** The path to the directory containing `adb.exe` (usually the `platform-tools` folder within the Android SDK) must be added to your operating system's PATH environment variable. The linked project above should help with this.

If the `adb` command is not recognized in your terminal or command prompt, the application will not be able to function.

## Installation and Usage

You can run the application in two ways:

### 1. Run from Source Files (Requires Python)

1.  **Install Python:** Ensure you have Python 3.x installed.
2.  **Clone the Repository:** Clone this GitHub repository or download the source files.
3.  **Install Python Dependencies:** Open a terminal or command prompt in the project directory and install the necessary libraries:
    ```bash
    pip install customtkinter
    # The application also depends on tkinter and threading, which are included with standard Python.
    ```
4.  **Run the Application:** Launch the main script:
    ```bash
    python main_app.py
    ```

### 2. Use the Executable (.exe)

If an executable has been compiled (e.g., using PyInstaller as described below), you can simply download the `.exe` file from the [Releases](https://github.com/Djkawada/ADB-Gripper/releases/tag/V1.0.0) section of this repository and run it directly.

**Note:** Even when using the executable, the prerequisite of **ADB configured in your PATH** is still necessary.

## Building the Executable (for Developers)

If you want to compile the application into an `.exe` file yourself, you can use PyInstaller:

1.  **Install PyInstaller:** `pip install pyinstaller`
2.  **Navigate to the Project Directory:** Open your terminal in the folder containing `main_app.py`.
3.  **Run the PyInstaller Command:**
    ```bash
    pyinstaller --onefile --windowed --icon=your_icon.ico main_app.py
    ```
    Replace `your_icon.ico` with the name of your Windows Icon (`.ico`) file.
4.  The executable (`main_app.exe`) will be generated in the `dist` sub-directory.

## Contribution

If you would like to contribute to the project, please send me a pull request or create a new branch for your changes.

## License

[Add your project's license information here, e.g., MIT, GPL, etc. If you haven't chosen a license yet, GitHub allows you to add one.]
