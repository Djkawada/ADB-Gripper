//! ADB subprocess wrapper and background logcat streaming.

use std::collections::HashMap;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc};
use std::thread::{self, JoinHandle};

#[derive(Clone, Debug)]
pub struct AdbDevice {
    pub serial: String,
    pub state: String,
    #[allow(dead_code)]
    pub description: String,
}

#[derive(Clone, Debug, Default)]
pub struct DeviceInfo {
    pub serial: String,
    pub manufacturer: String,
    pub brand: String,
    pub model: String,
    pub display_name: String,
    pub version: String,
    pub battery_level: String,
}

#[derive(Clone, Debug, Default)]
pub struct PackageDetails {
    pub package_name: String,
    pub version_name: String,
    pub version_code: String,
    pub installer: String,
    pub first_install_time: String,
    pub last_update_time: String,
    pub uid: String,
    pub permissions: Vec<String>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum UninstallOutcome {
    Uninstalled,
    Disabled,
    Failed,
}

fn adb_command() -> Command {
    #[allow(unused_mut)]
    let mut cmd = Command::new("adb");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    cmd
}

fn run_adb(args: &[&str]) -> Result<(String, String, i32), String> {
    let output = adb_command()
        .args(args)
        .output()
        .map_err(|e| format!("Failed to execute adb: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
    let code = output.status.code().unwrap_or(1);
    Ok((stdout, stderr, code))
}

pub fn is_adb_available() -> bool {
    adb_command()
        .arg("version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

pub fn list_devices() -> Result<Vec<AdbDevice>, String> {
    let (stdout, stderr, code) = run_adb(&["devices", "-l"])?;
    if code != 0 {
        let msg = if stderr.trim().is_empty() {
            format!("adb devices failed with code {code}")
        } else {
            stderr.trim().to_string()
        };
        return Err(msg);
    }

    let mut devices = Vec::new();
    for line in stdout.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with("List of devices attached") {
            continue;
        }
        let mut parts = trimmed.splitn(3, char::is_whitespace);
        let Some(serial) = parts.next().filter(|s| !s.is_empty()) else {
            continue;
        };
        let rest = trimmed[serial.len()..].trim_start();
        let mut rest_parts = rest.splitn(2, char::is_whitespace);
        let Some(state) = rest_parts.next().filter(|s| !s.is_empty()) else {
            continue;
        };
        let description = rest_parts.next().unwrap_or("").trim().to_string();

        devices.push(AdbDevice {
            serial: serial.to_string(),
            state: state.to_string(),
            description,
        });
    }
    Ok(devices)
}

pub fn connect_device(address: &str) -> Result<String, String> {
    let addr = address.trim();
    if addr.is_empty() {
        return Err("IP address is empty.".to_string());
    }
    let (stdout, stderr, code) = run_adb(&["connect", addr])?;
    if code != 0 {
        return Err(if stderr.trim().is_empty() {
            format!("adb connect failed (code {code})")
        } else {
            stderr.trim().to_string()
        });
    }
    let lower = stdout.to_lowercase();
    if lower.contains("connected to") || lower.contains("already connected") {
        Ok(stdout.trim().to_string())
    } else if lower.contains("connection refused")
        || lower.contains("unable to connect")
        || lower.contains("failed to connect")
    {
        Err(stdout.trim().to_string())
    } else {
        Ok(stdout.trim().to_string())
    }
}

pub fn get_device_info(serial: &str) -> Result<DeviceInfo, String> {
    let mut info = DeviceInfo {
        serial: serial.to_string(),
        manufacturer: "N/A".to_string(),
        brand: "N/A".to_string(),
        model: "N/A".to_string(),
        display_name: "N/A".to_string(),
        version: "N/A".to_string(),
        battery_level: "N/A".to_string(),
    };

    let (stdout_props, stderr_props, code_props) =
        run_adb(&["-s", serial, "shell", "getprop"])?;
    if code_props != 0 {
        return Err(if stderr_props.trim().is_empty() {
            format!("getprop failed with code {code_props}")
        } else {
            stderr_props.trim().to_string()
        });
    }

    let mut props: HashMap<String, String> = HashMap::new();
    for line in stdout_props.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix('[') {
            if let Some((key, val_part)) = rest.split_once("]: [") {
                if let Some(val) = val_part.strip_suffix(']') {
                    let clean = val.trim().trim_matches(|c| c == '\'' || c == '"' || c == '\r');
                    if !clean.is_empty() {
                        props.insert(key.to_string(), clean.to_string());
                    }
                }
            }
        }
    }

    for key in [
        "ro.product.manufacturer",
        "ro.product.vendor.manufacturer",
        "ro.product.odm.manufacturer",
    ] {
        if let Some(v) = props.get(key) {
            info.manufacturer = v.clone();
            break;
        }
    }

    for key in ["ro.product.brand", "ro.product.vendor.brand", "ro.product.odm.brand"] {
        if let Some(v) = props.get(key) {
            info.brand = v.clone();
            break;
        }
    }

    if let Some(v) = props.get("ro.product.model") {
        info.model = v.clone();
    }
    if let Some(v) = props.get("ro.build.version.release") {
        info.version = v.clone();
    }

    let display_candidates = [
        "ro.product.marketname",
        "ro.product.vendor.marketname",
        "ro.product.odm.marketname",
        "ro.product.system_dlkm.marketname",
        "ro.product.bootimage.marketname",
        "ro.product.display",
        "ro.product.name",
        "ro.product.device",
        "ro.product.model",
        "ro.vendor.product.model",
        "ro.system.product.model",
        "ro.system_ext.product.model",
        "ro.odm.product.model",
    ];

    let mut best_display: Option<String> = None;
    for key in display_candidates {
        if let Some(val) = props.get(key) {
            if val == &info.model && !key.contains("marketname") {
                continue;
            }
            best_display = Some(val.clone());
            break;
        }
    }
    info.display_name = best_display.unwrap_or_else(|| {
        if info.model != "N/A" {
            info.model.clone()
        } else {
            serial.to_string()
        }
    });

    if let Ok((stdout_bat, _, 0)) = run_adb(&["-s", serial, "shell", "dumpsys", "battery"]) {
        for line in stdout_bat.lines() {
            let trimmed = line.trim();
            if let Some(val) = trimmed.strip_prefix("level:") {
                info.battery_level = format!("{}%", val.trim());
                break;
            }
        }
    }

    Ok(info)
}

pub fn reboot_device(serial: &str, mode: &str) -> Result<(), String> {
    let mut args = vec!["-s", serial, "reboot"];
    if !mode.is_empty() {
        args.push(mode);
    }
    let (_, stderr, code) = run_adb(&args)?;
    if code == 0 && stderr.trim().is_empty() {
        Ok(())
    } else {
        Err(if stderr.trim().is_empty() {
            format!("Reboot failed with code {code}")
        } else {
            stderr.trim().to_string()
        })
    }
}

pub fn power_off_device(serial: &str) -> Result<(), String> {
    let (_, stderr, code) = run_adb(&["-s", serial, "shell", "reboot", "-p"])?;
    if code == 0 && stderr.trim().is_empty() {
        Ok(())
    } else {
        Err(if stderr.trim().is_empty() {
            format!("Power off failed with code {code}")
        } else {
            stderr.trim().to_string()
        })
    }
}

pub fn install_apk(serial: &str, apk_path: &str) -> Result<(), String> {
    if !Path::new(apk_path).exists() {
        return Err(format!("APK file not found: {apk_path}"));
    }
    let (stdout, stderr, code) = run_adb(&["-s", serial, "install", "-r", apk_path])?;
    if code == 0 && stdout.to_lowercase().contains("success") {
        Ok(())
    } else {
        let msg = if !stderr.trim().is_empty() {
            stderr.trim().to_string()
        } else {
            stdout.trim().to_string()
        };
        Err(if msg.is_empty() {
            "APK installation failed".to_string()
        } else {
            msg
        })
    }
}

pub fn list_packages(serial: &str, user_only: bool) -> Result<Vec<String>, String> {
    let mut args = vec!["-s", serial, "shell", "pm", "list", "packages", "--user", "0"];
    if user_only {
        args.push("-3");
    }
    let (stdout, stderr, code) = run_adb(&args)?;
    if code != 0 {
        return Err(if stderr.trim().is_empty() {
            format!("pm list packages failed with code {code}")
        } else {
            stderr.trim().to_string()
        });
    }
    let mut pkgs: Vec<String> = stdout
        .lines()
        .filter_map(|line| line.trim().strip_prefix("package:").map(|p| p.trim().to_string()))
        .filter(|p| !p.is_empty())
        .collect();
    pkgs.sort_by_key(|a| a.to_lowercase());
    Ok(pkgs)
}

pub fn uninstall_or_disable_package(serial: &str, package_name: &str) -> UninstallOutcome {
    if let Ok((stdout, _, 0)) = run_adb(&["-s", serial, "uninstall", "--user", "0", package_name]) {
        if stdout.to_lowercase().contains("success") {
            return UninstallOutcome::Uninstalled;
        }
    }
    if let Ok((stdout, _, 0)) = run_adb(&[
        "-s",
        serial,
        "shell",
        "pm",
        "disable-user",
        "--user",
        "0",
        package_name,
    ]) {
        let lower = stdout.to_lowercase();
        if lower.contains("new state: disabled") || !stdout.trim().is_empty() {
            return UninstallOutcome::Disabled;
        }
    }
    UninstallOutcome::Failed
}

pub fn get_package_details(serial: &str, package_name: &str) -> Result<PackageDetails, String> {
    let (stdout, stderr, code) =
        run_adb(&["-s", serial, "shell", "dumpsys", "package", package_name])?;
    if code != 0 {
        return Err(if stderr.trim().is_empty() {
            format!("dumpsys package failed with code {code}")
        } else {
            stderr.trim().to_string()
        });
    }

    let mut details = PackageDetails {
        package_name: package_name.to_string(),
        version_name: "Unknown".to_string(),
        version_code: "Unknown".to_string(),
        installer: "Unknown".to_string(),
        first_install_time: "Unknown".to_string(),
        last_update_time: "Unknown".to_string(),
        uid: "Unknown".to_string(),
        permissions: Vec::new(),
    };

    let mut reading_perms = false;
    for line in stdout.lines() {
        let trimmed = line.trim();
        if let Some(v) = trimmed.strip_prefix("versionName=") {
            details.version_name = v.to_string();
        } else if let Some(v) = trimmed.strip_prefix("versionCode=") {
            details.version_code = v.split_whitespace().next().unwrap_or("Unknown").to_string();
        } else if let Some(v) = trimmed.strip_prefix("installerPackageName=") {
            details.installer = v.to_string();
        } else if let Some(v) = trimmed.strip_prefix("firstInstallTime=") {
            details.first_install_time = v.to_string();
        } else if let Some(v) = trimmed.strip_prefix("lastUpdateTime=") {
            details.last_update_time = v.to_string();
        } else if let Some(v) = trimmed.strip_prefix("userId=") {
            details.uid = v.to_string();
        } else if trimmed.starts_with("requested permissions:") {
            reading_perms = true;
        } else if reading_perms {
            if trimmed.starts_with("install permissions:")
                || trimmed.starts_with("runtime permissions:")
                || trimmed.is_empty()
            {
                reading_perms = false;
            } else {
                details.permissions.push(trimmed.to_string());
            }
        }
    }

    Ok(details)
}

pub struct LogcatHandle {
    stop_flag: Arc<AtomicBool>,
    child: Arc<std::sync::Mutex<Option<Child>>>,
    worker: Option<JoinHandle<()>>,
}

impl LogcatHandle {
    pub fn start(serial: &str, line_tx: mpsc::Sender<String>) -> Result<Self, String> {
        let mut child = adb_command()
            .args(["-s", serial, "logcat", "-v", "time"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start adb logcat: {e}"))?;

        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| "Failed to capture logcat stdout".to_string())?;
        let stop_flag = Arc::new(AtomicBool::new(false));
        let stop_clone = Arc::clone(&stop_flag);
        let child_arc = Arc::new(std::sync::Mutex::new(Some(child)));

        let worker = thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines() {
                if stop_clone.load(Ordering::Relaxed) {
                    break;
                }
                match line {
                    Ok(l) => {
                        if line_tx.send(l).is_err() {
                            break;
                        }
                    }
                    Err(_) => break,
                }
            }
        });

        Ok(Self {
            stop_flag,
            child: child_arc,
            worker: Some(worker),
        })
    }

    pub fn stop(&mut self) {
        self.stop_flag.store(true, Ordering::Relaxed);
        if let Ok(mut guard) = self.child.lock() {
            if let Some(mut c) = guard.take() {
                let _ = c.kill();
                let _ = c.wait();
            }
        }
        if let Some(handle) = self.worker.take() {
            let _ = handle.join();
        }
    }
}

impl Drop for LogcatHandle {
    fn drop(&mut self) {
        self.stop();
    }
}
