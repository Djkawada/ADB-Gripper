import subprocess
import sys
import os
import threading # Included for potential future use with long-running tasks

class AdbManager:
    def __init__(self, status_callback=None):
        """
        Initializes the AdbManager.

        Args:
            status_callback: A function in the GUI to call with status updates (message, level).
                             Expected signature: status_callback(message, level="info")
        """
        self.status_callback = status_callback

        # Check if 'adb' command is available in PATH on initialization
        self._update_status("Checking for ADB command...", level="info")
        if not self._is_adb_available():
             self._update_status(
                 "Error: 'adb' command not found. Please ensure Android SDK Platform-Tools are installed "
                 "and 'adb' is in your system's PATH.", level="error")
             # Set a flag to indicate adb is not available
             self.adb_available = False
        else:
             self.adb_available = True
             self._update_status("'adb' command found.", level="info")

        self.logcat_process = None
        self.logcat_thread = None
        self._stop_logcat_event = threading.Event()


    def _is_adb_available(self):
        """Checks if the adb command is available in the system's PATH."""
        try:
            # Run a simple adb command like 'version' that doesn't require a device
            # Use short timeout as we only need to know if the command runs
            subprocess.run(['adb', 'version'], check=True, capture_output=True, text=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Command not found, or timed out trying to find/run it
            return False
        except Exception as e:
             # Catch any other unexpected errors
             print(f"An unexpected error occurred while checking for adb: {e}") # Print to console for debugging check
             return False


    def _run_adb_command(self, command, timeout=15):
        """
        Internal helper to run an ADB command using subprocess.

        Args:
            command: A list of strings representing the command and its arguments
                     (e.g., ['adb', 'devices', '-l']).
            timeout: Timeout in seconds for the command.

        Returns:
            A tuple (stdout, stderr, returncode) or (None, error_message, 1) if an exception occurs.
        """
        # If adb wasn't found during initialization, don't even try to run commands
        if not self.adb_available:
            self._update_status("ADB is not available. Cannot run command.", level="error")
            return None, "ADB not available", 1

        # Basic validation: ensure command starts with 'adb'
        if not command or command[0].lower() != 'adb':
             self._update_status(f"Internal Error: Command does not start with 'adb': {command}", level="error")
             return None, "Invalid command format", 1

        try:
            # Use creationflags=subprocess.CREATE_NO_WINDOW on Windows to prevent console window popup
            is_windows = sys.platform.startswith('win')
            creationflags = subprocess.CREATE_NO_WINDOW if is_windows else 0

            # print(f"Running command: {' '.join(command)}") # Optional: for debugging print
            result = subprocess.run(
                command,
                capture_output=True,
                text=True, # Use text mode (decodes bytes to strings)
                timeout=timeout,
                check=False,       # Do NOT raise CalledProcessError for non-zero exit codes
                creationflags=creationflags
            )
            # print(f"Command finished. Return code: {result.returncode}") # Optional: for debugging print
            # print(f"STDOUT: {result.stdout.strip()}") # Optional: for debugging print
            # print(f"STDERR: {result.stderr.strip()}") # Optional: for debugging print


            # Check stderr even if returncode is 0, as ADB sometimes prints warnings/errors there
            if result.returncode != 0:
                 error_message = result.stderr.strip() if result.stderr.strip() else f"ADB command failed with return code {result.returncode}."
                 self._update_status(f"ADB Command Error: {error_message}", level="error")
                 return result.stdout, result.stderr, result.returncode
            elif result.stderr.strip():
                 # Command succeeded but had stderr output (warnings?)
                 self._update_status(f"ADB Command Warning: {result.stderr.strip()}", level="warning")


            return result.stdout, result.stderr, result.returncode

        except FileNotFoundError:
            # This case should ideally be caught by _is_adb_available, but included for safety
            self._update_status("Error: ADB command not found during execution. Check PATH.", level="error")
            return None, "ADB command not found", 1
        except subprocess.TimeoutExpired:
             self._update_status(f"Error: ADB command timed out after {timeout} seconds.", level="error")
             return None, "Command timed out", 1
        except Exception as e:
            self._update_status(f"An unexpected error occurred while running ADB command: {e}", level="error")
            return None, str(e), 1


    def _update_status(self, message, level="info"):
        """Helper to call the GUI status callback if it exists."""
        if self.status_callback:
            # In a real application, if calling from a thread that is NOT the main GUI thread,
            # you MUST use self.status_callback.after() to update GUI safely.
            # Our threaded calls in main_app use .after() on the GUI side, so direct call here is okay
            # as the main_app handles the thread safety when it receives the callback.
            try:
                self.status_callback(message, level)
            except Exception as e:
                 print(f"Error calling status callback: {e}") # Print if callback itself fails
        else:
            # Fallback to printing if no callback is provided (e.g., for testing AdbManager directly)
            print(f"Status ({level}): {message}")

    def list_devices(self):
        """
        Lists connected ADB devices.
        Includes description from 'adb devices -l'.

        Returns:
            A list of device dictionaries, e.g.,
            [{'serial': 'emulator-5554', 'state': 'device', 'description': 'product:sdk_gphone_x86 model:sdk_gphone_x86 device:generic'},
             {'serial': '192.168.1.5:5555', 'state': 'device', 'description': ''}]
            Returns an empty list if no devices, ADB not available, or an error occurs.
        """
        if not self.adb_available:
            return []

        self._update_status("Searching for devices...", level="info")
        # Using a longer timeout for listing devices sometimes helps
        # 'adb devices -l' includes product/model/device info in the description
        stdout, stderr, returncode = self._run_adb_command(['adb', 'devices', '-l'], timeout=20)

        devices = []
        if returncode == 0 and stdout:
            lines = stdout.strip().split('\n')
            # The first line is usually "List of devices attached" - skip it if present
            if lines and "List of devices attached" in lines[0]:
                 lines = lines[1:]

            for line in lines:
                 line = line.strip()
                 if not line: # Skip empty lines
                      continue
                 # Split into serial, state, and optional description (description might contain spaces)
                 parts = line.split(maxsplit=2)
                 if len(parts) >= 2:
                     serial = parts[0]
                     state = parts[1]
                     description = parts[2] if len(parts) > 2 else ""

                     # Include 'device', 'unauthorized', and 'offline' states.
                     # GUI can filter or display state appropriately.
                     # An offline device might become online, Unauthorized needs user action.
                     devices.append({
                         'serial': serial,
                         'state': state,
                         'description': description # Includes model/product info from -l
                     })
                 else:
                      # Handle unexpected line formats (e.g., just serial or state missing)
                      self._update_status(f"Warning: Could not fully parse device line: '{line}'", level="warning")

            if devices:
                 # Status already updated by _run_adb_command for success/warning
                 pass
            elif returncode == 0 and not stdout.strip():
                self._update_status("No devices found.", level="info") # Handles case where stdout is empty but returncode is 0
            # else: _run_adb_command handled error status

        return devices

    def connect_device(self, address):
        """
        Connects to a device via TCP/IP address.

        Args:
            address: The IP address and optional port (e.g., "192.168.1.10:5555").

        Returns:
            True if the connect command likely succeeded (return code 0 and expected output), False otherwise.
        """
        if not self.adb_available:
            return False

        if not address:
            self._update_status("Error: IP address is empty for connection.", level="error")
            return False

        self._update_status(f"Attempting to connect to {address}...", level="info")
        command = ['adb', 'connect', address]
        stdout, stderr, returncode = self._run_adb_command(command, timeout=15)

        if returncode == 0:
            # ADB connect command successful, check stdout for confirmation messages
            stdout_lower = stdout.lower()
            if "connected to" in stdout_lower or "already connected" in stdout_lower:
                 # AdbManager status updated by _run_adb_command on success
                 return True
            elif " connection refused" in stdout_lower:
                 self._update_status(f"Connection failed for {address}: Connection refused. Is ADB over TCP enabled on the device?", level="error")
                 return False
            elif " unable to connect" in stdout_lower or "failed to connect" in stdout_lower:
                 # AdbManager status updated by _run_adb_command on error (via stderr check)
                 # Fallback check on stdout just in case stderr is empty
                 self._update_status(f"Connection failed for {address}: {stdout.strip()}", level="error")
                 return False
            else:
                 # Unexpected successful output, but treat as success based on return code 0
                 self._update_status(f"Connect command successful for {address}, but output was unexpected: {stdout.strip()}", level="warning")
                 return True
        else:
             # Non-zero return code errors (already reported by _run_adb_command)
             return False

    def get_device_info(self, serial):
        """
        Gets basic information for a specific device by running separate getprop/dumpsys commands.
        Attempts to find a user-friendly display name and battery level.

        Args:
            serial: The serial number or IP:port of the target device.

        Returns:
            A dictionary containing device info including 'serial', 'model',
            'version', 'display_name' (best available name), 'battery_level',
            or None if a significant error occurred during essential fetch.
        """
        if not self.adb_available: return None
        if not serial:
             self._update_status("Error: No device selected to get info.", level="error")
             return None

        self._update_status(f"Fetching info for device {serial}...", level="info")

        # Initialize info dictionary with defaults
        info = {
            'serial': serial,
            'model': 'N/A',
            'version': 'N/A',
            'display_name': 'N/A', # The name we'll try to use for display
            'battery_level': 'N/A' # Battery percentage
        }

        # List of properties to try fetching for a display name, in order of preference
        # Based on common properties and user's getprop output analysis.
        prop_names_to_try = [
            'ro.product.marketname',      # Found in user's output - High priority!
            'ro.product.vendor.marketname', # Found in user's output
            'ro.product.odm.marketname',  # Found in user's output
            'ro.product.system_dlkm.marketname', # Found in user's output
            'ro.product.bootimage.marketname', # Found in user's output
            'ro.product.display',         # Less common but might exist
            'ro.product.name',
            'ro.product.device',
            'ro.product.model',           # Always available, good fallback
            'ro.vendor.product.model',
            'ro.system.product.model',
            'ro.system_ext.product.model',
            'ro.odm.product.model',
            # Add other potential properties if known for specific devices
        ]

        fetched_values = {}
        essential_info_fetched = {'model': False, 'version': False, 'battery': False} # Track essential fetches


        # --- Fetch essential properties first ---
        # Get Model
        model_command = ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model']
        stdout_model, stderr_model, returncode_model = self._run_adb_command(model_command, timeout=5)
        if returncode_model == 0 and stdout_model:
             model_value = stdout_model.strip().strip("'\"\r")
             if model_value:
                 info['model'] = model_value
                 fetched_values['ro.product.model'] = info['model'] # Store in fetched_values too
                 essential_info_fetched['model'] = True
                 # print(f"DEBUG: Fetched ro.product.model: '{info['model']}'") # DEBUG PRINT
             # else: _run_adb_command handles warning for empty stdout on success
        # else: _run_adb_command handles error status


        # Get Android Version
        version_command = ['adb', '-s', serial, 'shell', 'getprop', 'ro.build.version.release']
        stdout_version, stderr_version, returncode_version = self._run_adb_command(version_command, timeout=5)
        if returncode_version == 0 and stdout_version:
             version_value = stdout_version.strip().strip("'\"\r")
             if version_value:
                 info['version'] = version_value
                 essential_info_fetched['version'] = True
                 # print(f"DEBUG: Fetched ro.build.version.release: '{info['version']}'") # DEBUG PRINT
             # else: _run_adb_command handles warning for empty stdout on success
        # else: _run_adb_command handles error status


        # Get Battery Level
        battery_command = ['adb', '-s', serial, 'shell', 'dumpsys', 'battery']
        stdout_battery, stderr_battery, returncode_battery = self._run_adb_command(battery_command, timeout=5)
        if returncode_battery == 0 and stdout_battery:
            # Parse battery output to find the level
            # Output often contains a line like "level: 85"
            for line in stdout_battery.splitlines():
                line = line.strip()
                if line.startswith('level:'):
                    try:
                        level_str = line.split(':')[1].strip()
                        info['battery_level'] = f"{level_str}%"
                        essential_info_fetched['battery'] = True
                        # print(f"DEBUG: Fetched battery level: '{info['battery_level']}'") # DEBUG PRINT
                        break # Found the level, no need to check other lines
                    except (IndexError, ValueError) as e:
                        self._update_status(f"Warning: Could not parse battery level line: '{line}'", level="warning")
                        # print(f"DEBUG: Battery parsing error: {e}") # DEBUG PRINT

        # else: _run_adb_command handles error status


        # --- Fetch other potential name/model properties in preference order ---
        best_display_name_found = None

        for prop_name in prop_names_to_try:
            # Skip properties we already explicitly fetched
            if prop_name in ['ro.product.model', 'ro.build.version.release']:
                 continue

            command = ['adb', '-s', serial, 'shell', 'getprop', prop_name]
            stdout, stderr, returncode = self._run_adb_command(command, timeout=5)
            if returncode == 0 and stdout:
                 value = stdout.strip().strip("'\"\r")
                 # print(f"DEBUG: Fetched {prop_name}: '{value}'") # DEBUG PRINT
                 if value: # Only store non-empty values
                     fetched_values[prop_name] = value

                     # Check if this value is a good candidate for display_name
                     # Prioritize based on the order in prop_names_to_try
                     # Only set if we haven't found a better one yet
                     if best_display_name_found is None:
                         if 'ro.product.model' in fetched_values and value == fetched_values['ro.product.model']:
                              # If same as model, only prioritize if it's a marketname property
                              if 'marketname' in prop_name.lower():
                                   best_display_name_found = value
                                #    print(f"DEBUG: Setting potential best_display_name_found (marketname): '{value}' from {prop_name}") # DEBUG PRINT
                             # else: skip, it's just the model again
                         else:
                              # Value is different from model or model wasn't fetched yet, use it
                              best_display_name_found = value
                            #   print(f"DEBUG: Setting potential best_display_name_found: '{value}' from {prop_name}") # DEBUG PRINT


            # _run_adb_command handles error status for individual fetches if returncode != 0 or stderr
            # We don't increment errors_during_fetch_count for these non-essential properties


        # --- Finalize display_name ---
        if best_display_name_found and best_display_name_found not in ['N/A', 'Error', '']:
            info['display_name'] = best_display_name_found
            # print(f"DEBUG: Final display_name set from best candidate: '{info['display_name']}'") # DEBUG PRINT
        # Fallback: If no suitable display_name found, use the fetched model
        elif info['model'] not in ['N/A', 'Error']:
             info['display_name'] = info['model'] # Fallback to model
            #  print(f"DEBUG: Final display_name set from ro.product.model (fallback): '{info['display_name']}') # DEBUG PRINT
        # Fallback: If model also failed, use the serial
        else:
             info['display_name'] = serial # Fallback to serial
            #  print(f"DEBUG: Final display_name set from serial (fallback): '{info['display_name']}') # DEBUG PRINT


        # --- Check if essential info failed ---
        # Consider a significant failure if we couldn't get at least model OR version
        # We check the flags set earlier. Battery is not considered essential for overall device identification.
        if not essential_info_fetched['model'] and not essential_info_fetched['version']:
             self._update_status(f"Failed to fetch essential model/version info for device {serial}.", level="error")
             return None # Indicate total failure
        else:
             # At least one essential piece of info was fetched.
             self._update_status(f"Info fetch complete for {serial}.", level="info")
             # print(f"DEBUG: Final info dictionary for {serial}: {info}") # DEBUG PRINT
             return info # Return the dictionary


    # Add other ADB command methods here:

    def reboot_device(self, serial, mode=""):
        """
        Reboots the specified device into a specific mode or normally.

        Args:
            serial: The serial number or IP:port of the target device.
            mode: The reboot mode ("recovery", "bootloader", "sideload", "sideload-auto-reboot" or "" for normal).

        Returns:
            True if the command was sent successfully, False otherwise.
        """
        if not self.adb_available: return False
        if not serial:
             self._update_status("Error: No device selected to reboot.", level="error")
             return False

        valid_modes = ["", "recovery", "bootloader", "sideload", "sideload-auto-reboot"]
        if mode not in valid_modes:
            self._update_status(f"Error: Invalid reboot mode '{mode}'. Valid modes are: {', '.join(valid_modes)}.", level="error")
            return False

        command = ['adb', '-s', serial, 'reboot']
        if mode:
            command.append(mode)
            self._update_status(f"Sending command: Rebooting device {serial} to {mode}...", level="info")
        else:
             self._update_status(f"Sending command: Rebooting device {serial} normally...", level="info")

        # Reboot commands typically don't have useful stdout/stderr on success,
        # and return code is often 0 even if the device immediately disconnects/reboots.
        # We just check if the command was sent without local errors (_run_adb_command handles its own errors).
        stdout, stderr, returncode = self._run_adb_command(command, timeout=10)

        # If _run_adb_command reported an error (returncode != 0 or stderr/exception), status is updated there.
        # If returncode == 0 and no stderr, assume command was sent successfully.
        if returncode == 0 and not stderr.strip():
            self._update_status(f"Reboot command sent successfully to {serial}.", level="info")
            return True
        else:
             # _run_adb_command already updated status on failure/warning
             return False


    def power_off_device(self, serial):
        """
        Powers off the specified device.

        Args:
            serial: The serial number or IP:port of the target device.

        Returns:
            True if the command was sent successfully, False otherwise.
        """
        if not self.adb_available: return False
        if not serial:
             self._update_status("Error: No device selected to power off.", level="error")
             return False

        self._update_status(f"Sending command: Powering off device {serial}...", level="info")
        # 'reboot -p' is the most common and reliable way to power off via shell
        command = ['adb', '-s', serial, 'shell', 'reboot', '-p']
        stdout, stderr, returncode = self._run_adb_command(command, timeout=10)

        # Similar to reboot, power off might not give a clean success indication
        # as the device shuts down. We check if the command was sent.
        if returncode == 0 and not stderr.strip():
             self._update_status(f"Power off command sent successfully to {serial}.", level="info")
             return True
        else:
             # _run_adb_command already updated status on failure/warning
        # else: Device might still be powering off even if ADB reported a warning/error
             return False


    def install_apk(self, serial, apk_path):
        """
        Installs an APK file on the specified device.

        Args:
            serial: The serial number or IP:port of the target device.
            apk_path: The full path to the .apk file to install.

        Returns:
            True if the installation reported success, False otherwise.
        """
        if not self.adb_available: return False
        if not serial or not apk_path:
             self._update_status("Error: Device and APK path must be specified for installation.", level="error")
             return False

        if not os.path.exists(apk_path):
            self._update_status(f"Error: APK file not found at {apk_path}", level="error")
            return False

        self._update_status(f"Sending command: Installing {os.path.basename(apk_path)} on {serial}...", level="info")

        # Basic install command. Could be extended with -r (reinstall) or -g (grant permissions)
        command = ['adb', '-s', serial, 'install', '-r', apk_path]

        # Installation can take a significant amount of time for large APKs
        stdout, stderr, returncode = self._run_adb_command(command, timeout=300)

        if returncode == 0 and "success" in stdout.lower():
            self._update_status(f"Successfully installed {os.path.basename(apk_path)}.", level="info")
            return True
        else:
            # _run_adb_command updates status for command errors/stderr
            if returncode == 0 and "failure" in stdout.lower():
                self._update_status(f"Installation reported failure: {stdout.strip()}", level="error")
            return False


    def list_packages(self, serial, user_only=True):
        """
        Lists installed packages on the specified device for user 0.

        Args:
            serial: The serial number or IP:port of the target device.
            user_only: If True, list only non-system (3rd party) packages.

        Returns:
            A list of package names (strings), or an empty list if error or no packages found.
        """
        if not self.adb_available: return []
        if not serial:
             self._update_status("Error: No device selected to list packages.", level="warning")
             return []

        user_id = '0' # Always target the primary user

        self._update_status(f"Listing packages for device {serial} (User {user_id}, {'User apps only' if user_only else 'All apps'})...", level="info")

        command = ['adb', '-s', serial, 'shell', 'pm', 'list', 'packages', '--user', user_id]
        if user_only:
            command.append('-3') # Filter for third-party apps

        # Using a longer timeout as listing packages can take time on some devices
        stdout, stderr, returncode = self._run_adb_command(command, timeout=60)

        packages = []
        if returncode == 0 and stdout:
            # Output is typically like "package:com.example.app\r\n"
            for line in stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('package:'):
                    # Extract the package name after "package:"
                    package_name = line[len('package:'):].strip()
                    if package_name:
                        packages.append(package_name)

            self._update_status(f"Found {len(packages)} packages.", level="info")
        # _run_adb_command handles status for non-zero returncode or stderr
        elif returncode == 0 and not stdout.strip():
             # Return code 0 but empty stdout might mean no packages found with the filter
             self._update_status("No packages found with the current filter.", level="info")
        # else: error status handled by _run_adb_command

        return packages


    def uninstall_package(self, serial, package_name, user_id='0'):
        """
        Uninstalls a package from the specified device for a given user.

        Args:
            serial: The serial number or IP:port of the target device.
            package_name: The package name to uninstall (e.g., "com.example.app").
            user_id: The user ID to uninstall from (default '0').

        Returns:
            True if the uninstall command reported success, False otherwise.
        """
        if not self.adb_available: return False
        if not serial or not package_name:
             self._update_status("Error: Device and package must be specified for uninstall.", level="error")
             return False

        self._update_status(f"Sending command: Uninstalling {package_name} from {serial} (User {user_id})...", level="info")

        # Use --user flag for the specific user
        # --k flag is NOT used here as per requirement to fully uninstall if possible
        command = ['adb', '-s', serial, 'uninstall', '--user', user_id, package_name]

        stdout, stderr, returncode = self._run_adb_command(command, timeout=60) # Uninstall can take time

        if returncode == 0 and "success" in stdout.lower():
            self._update_status(f"Successfully uninstalled {package_name}.", level="info")
            return True
        else:
            # _run_adb_command updates status for command errors/stderr
            # If returncode is 0 but no "Success", it might still be a failure scenario for ADB uninstall
            if returncode == 0 and "failure" in stdout.lower():
                 self._update_status(f"Uninstall command reported failure for {package_name}: {stdout.strip()}", level="error")
            # Note: A common failure for system apps is "DELETE_FAILED_INTERNAL_ERROR" or similar.
            # We don't parse specific errors here, just check for "Success".
            return False


    def disable_package(self, serial, package_name, user_id='0'):
        """
        Disables a package for the specified user on the device.

        Args:
            serial: The serial number or IP:port of the target device.
            package_name: The package name to disable.
            user_id: The user ID to disable for (default '0').

        Returns:
            True if the disable command reported success, False otherwise.
        """
        if not self.adb_available: return False
        if not serial or not package_name:
             self._update_status("Error: Device and package must be specified for disabling.", level="error")
             return False

        self._update_status(f"Sending command: Disabling {package_name} for {serial} (User {user_id})...", level="info")

        # Use --user flag for the specific user
        command = ['adb', '-s', serial, 'shell', 'pm', 'disable-user', '--user', user_id, package_name]

        stdout, stderr, returncode = self._run_adb_command(command, timeout=30) # Disable is usually faster

        if returncode == 0:
            # The output for successful disable is often just the new package state, e.g.,
            # "Package com.example.app new state: disabled\r\n"
            # We check for the package name followed by "new state: disabled"
            if f"package {package_name} new state: disabled" in stdout.lower():
                self._update_status(f"Successfully disabled {package_name}.", level="info")
                return True
            # Else, if returncode is 0 but output doesn't confirm disable, maybe a partial success?
            # Or _run_adb_command might have reported a warning via stderr
            elif stdout.strip():
                self._update_status(f"Disable command sent for {package_name}, but output was unexpected: {stdout.strip()}", level="warning")
                return True # Assume success if returncode is 0 and some stdout
            else:
                 # Return code 0 but empty stdout - unexpected, assume failure
                 self._update_status(f"Disable command sent for {package_name} but received no output.", level="error")
                 return False

        else:
            # _run_adb_command updates status for command errors/stderr
            return False


    def get_package_details(self, serial, package_name):
        """
        Retrieves detailed information about a specific package.
        Returns a dictionary with details.
        """
        if not self.adb_available: return None
        if not serial or not package_name: return None

        self._update_status(f"Fetching details for {package_name}...", level="info")

        # We use 'dumpsys package' to get details. It's verbose, so we might want to just grep relevant lines if possible,
        # but parsing in Python is more robust against cross-platform shell differences.
        command = ['adb', '-s', serial, 'shell', 'dumpsys', 'package', package_name]
        stdout, stderr, returncode = self._run_adb_command(command, timeout=10)

        details = {
            'package_name': package_name,
            'version_name': 'Unknown',
            'version_code': 'Unknown',
            'installer': 'Unknown',
            'first_install_time': 'Unknown',
            'last_update_time': 'Unknown',
            'uid': 'Unknown',
            'permissions': []
        }

        if returncode == 0 and stdout:
            lines = stdout.splitlines()
            reading_perms = False
            for line in lines:
                line = line.strip()
                if line.startswith('versionName='):
                    details['version_name'] = line.split('=', 1)[1]
                elif line.startswith('versionCode='):
                    details['version_code'] = line.split('=', 1)[1].split(' ', 1)[0] # Handle "123 minSdk=..."
                elif line.startswith('installerPackageName='):
                    details['installer'] = line.split('=', 1)[1]
                elif line.startswith('firstInstallTime='):
                    details['first_install_time'] = line.split('=', 1)[1]
                elif line.startswith('lastUpdateTime='):
                    details['last_update_time'] = line.split('=', 1)[1]
                elif line.startswith('userId='):
                    details['uid'] = line.split('=', 1)[1]
                elif line.startswith('requested permissions:'):
                    reading_perms = True
                elif reading_perms:
                    if line.startswith('install permissions:') or line.startswith('runtime permissions:') or line == "":
                        reading_perms = False
                    else:
                        details['permissions'].append(line)

        return details


    def start_logcat(self, serial, callback):
        """
        Starts a logcat stream in a separate thread.
        Args:
            serial: Device serial.
            callback: Function to call with each new line of log (str).
        """
        if not self.adb_available or not serial:
            self._update_status("Cannot start Logcat: ADB unavailable or no device.", level="error")
            return

        if self.logcat_process:
            self.stop_logcat()

        self._stop_logcat_event.clear()
        
        # Clear buffer first?
        # self._run_adb_command(['adb', '-s', serial, 'logcat', '-c'], timeout=5)

        command = ['adb', '-s', serial, 'logcat', '-v', 'time']
        
        def _logcat_worker():
            try:
                # Use subprocess.Popen for continuous stream
                creationflags = 0
                if sys.platform.startswith('win'):
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                self.logcat_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1, # Line buffered
                    encoding='utf-8',
                    errors='replace',
                    creationflags=creationflags
                )

                while not self._stop_logcat_event.is_set():
                    line = self.logcat_process.stdout.readline()
                    if not line and self.logcat_process.poll() is not None:
                        break # Process ended
                    if line:
                        callback(line.rstrip())
            except Exception as e:
                self._update_status(f"Logcat error: {e}", level="error")
            finally:
                self.stop_logcat()

        self.logcat_thread = threading.Thread(target=_logcat_worker, daemon=True)
        self.logcat_thread.start()
        self._update_status(f"Logcat started for {serial}.", level="info")


        def stop_logcat(self):


            """Stops the currently running logcat process."""


            self._stop_logcat_event.set()


            if self.logcat_process:


                self.logcat_process.terminate()


                try:


                    self.logcat_process.wait(timeout=1)


                except subprocess.TimeoutExpired:


                    self.logcat_process.kill()


                self.logcat_process = None


                self._update_status("Logcat stopped.", level="info")


    