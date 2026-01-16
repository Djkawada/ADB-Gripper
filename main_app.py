# ADB Gripper - A simple and modern GUI application to manage Android devices via ADB
# Copyright (C) 2025 Djkawada
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import customtkinter as ctk
import tkinter as tk
import os
import sys
import threading # Import threading for potentially long ADB operations
import tkinter.filedialog as filedialog # Needed for file selection dialog
import tkinter.messagebox as messagebox # Still useful for other messages


# Import the adb_manager
from adb_manager import AdbManager

class AdbGripperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Configuration ---
        self.title("ADB Gripper")
        self.geometry("800x600")
        self.minsize(600, 400)
        ctk.set_appearance_mode("System") # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("blue") # Themes: "blue" (default), "green", "dark-blue"

        # --- AdbManager Instance ---
        # Create an instance of AdbManager, passing the status update method
        # This checks for ADB availability on initialization
        self.adb_manager = AdbManager(self.update_status)
        self.current_device_serial = None # Variable to store the currently selected device identifier
        self.selected_apk_path = None # Variable to store the path of the selected APK file

        # Dictionary to store device info fetched by list_devices (serial -> device dict from adb devices -l)
        self.available_devices_info = {}
        # List to store the currently displayed app package names in the uninstall list
        self.current_app_packages = []
        # Dictionary to hold references to the app checkboxes for easy access {package_name: CTkCheckBox_widget}
        self.app_checkboxes = {}

        # Variable to hold the reference to the confirmation dialog window
        self.confirmation_dialog = None
        # Variable to temporarily store packages selected for uninstall during confirmation
        self._packages_to_uninstall_in_dialog = []


        # --- Layout Configuration ---
        # Use grid layout for the main window frames
        # Column 0: Left sidebar (Device Info), Column 1: Main content area (Tabs)
        # minsize ensures info pane is visible even if right pane is stretched
        self.grid_columnconfigure(0, weight=1, minsize=200)
        self.grid_columnconfigure(1, weight=4)
        # Row 0: Top connection area, Row 1: Main content + sidebar, Row 2: Status bar
        # weight 0 means the row height is determined by the widgets inside it
        # weight 1 means the row takes up any extra vertical space
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # --- Create Main Frames/Pads ---

        # Top Frame (Connection Area)
        # Use fg_color="transparent" so the window's background color shows through
        self.connection_frame = ctk.CTkFrame(self, fg_color="transparent")
        # Place in row 0, spanning both columns (0 and 1), sticking to all sides (nsew) of the grid cell
        self.connection_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        # Configure the grid layout *within* the connection_frame for its widgets
        self.connection_frame.grid_columnconfigure(0, weight=0) # "Connected Devices:" label (fixed width)
        self.connection_frame.grid_columnconfigure(1, weight=1) # Device Dropdown (expands)
        self.connection_frame.grid_columnconfigure(2, weight=0) # Refresh button (fixed width)
        self.connection_frame.grid_columnconfigure(3, weight=0) # "Connect IP:" label (fixed width)
        self.connection_frame.grid_columnconfigure(4, weight=1) # IP Entry (expands)
        self.connection_frame.grid_columnconfigure(5, weight=0) # Connect button (fixed width)
        self.connection_frame.grid_columnconfigure(6, weight=2) # Spacer column to push elements left (takes more space)
        self.connection_frame.grid_rowconfigure(0, weight=1) # Top row for connection controls
        self.connection_frame.grid_rowconfigure(1, weight=1) # Bottom row for the selected device label


        # Add widgets to the Connection Frame (placed using the connection_frame's internal grid)
        ctk.CTkLabel(self.connection_frame, text="Connected Devices:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")

        # Device Selection Dropdown - Will display formatted string "Serial (Description) [State]"
        # Initial state and text depend on adb availability check below
        self.device_combobox = ctk.CTkComboBox(self.connection_frame, values=["Loading..."], state="disabled")
        self.device_combobox.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew") # 'ew' makes it expand east-west
        # Bind the selection event - "<<ComboboxSelected>>" is a standard tkinter event name
        self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)

        # Refresh Button
        self.refresh_button = ctk.CTkButton(self.connection_frame, text="Refresh", command=self.list_devices_in_gui)
        self.refresh_button.grid(row=0, column=2, padx=(0, 20), pady=5, sticky="w")

        # IP Connect Controls
        ctk.CTkLabel(self.connection_frame, text="Connect IP:").grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")
        self.ip_entry = ctk.CTkEntry(self.connection_frame, placeholder_text="e.g., 192.168.1.10:5555")
        self.ip_entry.grid(row=0, column=4, padx=(0, 10), pady=5, sticky="ew")

        self.connect_ip_button = ctk.CTkButton(self.connection_frame, text="Connect", command=self.connect_device_by_ip)
        self.connect_ip_button.grid(row=0, column=5, padx=(0, 0), pady=5, sticky="w") # Reduced padx here

        # Spacer column to push other elements to the left
        self.connection_frame.grid_columnconfigure(6, weight=1)


        # Label to show currently selected device, spanning across all columns of the connection_frame
        # This label will show "Commercial Name (Model) (Serial)" after fetching info
        self.selected_device_label = ctk.CTkLabel(self.connection_frame, text="Selected Device: None", font=ctk.CTkFont(weight="bold"))
        self.selected_device_label.grid(row=1, column=0, columnspan=7, padx=5, pady=(0, 5), sticky="w")


        # Left Frame (Device Info Sidebar)
        # Placed in row 1, column 0. Use 'sticky="nsew"' so it fills the grid cell
        self.info_frame = ctk.CTkFrame(self) # No width specified, let grid weight and minsize handle it
        self.info_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        # Configure grid within the info_frame for vertical stacking of labels
        self.info_frame.grid_columnconfigure(0, weight=1) # Single column for labels to expand horizontally


        # Add labels for Device Info (will be populated after device selection)
        ctk.CTkLabel(self.info_frame, text="Device Information", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        self.serial_display_label = ctk.CTkLabel(self.info_frame, text="Serial: N/A", anchor="w") # Display selected device serial
        self.serial_display_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")
        self.model_label = ctk.CTkLabel(self.info_frame, text="Model: N/A", anchor="w")
        self.model_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")
        # Add Commercial Name Label
        self.commercial_name_label = ctk.CTkLabel(self.info_frame, text="Commercial Name: N/A", anchor="w")
        self.commercial_name_label.grid(row=3, column=0, padx=10, pady=2, sticky="w")

        self.android_version_label = ctk.CTkLabel(self.info_frame, text="Android Version: N/A", anchor="w")
        self.android_version_label.grid(row=4, column=0, padx=10, pady=2, sticky="w") # Shifted down

        self.battery_level_label = ctk.CTkLabel(self.info_frame, text="Battery Level: N/A", anchor="w") # Add Battery Level Label
        self.battery_level_label.grid(row=5, column=0, padx=10, pady=2, sticky="w") # Added new row

        # Configure rows in info_frame to not expand the top labels, pushing extra space down
        self.info_frame.grid_rowconfigure(0, weight=0)
        self.info_frame.grid_rowconfigure(1, weight=0)
        self.info_frame.grid_rowconfigure(2, weight=0)
        self.info_frame.grid_rowconfigure(3, weight=0) # Row for Commercial Name
        self.info_frame.grid_rowconfigure(4, weight=0) # Row for Android Version
        self.info_frame.grid_rowconfigure(5, weight=0) # Row for Battery Level
        self.info_frame.grid_rowconfigure(6, weight=1) # Dummy row with weight 1


        # Right Frame (Functionality Tabs)
        # Placed in row 1, column 1. Use 'sticky="nsew"' so it fills the grid cell
        self.functionality_tabview = ctk.CTkTabview(self)
        self.functionality_tabview.grid(row=1, column=1, sticky="nsew", padx=10, pady=5)

        # Add the tabs
        self.device_control_tab = self.functionality_tabview.add("Device Control")
        self.app_management_tab = self.functionality_tabview.add("App Management")
        self.logcat_tab = self.functionality_tabview.add("Logcat")


        # --- Populate Device Control Tab ---
        # Configure the grid within the Device Control tab frame
        self.functionality_tabview.tab("Device Control").grid_columnconfigure(0, weight=1) # Center column

        # Add buttons to the Device Control tab
        self.reboot_normal_button = ctk.CTkButton(
            self.functionality_tabview.tab("Device Control"),
            text="Reboot Normally",
            command=self.reboot_normal
        )
        self.reboot_normal_button.grid(row=0, column=0, padx=20, pady=10, sticky="ew") # 'ew' makes button expand horizontally

        self.reboot_recovery_button = ctk.CTkButton(
            self.functionality_tabview.tab("Device Control"),
            text="Reboot to Recovery",
            command=self.reboot_recovery
        )
        # Correct variable name here:
        self.reboot_recovery_button.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.reboot_bootloader_button = ctk.CTkButton(
            self.functionality_tabview.tab("Device Control"),
            text="Reboot to Bootloader",
            command=self.reboot_bootloader
        )
        self.reboot_bootloader_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.power_off_button = ctk.CTkButton(
            self.functionality_tabview.tab("Device Control"),
            text="Power Off",
            command=self.power_off,
            fg_color="darkred", # Use a different color for Power Off
            hover_color="red"
        )
        self.power_off_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # Configure rows in Device Control tab to not expand unnecessarily, push space below buttons
        self.functionality_tabview.tab("Device Control").grid_rowconfigure(0, weight=0)
        self.functionality_tabview.tab("Device Control").grid_rowconfigure(1, weight=0)
        self.functionality_tabview.tab("Device Control").grid_rowconfigure(2, weight=0)
        self.functionality_tabview.tab("Device Control").grid_rowconfigure(3, weight=0)
        self.functionality_tabview.tab("Device Control").grid_rowconfigure(4, weight=1) # Spacer row


        # --- Populate App Management Tab ---
        self.functionality_tabview.tab("App Management").grid_columnconfigure(0, weight=1) # Single column for content

        # --- Install App Section (Top part of the tab) ---
        self.install_frame = ctk.CTkFrame(self.functionality_tabview.tab("App Management"), fg_color="transparent")
        self.install_frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="nsew")
        # Configure grid within install_frame
        self.install_frame.grid_columnconfigure(0, weight=0) # Label
        self.install_frame.grid_columnconfigure(1, weight=1) # Entry/Label for path (takes space)
        self.install_frame.grid_columnconfigure(2, weight=0) # Browse button
        self.install_frame.grid_columnconfigure(3, weight=0) # Install button


        ctk.CTkLabel(self.install_frame, text="Install APK:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")

        # Label to display selected file path
        # Use anchor="w" to align text to the left if the label is wider than the text
        self.apk_path_label = ctk.CTkLabel(self.install_frame, text="No file selected", anchor="w")
        self.apk_path_label.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="ew")

        self.select_apk_button = ctk.CTkButton(self.install_frame, text="Browse...", command=self.select_apk_file)
        self.select_apk_button.grid(row=0, column=2, padx=(0, 10), pady=5, sticky="w")

        # Install button starts disabled, enabled only when a file is selected AND device is connected
        self.install_apk_button = ctk.CTkButton(self.install_frame, text="Install", command=self.install_selected_apk, state="disabled")
        self.install_apk_button.grid(row=0, column=3, padx=(0, 0), pady=5, sticky="w")


        # --- Uninstall App Section ---
        # This section will be placed in row 1 of the App Management tab
        self.uninstall_frame = ctk.CTkFrame(self.functionality_tabview.tab("App Management"), fg_color="transparent")
        self.uninstall_frame.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="nsew")
        # Configure grid within uninstall_frame
        self.uninstall_frame.grid_columnconfigure(0, weight=1) # Give the list area space
        self.uninstall_frame.grid_rowconfigure(0, weight=0) # Controls row
        self.uninstall_frame.grid_rowconfigure(1, weight=0) # Warning row
        self.uninstall_frame.grid_rowconfigure(2, weight=1) # App list row

        # Add this line to make the row containing uninstall_frame expand vertically
        self.functionality_tabview.tab("App Management").grid_rowconfigure(1, weight=1)


        # Uninstall Controls (Filter options, Refresh button, Uninstall button)
        self.uninstall_controls_frame = ctk.CTkFrame(self.uninstall_frame, fg_color="transparent")
        self.uninstall_controls_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        self.uninstall_controls_frame.grid_columnconfigure(0, weight=0) # Label
        self.uninstall_controls_frame.grid_columnconfigure(1, weight=0) # Segmented Button
        self.uninstall_controls_frame.grid_columnconfigure(2, weight=1) # Spacer
        self.uninstall_controls_frame.grid_columnconfigure(3, weight=0) # Refresh Button
        self.uninstall_controls_frame.grid_columnconfigure(4, weight=0) # Details Button
        self.uninstall_controls_frame.grid_columnconfigure(5, weight=0) # Uninstall Button

        ctk.CTkLabel(self.uninstall_controls_frame, text="Show:").grid(row=0, column=0, padx=(0, 10), sticky="w")

        # Segmented button for filtering (User Apps vs All Apps)
        self.app_filter_options = ["User Apps", "All Apps"]
        self.app_filter_button = ctk.CTkSegmentedButton(self.uninstall_controls_frame, values=self.app_filter_options, command=self.on_app_filter_change)
        self.app_filter_button.grid(row=0, column=1, padx=(0, 20), sticky="w")
        self.app_filter_button.set("User Apps") # Default selection

        # Spacer
        self.uninstall_controls_frame.grid_columnconfigure(2, weight=1)

        self.refresh_app_list_button = ctk.CTkButton(self.uninstall_controls_frame, text="Refresh List", command=self.list_apps_in_gui)
        self.refresh_app_list_button.grid(row=0, column=3, padx=(0, 10), sticky="w")

        self.view_details_button = ctk.CTkButton(self.uninstall_controls_frame, text="Details", command=self.view_app_details, state="disabled", width=80)
        self.view_details_button.grid(row=0, column=4, padx=(0, 10), sticky="w")

        self.uninstall_selected_button = ctk.CTkButton(self.uninstall_controls_frame, text="Uninstall Selected", command=self.uninstall_selected_apps, state="disabled", fg_color="darkred", hover_color="red")
        self.uninstall_selected_button.grid(row=0, column=5, padx=(0, 0), sticky="w")


        # Warning Label (initially hidden or showing mild warning)
        self.uninstall_warning_label = ctk.CTkLabel(self.uninstall_frame, text="Caution: Listing USER APPS. Be careful, some user apps may be essential for certain features.", text_color="orange", wraplength=500) # wraplength helps text wrap
        self.uninstall_warning_label.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        # Set initial text for "User Apps" mode (done by setting default above)


        # Frame to contain the scrollable app list (populated dynamically)
        self.app_list_scrollable_frame = ctk.CTkScrollableFrame(self.uninstall_frame)
        self.app_list_scrollable_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        # Configure grid inside the scrollable frame for app entries (Checkbox + Label)
        # These column weights will be set when populating the list


        # --- Populate Logcat Tab ---
        self.logcat_tab.grid_columnconfigure(0, weight=1)
        self.logcat_tab.grid_rowconfigure(0, weight=0) # Controls
        self.logcat_tab.grid_rowconfigure(1, weight=1) # Log area

        # Logcat Controls
        self.logcat_controls_frame = ctk.CTkFrame(self.logcat_tab, fg_color="transparent")
        self.logcat_controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.logcat_start_button = ctk.CTkButton(self.logcat_controls_frame, text="Start Logcat", command=self.start_logcat_gui)
        self.logcat_start_button.pack(side="left", padx=5)

        self.logcat_stop_button = ctk.CTkButton(self.logcat_controls_frame, text="Stop Logcat", command=self.stop_logcat_gui, state="disabled", fg_color="darkred")
        self.logcat_stop_button.pack(side="left", padx=5)

        self.logcat_clear_button = ctk.CTkButton(self.logcat_controls_frame, text="Clear", command=self.clear_logcat_gui, width=80)
        self.logcat_clear_button.pack(side="left", padx=5)
        
        self.logcat_save_button = ctk.CTkButton(self.logcat_controls_frame, text="Save Log", command=self.save_logcat_gui, width=80)
        self.logcat_save_button.pack(side="left", padx=5)

        # Logcat Text Area
        self.logcat_textbox = ctk.CTkTextbox(self.logcat_tab, activate_scrollbars=True)
        self.logcat_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.logcat_textbox.configure(state="disabled") # Read-only initially


        # Bottom Frame (Status Bar)
        # Placed in row 2, spanning both columns. Fixed height.
        self.status_frame = ctk.CTkFrame(self, height=30, fg_color="gray") # Give it a distinct color for visibility
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        # Configure grid within status_frame for the label
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_rowconfigure(0, weight=1)

        # Label to display status messages, anchored to the west (left)
        self.status_label = ctk.CTkLabel(self.status_frame, text="Initializing...", anchor="w") # Initial status text
        self.status_label.grid(row=0, column=0, sticky="nsew", padx=5) # 'nsew' makes label fill the status frame


        # --- Initial Actions ---
        # Automatically list devices on startup if ADB is available
        if self.adb_manager.adb_available:
             # Run list_devices_in_gui in a thread on startup to avoid freezing UI
             threading.Thread(target=self._perform_list_devices_threaded, daemon=True).start()
        else:
             # If adb is not available, update GUI elements and status
             self.device_combobox.set("ADB not found")
             self.device_combobox.configure(state="disabled")
             self.refresh_button.configure(state="disabled")
             self.connect_ip_button.configure(state="disabled")
             # Functionality tabs/buttons should also be disabled
             self.enable_functionality_widgets(False)
             self.update_status("ADB command not found. Please install Android SDK Platform-Tools.", level="error")


    # --- Status Update Method ---
    def update_status(self, message, level="info"):
        """
        Method to update the status bar message safely from any thread.
        Uses self.after() to ensure GUI updates happen on the main thread.
        """
        color = "white" # Default text color
        if level == "error":
            color = "red"
        elif level == "warning":
            color = "yellow" # Or orange

        # Schedule the actual update of the status label on the main thread
        # self.after(delay_ms, callback, *args)
        self.after(0, lambda msg=message, clr=color: self._do_update_status_gui(msg, clr)) # Using lambda here


    def _do_update_status_gui(self, message, color):
        """Helper method to perform the actual status label update on the main thread."""
        self.status_label.configure(text=message, text_color=color)
        # Optional: print to console for easier debugging
        # print(f"GUI Status ({level}): {message}")


    # --- Widget State Control ---
    def enable_functionality_widgets(self, enable):
        """Enables or disables widgets in the functionality tabs based on device connection."""
        state = "normal" if enable else "disabled"

        # Device Control Buttons
        self.reboot_normal_button.configure(state=state)
        self.reboot_recovery_button.configure(state=state)
        self.reboot_bootloader_button.configure(state=state)
        self.power_off_button.configure(state=state)

        # App Management - Install Section
        self.select_apk_button.configure(state=state)
        # Install button is enabled only if a device is selected AND a file is selected
        # So, we only enable it here if enable is True and a file is already selected (self.selected_apk_path is not None)
        apk_file_selected = (self.selected_apk_path is not None and os.path.exists(self.selected_apk_path))
        self.install_apk_button.configure(state="normal" if enable and apk_file_selected else "disabled")

        # App Management - Uninstall Section Controls
        self.app_filter_button.configure(state=state)
        self.refresh_app_list_button.configure(state=state)
        # Uninstall button starts disabled even when enabled, only active when apps are selected
        self.uninstall_selected_button.configure(state="disabled")


    # --- Device Listing Logic ---
    def list_devices_in_gui(self):
        """Calls AdbManager to list devices and updates the GUI dropdown."""
        if not self.adb_manager.adb_available:
            return # Do nothing if adb is not found

        # Update GUI state immediately to show activity
        self.refresh_button.configure(state="disabled")
        self.device_combobox.set("Searching...")
        self.device_combobox.configure(state="disabled")
        # Clear selected device info temporarily while searching
        self.selected_device_label.configure(text="Selected Device: Searching...")
        self.update_device_info(clear_only=True) # Clear info sidebar


        # Run the potentially blocking ADB command in a separate thread
        # daemon=True ensures the thread doesn't prevent the app from closing
        threading.Thread(target=self._perform_list_devices_threaded, daemon=True).start()


    def _perform_list_devices_threaded(self):
         """Performs device listing in a thread and updates GUI via self.after."""
         # Blocking call to AdbManager - returns list of device dicts (serial, state, description)
         devices = self.adb_manager.list_devices()
         # We need to format the values for the combobox using the serial and state
         device_display_values = []
         # Store the device info for later retrieval by serial
         self.available_devices_info = {} # Dict to map serial -> device dict

         for dev in devices:
             serial = dev['serial']
             description = dev.get('description', '') # Get description from adb devices -l
             state = dev.get('state', '')

             # Format the string displayed in the combobox - Show just Serial, add state if not 'device'
             display_str = serial
             if state in ['unauthorized', 'offline']:
                 display_str = f"{serial} [{state.capitalize()}]"
             # For 'device' state, just show the serial

             device_display_values.append(display_str)
             self.available_devices_info[serial] = dev # Store the full device info by serial


         # Use self.after to update GUI elements from the thread safely
         # Schedule the update on the main GUI thread
         self.after(0, self._update_device_list_gui, device_display_values)


    def _update_device_list_gui(self, device_display_values):
         """Updates the GUI device list dropdown from data fetched in a thread."""
         if device_display_values:
             self.device_combobox.configure(values=device_display_values, state="normal")
             # Select the first device and trigger the selection logic
             # Ensure the value we are setting exists in the list of values
             current_value = self.device_combobox.get()
             if current_value not in device_display_values or current_value in ["No devices found", "Searching...", "ADB not found"]:
                  self.device_combobox.set(device_display_values[0])
             # Explicitly call on_device_selected as setting the value doesn't always trigger binding
             # Use self.after(0, ...) to ensure it runs after the combobox values are fully updated
             self.after(0, self.on_device_selected)
         else:
             # No devices found
             self.device_combobox.configure(values=["No devices found"], state="disabled")
             self.device_combobox.set("No devices found")
             self.selected_device_label.configure(text="Selected Device: None")
             self.current_device_serial = None
             self.update_device_info(clear_only=True) # Clear info sidebar
             self.enable_functionality_widgets(False) # Disable controls
             self.available_devices_info = {} # Clear stored device info


         # Re-enable refresh button after command finishes
         self.refresh_button.configure(state="normal")


    # --- Device Connection by IP Logic ---
    def connect_device_by_ip(self):
        """Attempts to connect to a device using the IP address from the entry field."""
        if not self.adb_manager.adb_available:
            return # Do nothing if adb is not found

        ip_address = self.ip_entry.get()
        if not ip_address:
            self.update_status("Please enter an IP address to connect.", level="warning")
            return

        # Update GUI state immediately to show activity
        self.connect_ip_button.configure(state="disabled")
        self.ip_entry.configure(state="disabled")
        self.selected_device_label.configure(text=f"Selected Device: Connecting to {ip_address}...") # Temporary status
        self.update_device_info(clear_only=True) # Clear info sidebar


        # Run the connection attempt in a separate thread
        threading.Thread(target=self._perform_connect_ip_threaded, args=(ip_address,), daemon=True).start()


    def _perform_connect_ip_threaded(self, ip_address):
        """Performs IP connection in a thread and updates GUI via self.after."""
        # Blocking call to AdbManager
        success = self.adb_manager.connect_device(ip_address)
        # Schedule handling the result on the main GUI thread
        self.after(0, lambda s=success, addr=ip_address: self._handle_connect_result_gui(s, attempted_address=addr)) # Using lambda here


    def _handle_connect_result_gui(self, success, attempted_address):
        """Handles the result of a connection attempt and updates GUI."""
        if success:
            # If connect command succeeded, refresh the device list to see the new connection
            # This is important for ADB to fully register the connection.
            # list_devices_in_gui is also threaded internally, so it's safe to call here.
            self.list_devices_in_gui()
            # Status update already handled by AdbManager callback
        else:
             # If connection failed, update status (already done by AdbManager)
             # Clear selected device info as connection failed
             # Use the attempted address in the label
             self.selected_device_label.configure(text=f"Selected Device: Connection to {attempted_address} failed.")
             self.update_device_info(clear_only=True) # Clear info sidebar
             self.enable_functionality_widgets(False) # Disable controls


        # Re-enable GUI elements regardless of success/failure
        self.connect_ip_button.configure(state="normal")
        self.ip_entry.configure(state="normal")


    # --- Device Selection and Info Update Logic ---
    def on_device_selected(self, event=None):
        """Handles when a device is selected from the dropdown."""
        selected_item_text = self.device_combobox.get()
        # Parse the serial number from the displayed text (assuming "Serial (Description)" format or just "Serial")
        # Find the first space or parenthesis to extract the serial
        serial = selected_item_text.split(' ')[0].split('(')[0].strip()


        # Only update if a valid serial is selected (not the placeholder/error text)
        if serial and serial not in ["No", "ADB", "Selected", "Searching..."]: # Simple check against placeholder text parts
             # Also check if this serial is actually in our list of available devices (important after refresh)
             if serial in self.available_devices_info:
                self.current_device_serial = serial
                # Update device info panel - This call will trigger a threaded fetch
                # The selected_device_label will be updated *after* fetch is complete in _do_update_device_info_gui
                self.selected_device_label.configure(text=f"Selected Device: {serial} (Fetching info...)") # Temporary status
                self.update_device_info() # This triggers the fetch
                # Enable functionality widgets now that a device is selected
                self.enable_functionality_widgets(True)
                # Also load the app list when a device is selected
                self.list_apps_in_gui()

             else:
                  # The selected serial is no longer in the available devices list (e.g., unplugged)
                  # This case should ideally be handled by list_devices_in_gui refreshing automatically
                  # after a disconnection, but adding a fallback refresh here just in case.
                  self.update_status(f"Selected device {serial} is no longer available. Refreshing list.", level="warning")
                  self.list_devices_in_gui() # Refresh the list to update the dropdown
        else:
             # No valid device selected (placeholder text)
             self.current_device_serial = None
             self.selected_device_label.configure(text="Selected Device: None")
             self.update_device_info(clear_only=True) # Clear info display
             self.enable_functionality_widgets(False) # Disable controls


    def update_device_info(self, clear_only=False):
        """
        Updates the device information labels based on the current_device_serial.
        Args: clear_only: If True, only clears the labels.
        """
        # Clear previous info display immediately
        self.serial_display_label.configure(text="Serial: N/A")
        self.model_label.configure(text="Model: N/A")
        self.commercial_name_label.configure(text="Commercial Name: N/A") # Clear commercial name
        self.android_version_label.configure(text="Android Version: N/A")
        self.battery_level_label.configure(text="Battery Level: N/A") # Clear battery level


        if not clear_only and self.current_device_serial and self.adb_manager.adb_available:
             # Update the serial display label immediately as we know the serial
             # The main selected_device_label is updated temporarily in on_device_selected
             self.serial_display_label.configure(text=f"Serial: {self.current_device_serial}")

             # Run fetching device info in a separate thread to keep GUI responsive
             threading.Thread(target=self._fetch_and_update_device_info_threaded, args=(self.current_device_serial,), daemon=True).start()
        # else: clear_only was True, or current_device_serial is None, labels are already N/A


    def _fetch_and_update_device_info_threaded(self, serial):
         """Fetches device info in a thread and updates GUI via self.after."""
         # Call the AdbManager method to get the info (blocking call)
         # This will return the info dictionary including display_name and battery_level
         info = self.adb_manager.get_device_info(serial)

         # Schedule safely updating GUI elements from the thread
         self.after(0, lambda info_data=info: self._do_update_device_info_gui(info_data)) # Using lambda here


    def _do_update_device_info_gui(self, info):
         """Updates the GUI Device Info labels and Selected Device label with data fetched in a thread."""
         # This method runs on the main GUI thread (via self.after).

         # Extract info, providing defaults if info is None or key is missing
         serial = info.get('serial', 'N/A') if info else 'N/A'
         model = info.get('model', 'N/A') if info else 'N/A'
         version = info.get('version', 'N/A') if info else 'N/A'
         # Get the display_name and battery_level fetched by AdbManager
         display_name = info.get('display_name', 'N/A') if info else 'N/A'
         battery_level = info.get('battery_level', 'N/A') if info else 'N/A'


         # --- Update Device Info sidebar labels ---
         self.serial_display_label.configure(text=f"Serial: {serial}")
         self.model_label.configure(text=f"Model: {model}")
         self.commercial_name_label.configure(text=f"Commercial Name: {display_name}") # Update commercial name label
         self.android_version_label.configure(text=f"Android Version: {version}")
         self.battery_level_label.configure(text=f"Battery Level: {battery_level}") # Update battery level label


         # --- Update the 'Selected Device' label in the connection area ---
         # Prioritize display: display_name > model > serial

         text_to_display = "Selected Device: None" # Default text if no valid info found

         # Use the determined display_name for the main label
         if display_name and display_name not in ['N/A', 'Error']:
             # Include model and serial in parentheses if display_name is available
             # Format: "Selected Device: Commercial Name (Model) (Serial)"
             text_to_display = f"Selected Device: {display_name} ({model}) ({serial})"
         elif model and model not in ['N/A', 'Error']:
             # Fallback to Model (Serial) if no valid display_name
             text_to_display = f"Selected Device: {model} ({serial})"
         elif serial and serial not in ['N/A', 'Error']:
             # Fallback to just serial if neither display_name nor model is valid
             text_to_display = f"Selected Device: {serial}"
         # Else: keep default "Selected Device: None"


         # Effective update of the label
         self.selected_device_label.configure(text=text_to_display)


    # --- Device Control Methods ---

    def reboot_normal(self):
        """Initiates a normal device reboot in a separate thread."""
        if self.current_device_serial and self.adb_manager.adb_available:
            # Disable buttons temporarily to prevent multiple clicks
            self.enable_functionality_widgets(False)
            self.update_status("Initiating normal reboot...", level="info")
            # Run the reboot command in a separate thread
            threading.Thread(target=self._perform_reboot_threaded, args=(self.current_device_serial, ""), daemon=True).start()
        else:
             self.update_status("No device selected or ADB not available.", level="warning")

    def reboot_recovery(self):
        """Initiates a reboot to recovery in a separate thread."""
        if self.current_device_serial and self.adb_manager.adb_available:
            self.enable_functionality_widgets(False)
            self.update_status("Initiating reboot to recovery...", level="info")
            threading.Thread(target=self._perform_reboot_threaded, args=(self.current_device_serial, "recovery"), daemon=True).start()
        else:
             self.update_status("No device selected or ADB not available.", level="warning")

    def reboot_bootloader(self):
        """Initiates a reboot to bootloader in a separate thread."""
        if self.current_device_serial and self.adb_manager.adb_available:
            self.enable_functionality_widgets(False)
            self.update_status("Initiating reboot to bootloader...", level="info")
            threading.Thread(target=self._perform_reboot_threaded, args=(self.current_device_serial, "bootloader"), daemon=True).start()
        else:
             self.update_status("No device selected or ADB not available.", level="warning")

    def _perform_reboot_threaded(self, serial, mode):
        """Performs the reboot command in a thread and handles potential disconnection."""
        # Blocking call to AdbManager
        success = self.adb_manager.reboot_device(serial, mode)

        # If command sent successfully, the device is likely disconnecting.
        # Schedule a refresh of the device list after a short delay.
        if success:
            # Use self.after to schedule list_devices_in_gui (which is itself threaded)
            self.after(5000, self.list_devices_in_gui) # Refresh after 5 seconds
        else:
             # If the command failed to send, re-enable widgets immediately
             self.after(0, lambda: self.enable_functionality_widgets(True)) # Re-enable via lambda


        # AdbManager callback handles status updates (success or failure)


    def power_off(self):
        """Initiates device power off in a separate thread."""
        if self.current_device_serial and self.adb_manager.adb_available:
             self.enable_functionality_widgets(False)
             self.update_status("Initiating power off...", level="info")
             # Run the power off command in a separate thread
             threading.Thread(target=self._perform_power_off_threaded, args=(self.current_device_serial,), daemon=True).start()
        else:
             self.update_status("No device selected or ADB not available.", level="warning")

    def _perform_power_off_threaded(self, serial):
        """Performs the power off command in a thread and handles potential disconnection."""
        # Blocking call to AdbManager
        success = self.adb_manager.power_off_device(serial)

        # Device will disconnect immediately after power off.
        # Schedule a refresh of the device list shortly after.
        if success:
             self.after(2000, self.list_devices_in_gui) # Refresh after 2 seconds
        else:
            # If the command failed to send, re-enable widgets immediately
             self.after(0, lambda: self.enable_functionality_widgets(True)) # Re-enable via lambda

        # AdbManager callback handles status updates (success or failure)


    # --- App Management - Install Methods ---

    def select_apk_file(self):
        """Opens a file dialog to select an APK file and updates the path label."""
        # Use tkinter's filedialog to open the file picker
        apk_path = filedialog.askopenfilename(
            title="Select APK File",
            filetypes=(("APK files", "*.apk"), ("All files", "*.*"))
        )
        if apk_path:
            # Store the selected path in an instance variable
            self.selected_apk_path = apk_path
            # Update the label text to show just the filename for brevity
            self.apk_path_label.configure(text=os.path.basename(apk_path))
            # Enable the install button if a device is also selected and adb is available
            if self.current_device_serial and self.adb_manager.adb_available:
                self.install_apk_button.configure(state="normal")
        else:
            # If dialog is cancelled or no file selected, clear the path and disable install button
            self.selected_apk_path = None
            self.apk_path_label.configure(text="No file selected")
            self.install_apk_button.configure(state="disabled")


    def install_selected_apk(self):
        """Calls AdbManager to install the selected APK in a separate thread."""
        if not self.current_device_serial or not self.adb_manager.adb_available:
             self.update_status("No device selected or ADB not available.", level="warning")
             return

        # Check if an APK file path is stored and the file exists
        if not self.selected_apk_path or not os.path.exists(self.selected_apk_path):
             self.update_status("No valid APK file selected or file not found.", level="warning")
             # Clear the invalid path display
             self.selected_apk_path = None
             self.apk_path_label.configure(text="No file selected")
             self.install_apk_button.configure(state="disabled")
             return

        # Disable the install button while installation is in progress
        self.install_apk_button.configure(state="disabled")
        self.select_apk_button.configure(state="disabled") # Also disable browse during install
        # Note: Other functionality widgets are already enabled if we reach here.


        # Run the installation command in a separate thread
        # Using daemon=True allows the thread to close automatically when the main app exits
        self.update_status(f"Starting installation of {os.path.basename(self.selected_apk_path)}...", level="info")
        threading.Thread(target=self._perform_install_apk_threaded, args=(self.current_device_serial, self.selected_apk_path), daemon=True).start()


    def _perform_install_apk_threaded(self, serial, apk_path):
        """Performs the APK installation command in a thread."""
        # Blocking call to AdbManager
        success = self.adb_manager.install_apk(serial, apk_path)

        # Schedule re-enabling buttons on the main GUI thread
        # The AdbManager callback already updates the status bar with the final outcome.
        self.after(0, lambda: self._enable_install_buttons_gui()) # Schedule via lambda


    def _enable_install_buttons_gui(self):
        """Re-enables install buttons on the main GUI thread after installation attempt."""
        # Always re-enable the browse button
        self.select_apk_button.configure(state="normal")

        # Re-enable the install button only if a device is still selected AND an APK file is still selected
        # and the file still exists.
        if self.current_device_serial and self.selected_apk_path and self.adb_manager.adb_available:
             if os.path.exists(self.selected_apk_path):
                self.install_apk_button.configure(state="normal")
             else:
                 # If the file disappeared, update the GUI to reflect this
                 self.selected_apk_path = None
                 self.apk_path_label.configure(text="File not found")
                 self.update_status("Selected APK file not found during re-enable check.", level="error")
                 self.install_apk_button.configure(state="disabled") # Explicitly disable if file gone
        else:
             # If device/adb is gone or no file selected, ensure install button is disabled
             self.install_apk_button.configure(state="disabled")


    # --- App Management - Uninstall Methods ---

    def on_app_filter_change(self, selected_filter):
        """Handles change in the app filter (User Apps vs All Apps)."""
        # Update warning label based on selection
        if selected_filter == "All Apps":
            self.uninstall_warning_label.configure(
                text="Warning: Listing SYSTEM APPS. Uninstalling critical system apps can DAMAGE or BRICK your device!",
                text_color="red"
            )
        else: # "User Apps"
             self.uninstall_warning_label.configure(
                 text="Caution: Listing USER APPS. Be careful, some user apps may be essential for certain features.",
                 text_color="orange"
             )

        # Trigger listing apps with the new filter setting
        # This should happen when the filter changes, if a device is selected
        if self.current_device_serial and self.adb_manager.adb_available:
             self.list_apps_in_gui() # Call this method to refresh the list with the new filter

    def list_apps_in_gui(self):
        """Calls AdbManager to list packages and updates the GUI list."""
        if not self.current_device_serial or not self.adb_manager.adb_available:
             self.update_status("No device selected or ADB not available to list apps.", level="warning")
             return

        # Determine filter based on segmented button selection
        user_only = (self.app_filter_button.get() == "User Apps")

        self.update_status(f"Listing {'user' if user_only else 'all'} apps...", level="info")

        # Disable refresh/uninstall buttons while listing
        self.refresh_app_list_button.configure(state="disabled")
        self.uninstall_selected_button.configure(state="disabled")

        # Clear the existing app list display widgets
        for widget in self.app_list_scrollable_frame.winfo_children():
            widget.destroy()
        self.app_checkboxes = {} # Clear the dictionary of checkbox references
        self.current_app_packages = [] # Clear the list of current packages


        # Use a thread to call AdbManager.list_packages (blocking call)
        threading.Thread(target=self._perform_list_apps_threaded, args=(self.current_device_serial, user_only), daemon=True).start()


    def _perform_list_apps_threaded(self, serial, user_only):
        """Performs the app listing command in a thread and updates GUI via self.after."""
        # Blocking call to AdbManager
        packages = self.adb_manager.list_packages(serial, user_only)

        # Schedule updating the GUI list on the main GUI thread
        self.after(0, lambda pkg_list=packages: self._update_app_list_gui(pkg_list)) # Using lambda here


    def _update_app_list_gui(self, packages):
        """Populates the scrollable frame with the list of packages and checkboxes."""
        self.current_app_packages = packages # Store the list of packages currently displayed
        self.app_checkboxes = {} # Prepare to store checkbox references

        # Clear previous grid configuration inside the scrollable frame
        # Need to ensure all previous rows are cleared before re-gridding
        # This is done by destroying widgets above, but explicit row configure reset is good practice
        # for i in range(self.app_list_scrollable_frame.grid_size()[1]): # Can get max row index
        #      self.app_list_scrollable_frame.grid_rowconfigure(i, weight=0)


        if not packages:
            ctk.CTkLabel(self.app_list_scrollable_frame, text="No applications found matching the filter.").grid(row=0, column=0, padx=10, pady=10, sticky="w", columnspan=2) # Span two columns if no apps
            # Ensure column weights are set for the "No apps found" label
            self.app_list_scrollable_frame.grid_columnconfigure(0, weight=1)
            self.app_list_scrollable_frame.grid_columnconfigure(1, weight=0) # Ensure column 1 doesn't take space


        else:
            # Configure the grid inside the scrollable frame for app entries (Checkbox + Label)
            self.app_list_scrollable_frame.grid_columnconfigure(0, weight=0) # Checkbox column (fixed width)
            self.app_list_scrollable_frame.grid_columnconfigure(1, weight=1) # Label column (takes space)

            # Sort packages alphabetically for easier navigation
            packages.sort()

            for i, package_name in enumerate(packages):
                # Create a checkbox for the app
                checkbox = ctk.CTkCheckBox(self.app_list_scrollable_frame, text=package_name, command=self._on_app_checkbox_changed)
                checkbox.grid(row=i, column=0, padx=(10, 5), pady=2, sticky="w") # Align checkbox to the left

                # Store checkbox reference
                self.app_checkboxes[package_name] = checkbox

                # Optional: Add a label next to the checkbox if desired (e.g., for friendly name if implemented)
                # label = ctk.CTkLabel(self.app_list_scrollable_frame, text=package_name, anchor="w")
                # label.grid(row=i, column=1, padx=(0, 10), pady=2, sticky="ew")

            # Ensure the last row has weight 1 to push content up, if needed (often handled by scrollable frame itself)
            # self.app_list_scrollable_frame.grid_rowconfigure(len(packages), weight=1)


        # Re-enable refresh button
        self.refresh_app_list_button.configure(state="normal")

        # Re-evaluate uninstall button state based on selections (currently none after refresh)
        self._on_app_checkbox_changed() # Call this to update uninstall button state


    def _on_app_checkbox_changed(self):
        """Checks if any app checkbox is selected and updates the Uninstall and Details button states."""
        selected_count = sum(1 for checkbox in self.app_checkboxes.values() if checkbox.get() == 1)
        
        self.uninstall_selected_button.configure(state="normal" if selected_count > 0 else "disabled")
        # Enable Details button only if exactly one app is selected
        self.view_details_button.configure(state="normal" if selected_count == 1 else "disabled")


    def uninstall_selected_apps(self):
        """Handles confirmation and uninstallation/disabling of selected apps."""
        # Get list of selected package names
        selected_packages = [
            package_name for package_name, checkbox in self.app_checkboxes.items()
            if checkbox.get() == 1
        ]

        if not selected_packages:
            self.update_status("No applications selected for uninstall.", level="warning")
            return

        # Store the selected packages temporarily for the confirmation dialog callbacks
        self._packages_to_uninstall_in_dialog = selected_packages

        # Show the custom confirmation dialog
        self.show_uninstall_confirmation(selected_packages)


    def show_uninstall_confirmation(self, selected_packages):
        """Shows the custom CTkTopLevel confirmation dialog before uninstalling."""
        if self.confirmation_dialog is not None and self.confirmation_dialog.winfo_exists():
            # Dialog is already open, bring it to front if needed or do nothing
            self.confirmation_dialog.lift()
            return

        # Create the custom top-level dialog window
        self.confirmation_dialog = ctk.CTkToplevel(self)
        self.confirmation_dialog.title("Confirm Uninstallation")
        self.confirmation_dialog.geometry("400x400") # Adjust size as needed
        self.confirmation_dialog.transient(self) # Keep dialog on top of main window
        self.confirmation_dialog.grab_set() # Modal: disable interaction with main window

        # Configure grid for the dialog window
        self.confirmation_dialog.grid_columnconfigure(0, weight=1)
        self.confirmation_dialog.grid_rowconfigure(0, weight=0) # Warning row
        self.confirmation_dialog.grid_rowconfigure(1, weight=0) # Info text row
        self.confirmation_dialog.grid_rowconfigure(2, weight=1) # App list area (takes space)
        self.confirmation_dialog.grid_rowconfigure(3, weight=0) # Buttons row

        # Determine the warning message based on whether system apps are potentially included
        current_filter = self.app_filter_button.get()
        is_all_apps_filter = (current_filter == "All Apps")

        warning_text = ""
        warning_color = "orange" # Default for user apps
        if is_all_apps_filter:
             warning_text = "WARNING: You are attempting to uninstall SYSTEM apps. This can seriously DAMAGE or BRICK your device!"
             warning_color = "red"

        # Add warning label to dialog
        ctk.CTkLabel(self.confirmation_dialog, text=warning_text, text_color=warning_color, font=ctk.CTkFont(weight="bold"), wraplength=350).grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew")

        # Add informative text
        ctk.CTkLabel(self.confirmation_dialog, text="Are you sure you want to uninstall or disable the following applications?", wraplength=350).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")


        # Add a Textbox or Scrollable Frame to list the selected packages
        # Using a Textbox is simpler for just displaying text
        package_list_text = "\n".join(selected_packages)
        package_list_textbox = ctk.CTkTextbox(self.confirmation_dialog, wrap="word", activate_scrollbars=True)
        package_list_textbox.insert("0.0", package_list_text) # Insert text at the beginning
        package_list_textbox.configure(state="disabled") # Make it read-only
        package_list_textbox.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew") # Takes remaining space


        # Add buttons frame to dialog
        button_frame = ctk.CTkFrame(self.confirmation_dialog, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1) # Spacer
        button_frame.grid_columnconfigure(1, weight=0) # Cancel button
        button_frame.grid_columnconfigure(2, weight=0) # Confirm button

        # Add Cancel and Confirm buttons to the button frame
        ctk.CTkButton(button_frame, text="Cancel", command=self._cancel_uninstall).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(button_frame, text="Confirm Uninstall", command=self._confirm_uninstall, fg_color="darkred", hover_color="red").grid(row=0, column=2)


    def _confirm_uninstall(self):
        """Callback for the Confirm button in the custom dialog."""
        if self.confirmation_dialog is not None:
            self.confirmation_dialog.destroy() # Close the dialog window
            self.confirmation_dialog = None # Clear the reference

        # Trigger the actual uninstall process in a separate thread
        # Use the stored list of packages
        if self.current_device_serial and self.adb_manager.adb_available and self._packages_to_uninstall_in_dialog:
             self.update_status(f"Confirmation received. Starting uninstall process for {len(self._packages_to_uninstall_in_dialog)} app(s)...", level="info")
             threading.Thread(target=self._perform_uninstall_threaded, args=(self.current_device_serial, self._packages_to_uninstall_in_dialog), daemon=True).start()
        else:
             self.update_status("Device disconnected, ADB not available, or no packages to uninstall. Cannot perform uninstall.", level="error")
             self._packages_to_uninstall_in_dialog = [] # Clear the stored list


    def _cancel_uninstall(self):
        """Callback for the Cancel button in the custom dialog."""
        if self.confirmation_dialog is not None:
            self.confirmation_dialog.destroy() # Close the dialog window
            self.confirmation_dialog = None # Clear the reference

        self.update_status("Uninstallation cancelled by user.", level="info")
        self._packages_to_uninstall_in_dialog = [] # Clear the stored list


    def _perform_uninstall_threaded(self, serial, packages_to_uninstall):
        """Performs the uninstall/disable command(s) for selected packages in a thread."""
        # Disable GUI controls during the uninstall process using self.after() via lambda
        self.after(0, lambda: self.enable_functionality_widgets(False)) # Disable main controls
        self.after(0, lambda: self.refresh_app_list_button.configure(state="disabled")) # Specifically disable refresh list btn
        self.after(0, lambda: self.uninstall_selected_button.configure(state="disabled")) # Specifically disable uninstall btn


        results = {} # To store results for each package {package_name: "success" | "disabled" | "failed"}
        total_packages = len(packages_to_uninstall)

        for i, package_name in enumerate(packages_to_uninstall):
            # Update status bar with progress for the specific package using lambda
            self.after(0, lambda msg=f"[{i+1}/{total_packages}] Processing {package_name}...", lvl="info": self.update_status(msg, level=lvl))

            # Try uninstalling first
            uninstall_success = self.adb_manager.uninstall_package(serial, package_name)

            if uninstall_success:
                results[package_name] = "success"
                self.after(0, lambda pkg=package_name, res="success": self._handle_uninstall_result_gui(pkg, res))
            else:
                # Uninstall failed, attempt to disable
                self.after(0, lambda msg=f"[{i+1}/{total_packages}] Uninstall failed for {package_name}. Attempting to disable...", lvl="warning": self.update_status(msg, level=lvl))
                disable_success = self.adb_manager.disable_package(serial, package_name)

                if disable_success:
                    results[package_name] = "disabled"
                    self.after(0, lambda pkg=package_name, res="disabled": self._handle_uninstall_result_gui(pkg, res))
                else:
                    results[package_name] = "failed" # Failed both uninstall and disable
                    self.after(0, lambda pkg=package_name, res="failed": self._handle_uninstall_result_gui(pkg, res))

        # All packages processed
        self.after(0, lambda: self.update_status("Uninstallation process complete.", level="info"))
        # Re-enable GUI controls and refresh the app list using lambda
        self.after(0, lambda: self.enable_functionality_widgets(True)) # Re-enable main controls
        self.after(0, self.list_apps_in_gui) # Refresh the app list to reflect changes


    def _handle_uninstall_result_gui(self, package_name, result_status):
        """Handles the result of a single uninstall/disable attempt and updates the GUI list display."""
        # This method runs on the main GUI thread (via self.after).

        # Find the checkbox widget for the processed package
        if package_name in self.app_checkboxes:
            checkbox = self.app_checkboxes[package_name]

            # Update the checkbox text/color to indicate the result
            if result_status == "success":
                checkbox.configure(text=f"{package_name} (Uninstalled)", text_color="green", state="disabled")
            elif result_status == "disabled":
                checkbox.configure(text=f"{package_name} (Disabled)", text_color="orange", state="disabled")
            elif result_status == "failed":
                 checkbox.configure(text=f"{package_name} (Failed)", text_color="red", state="disabled")

            # Uncheck the box after processing (it's also disabled, but good practice)
            checkbox.select(0)

        # The final list_apps_in_gui call will refresh the entire list, removing
        # uninstalled apps and showing disabled ones (if the filter allows).
        # The visual status update above provides immediate feedback during the process.

        # Re-evaluate the uninstall button state after each attempt (in case the last selected was removed)
        # This happens via the final enable_functionality_widgets and list_apps_in_gui calls.
        pass # No need to call _on_app_checkbox_changed here per item anymore


    # --- App Details Method ---
    def view_app_details(self):
        """Fetches and displays details for the single selected app."""
        # Identify the selected package
        selected_package = None
        for pkg, checkbox in self.app_checkboxes.items():
            if checkbox.get() == 1:
                selected_package = pkg
                break
        
        if not selected_package: return

        if not self.current_device_serial or not self.adb_manager.adb_available:
            self.update_status("Device not connected.", level="error")
            return

        self.update_status(f"Fetching details for {selected_package}...", level="info")
        
        # Run in thread
        threading.Thread(target=self._perform_get_details_threaded, args=(self.current_device_serial, selected_package), daemon=True).start()

    def _perform_get_details_threaded(self, serial, package_name):
        details = self.adb_manager.get_package_details(serial, package_name)
        self.after(0, lambda d=details: self._show_details_popup(d))

    def _show_details_popup(self, details):
        if not details:
            self.update_status("Failed to fetch app details.", level="error")
            return

        # Create popup
        popup = ctk.CTkToplevel(self)
        popup.title(f"Details: {details['package_name']}")
        popup.geometry("500x400")
        popup.transient(self)
        
        # Grid layout
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=3)

        row = 0
        for key, label_text in [
            ('package_name', 'Package:'),
            ('version_name', 'Version Name:'),
            ('version_code', 'Version Code:'),
            ('installer', 'Installer:'),
            ('first_install_time', 'First Install:'),
            ('last_update_time', 'Last Update:'),
            ('uid', 'UID:'),
        ]:
            ctk.CTkLabel(popup, text=label_text, font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=5, sticky="e")
            ctk.CTkLabel(popup, text=details.get(key, 'N/A'), anchor="w").grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            row += 1

        # Permissions list
        ctk.CTkLabel(popup, text="Permissions:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=5, sticky="ne")
        
        perms_textbox = ctk.CTkTextbox(popup, height=150)
        perms_textbox.grid(row=row, column=1, padx=10, pady=5, sticky="nsew")
        popup.grid_rowconfigure(row, weight=1)
        
        perms_text = "\n".join(details.get('permissions', []))
        perms_textbox.insert("0.0", perms_text)
        perms_textbox.configure(state="disabled")

        self.update_status(f"Details shown for {details['package_name']}.", level="info")


    # --- Logcat Methods ---
    def start_logcat_gui(self):
        if not self.current_device_serial:
            self.update_status("No device selected.", level="error")
            return
        
        self.logcat_textbox.configure(state="normal") # clear logic needs this
        # self.logcat_textbox.delete("0.0", "end") # Optional: auto-clear on start
        self.logcat_textbox.configure(state="disabled")

        self.logcat_start_button.configure(state="disabled")
        self.logcat_stop_button.configure(state="normal")
        
        self.adb_manager.start_logcat(self.current_device_serial, self.update_logcat_gui)

    def stop_logcat_gui(self):
        self.adb_manager.stop_logcat()
        self.logcat_start_button.configure(state="normal")
        self.logcat_stop_button.configure(state="disabled")

    def update_logcat_gui(self, line):
        # This is called from a thread, so use after
        self.after(0, lambda l=line: self._append_logcat_line(l))

    def _append_logcat_line(self, line):
        self.logcat_textbox.configure(state="normal")
        self.logcat_textbox.insert("end", line)
        self.logcat_textbox.see("end") # Auto-scroll
        self.logcat_textbox.configure(state="disabled")

    def clear_logcat_gui(self):
        self.logcat_textbox.configure(state="normal")
        self.logcat_textbox.delete("0.0", "end")
        self.logcat_textbox.configure(state="disabled")

    def save_logcat_gui(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                content = self.logcat_textbox.get("0.0", "end")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.update_status(f"Logcat saved to {os.path.basename(file_path)}", level="info")
            except Exception as e:
                self.update_status(f"Error saving logcat: {e}", level="error")


# --- Run the application ---
if __name__ == "__main__":
    # Check if the script is being run directly
    app = AdbGripperApp() # Create the application instance
    app.mainloop() # Start the CustomTkinter event loop