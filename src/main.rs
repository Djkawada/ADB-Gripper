#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod adb;
mod bloatware;

use adb::{AdbDevice, DeviceInfo, LogcatHandle, PackageDetails, UninstallOutcome};
use bloatware::{classify_installed_packages, BloatwareReport};
use eframe::egui;
use std::collections::HashSet;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    DeviceControl,
    AppManagement,
    BloatwareAdvisor,
    Logcat,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum AppFilter {
    UserApps,
    AllApps,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum StatusLevel {
    Info,
    Warning,
    Error,
}

enum BgEvent {
    DevicesListed(Result<Vec<AdbDevice>, String>),
    IpConnected(String, Result<String, String>),
    DeviceInfoFetched(String, Result<DeviceInfo, String>),
    ActionFinished(String, Result<String, String>, bool),
    ApkInstalled(Result<String, String>),
    PackagesListed(Result<Vec<String>, String>),
    BloatwareScanned(Result<BloatwareReport, String>),
    UninstallProgress(String, UninstallOutcome),
    UninstallComplete,
    PackageDetailsFetched(Result<PackageDetails, String>),
}

struct AdbGripperApp {
    adb_available: bool,
    devices: Vec<AdbDevice>,
    selected_serial: Option<String>,
    device_info: Option<DeviceInfo>,
    ip_input: String,

    active_tab: Tab,
    busy: bool,

    // App Management
    selected_apk: Option<PathBuf>,
    app_filter: AppFilter,
    packages: Vec<String>,
    selected_packages: HashSet<String>,
    package_status_tags: std::collections::HashMap<String, UninstallOutcome>,
    details_modal: Option<PackageDetails>,

    // Bloatware Advisor
    bloatware_report: Option<BloatwareReport>,
    selected_bloatware: HashSet<String>,
    confirm_uninstall: Option<Vec<String>>,

    // Logcat
    logcat_handle: Option<LogcatHandle>,
    logcat_rx: Option<Receiver<String>>,
    logcat_lines: Vec<String>,

    // Status & Background Channel
    status_msg: String,
    status_level: StatusLevel,
    tx: Sender<BgEvent>,
    rx: Receiver<BgEvent>,
}

impl AdbGripperApp {
    fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let (tx, rx) = mpsc::channel();
        let adb_available = adb::is_adb_available();

        let mut app = Self {
            adb_available,
            devices: Vec::new(),
            selected_serial: None,
            device_info: None,
            ip_input: String::new(),
            active_tab: Tab::DeviceControl,
            busy: false,
            selected_apk: None,
            app_filter: AppFilter::UserApps,
            packages: Vec::new(),
            selected_packages: HashSet::new(),
            package_status_tags: std::collections::HashMap::new(),
            details_modal: None,
            bloatware_report: None,
            selected_bloatware: HashSet::new(),
            confirm_uninstall: None,
            logcat_handle: None,
            logcat_rx: None,
            logcat_lines: Vec::new(),
            status_msg: if adb_available {
                "ADB found. Searching for devices...".to_string()
            } else {
                "Error: 'adb' command not found in PATH. Please install Android SDK Platform-Tools.".to_string()
            },
            status_level: if adb_available {
                StatusLevel::Info
            } else {
                StatusLevel::Error
            },
            tx,
            rx,
        };

        if adb_available {
            app.refresh_devices(cc.egui_ctx.clone());
        }
        app
    }

    fn set_status(&mut self, msg: impl Into<String>, level: StatusLevel) {
        self.status_msg = msg.into();
        self.status_level = level;
    }

    fn current_device_ready(&self) -> bool {
        let Some(serial) = &self.selected_serial else {
            return false;
        };
        self.devices
            .iter()
            .any(|d| &d.serial == serial && d.state == "device")
    }

    fn refresh_devices(&mut self, ctx: egui::Context) {
        if !self.adb_available {
            return;
        }
        self.busy = true;
        self.set_status("Searching for ADB devices...", StatusLevel::Info);
        let tx = self.tx.clone();
        thread::spawn(move || {
            let res = adb::list_devices();
            let _ = tx.send(BgEvent::DevicesListed(res));
            ctx.request_repaint();
        });
    }

    fn connect_ip(&mut self, ctx: egui::Context) {
        let addr = self.ip_input.trim().to_string();
        if addr.is_empty() {
            self.set_status("Please enter an IP address to connect.", StatusLevel::Warning);
            return;
        }
        self.busy = true;
        self.set_status(format!("Connecting to {addr}..."), StatusLevel::Info);
        let tx = self.tx.clone();
        thread::spawn(move || {
            let res = adb::connect_device(&addr);
            let _ = tx.send(BgEvent::IpConnected(addr, res));
            ctx.request_repaint();
        });
    }

    fn select_device(&mut self, serial: String, ctx: egui::Context) {
        if self.logcat_handle.is_some() {
            self.stop_logcat();
        }
        self.selected_serial = Some(serial.clone());
        self.device_info = None;
        self.packages.clear();
        self.selected_packages.clear();
        self.package_status_tags.clear();
        self.bloatware_report = None;
        self.selected_bloatware.clear();

        let state = self
            .devices
            .iter()
            .find(|d| d.serial == serial)
            .map(|d| d.state.as_str())
            .unwrap_or("unknown");

        if state != "device" {
            let msg = if state == "unauthorized" {
                format!("Device {serial} is unauthorized. Accept the USB debugging prompt on the device.")
            } else {
                format!("Device {serial} is {state}. Cannot run ADB commands.")
            };
            self.set_status(msg, StatusLevel::Warning);
            return;
        }

        self.set_status(format!("Fetching info for {serial}..."), StatusLevel::Info);
        let tx = self.tx.clone();
        thread::spawn(move || {
            let res = adb::get_device_info(&serial);
            let _ = tx.send(BgEvent::DeviceInfoFetched(serial, res));
            ctx.request_repaint();
        });
    }

    fn refresh_packages(&mut self, ctx: egui::Context) {
        let Some(serial) = self.selected_serial.clone() else {
            return;
        };
        if !self.current_device_ready() {
            return;
        }
        let user_only = self.app_filter == AppFilter::UserApps;
        self.set_status("Listing installed packages...", StatusLevel::Info);
        let tx = self.tx.clone();
        thread::spawn(move || {
            let res = adb::list_packages(&serial, user_only);
            let _ = tx.send(BgEvent::PackagesListed(res));
            ctx.request_repaint();
        });
    }

    fn scan_bloatware(&mut self, ctx: egui::Context) {
        let Some(serial) = self.selected_serial.clone() else {
            return;
        };
        if !self.current_device_ready() {
            return;
        }
        let (manufacturer, brand) = self
            .device_info
            .as_ref()
            .map(|i| (i.manufacturer.clone(), i.brand.clone()))
            .unwrap_or_default();

        self.set_status("Scanning device for bloatware...", StatusLevel::Info);
        let tx = self.tx.clone();
        thread::spawn(move || {
            let res = adb::list_packages(&serial, false)
                .map(|pkgs| classify_installed_packages(&pkgs, &manufacturer, &brand));
            let _ = tx.send(BgEvent::BloatwareScanned(res));
            ctx.request_repaint();
        });
    }

    fn start_uninstall(&mut self, packages: Vec<String>, ctx: egui::Context) {
        let Some(serial) = self.selected_serial.clone() else {
            return;
        };
        if packages.is_empty() {
            return;
        }
        self.busy = true;
        self.set_status(
            format!("Uninstalling/disabling {} package(s)...", packages.len()),
            StatusLevel::Info,
        );
        let tx = self.tx.clone();
        thread::spawn(move || {
            for pkg in packages {
                let outcome = adb::uninstall_or_disable_package(&serial, &pkg);
                let _ = tx.send(BgEvent::UninstallProgress(pkg, outcome));
                ctx.request_repaint();
            }
            let _ = tx.send(BgEvent::UninstallComplete);
            ctx.request_repaint();
        });
    }

    fn start_logcat(&mut self, ctx: egui::Context) {
        let Some(serial) = self.selected_serial.clone() else {
            return;
        };
        if !self.current_device_ready() {
            return;
        }
        self.stop_logcat();
        let (line_tx, line_rx) = mpsc::channel();
        match LogcatHandle::start(&serial, line_tx) {
            Ok(handle) => {
                self.logcat_handle = Some(handle);
                self.logcat_rx = Some(line_rx);
                self.set_status(format!("Logcat started for {serial}."), StatusLevel::Info);
                // Repaint periodically while logcat is active
                let stop_tx = ctx;
                thread::spawn(move || {
                    loop {
                        thread::sleep(std::time::Duration::from_millis(150));
                        stop_tx.request_repaint();
                    }
                });
            }
            Err(e) => self.set_status(e, StatusLevel::Error),
        }
    }

    fn stop_logcat(&mut self) {
        if let Some(mut handle) = self.logcat_handle.take() {
            handle.stop();
            self.set_status("Logcat stopped.", StatusLevel::Info);
        }
        self.logcat_rx = None;
    }

    fn poll_events(&mut self, ctx: &egui::Context) {
        while let Ok(ev) = self.rx.try_recv() {
            match ev {
                BgEvent::DevicesListed(Ok(list)) => {
                    self.busy = false;
                    self.devices = list;
                    if self.devices.is_empty() {
                        self.selected_serial = None;
                        self.device_info = None;
                        self.packages.clear();
                        self.bloatware_report = None;
                        self.set_status("No devices found.", StatusLevel::Info);
                    } else {
                        let still_present = self
                            .selected_serial
                            .as_ref()
                            .is_some_and(|s| self.devices.iter().any(|d| &d.serial == s));
                        let target = if still_present {
                            self.selected_serial.clone().unwrap()
                        } else {
                            self.devices[0].serial.clone()
                        };
                        self.select_device(target, ctx.clone());
                    }
                }
                BgEvent::DevicesListed(Err(e)) => {
                    self.busy = false;
                    self.set_status(e, StatusLevel::Error);
                }
                BgEvent::IpConnected(addr, Ok(msg)) => {
                    self.set_status(format!("Connected to {addr}: {msg}"), StatusLevel::Info);
                    self.refresh_devices(ctx.clone());
                }
                BgEvent::IpConnected(addr, Err(e)) => {
                    self.busy = false;
                    self.set_status(format!("Failed to connect to {addr}: {e}"), StatusLevel::Error);
                }
                BgEvent::DeviceInfoFetched(serial, Ok(info)) => {
                    if self.selected_serial.as_deref() == Some(serial.as_str()) {
                        self.device_info = Some(info);
                        self.set_status(format!("Info loaded for {serial}."), StatusLevel::Info);
                        self.refresh_packages(ctx.clone());
                        self.scan_bloatware(ctx.clone());
                    }
                }
                BgEvent::DeviceInfoFetched(serial, Err(e)) => {
                    self.set_status(format!("Failed to fetch info for {serial}: {e}"), StatusLevel::Error);
                }
                BgEvent::ActionFinished(label, Ok(msg), refresh_after) => {
                    self.busy = false;
                    self.set_status(format!("{label}: {msg}"), StatusLevel::Info);
                    if refresh_after {
                        self.refresh_devices(ctx.clone());
                    }
                }
                BgEvent::ActionFinished(label, Err(e), _) => {
                    self.busy = false;
                    self.set_status(format!("{label} failed: {e}"), StatusLevel::Error);
                }
                BgEvent::ApkInstalled(Ok(msg)) => {
                    self.busy = false;
                    self.set_status(msg, StatusLevel::Info);
                    self.refresh_packages(ctx.clone());
                }
                BgEvent::ApkInstalled(Err(e)) => {
                    self.busy = false;
                    self.set_status(format!("APK install failed: {e}"), StatusLevel::Error);
                }
                BgEvent::PackagesListed(Ok(pkgs)) => {
                    self.set_status(format!("Found {} package(s).", pkgs.len()), StatusLevel::Info);
                    self.packages = pkgs;
                    self.selected_packages.clear();
                    self.package_status_tags.clear();
                }
                BgEvent::PackagesListed(Err(e)) => {
                    self.set_status(format!("Failed to list packages: {e}"), StatusLevel::Error);
                }
                BgEvent::BloatwareScanned(Ok(report)) => {
                    self.selected_bloatware.clear();
                    for item in &report.safe {
                        self.selected_bloatware.insert(item.package.to_string());
                    }
                    self.set_status(
                        format!(
                            "Bloatware scan ({}): {} safe, {} caution.",
                            report.brand_label,
                            report.safe.len(),
                            report.caution.len()
                        ),
                        StatusLevel::Info,
                    );
                    self.bloatware_report = Some(report);
                }
                BgEvent::BloatwareScanned(Err(e)) => {
                    self.set_status(format!("Bloatware scan failed: {e}"), StatusLevel::Error);
                }
                BgEvent::UninstallProgress(pkg, outcome) => {
                    self.package_status_tags.insert(pkg, outcome);
                }
                BgEvent::UninstallComplete => {
                    self.busy = false;
                    self.set_status("Uninstall/disable process complete.", StatusLevel::Info);
                    self.refresh_packages(ctx.clone());
                    self.scan_bloatware(ctx.clone());
                }
                BgEvent::PackageDetailsFetched(Ok(details)) => {
                    self.details_modal = Some(details);
                }
                BgEvent::PackageDetailsFetched(Err(e)) => {
                    self.set_status(format!("Failed to fetch package details: {e}"), StatusLevel::Error);
                }
            }
        }

        if let Some(rx) = &self.logcat_rx {
            while let Ok(line) = rx.try_recv() {
                self.logcat_lines.push(line);
                if self.logcat_lines.len() > 5000 {
                    let excess = self.logcat_lines.len() - 5000;
                    self.logcat_lines.drain(0..excess);
                }
            }
        }
    }
}

impl Drop for AdbGripperApp {
    fn drop(&mut self) {
        self.stop_logcat();
    }
}

impl eframe::App for AdbGripperApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_events(ctx);

        // Top Connection Bar
        egui::TopBottomPanel::top("top_bar").show(ctx, |ui| {
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                ui.label("Connected Devices:");
                let current_label = self
                    .selected_serial
                    .as_ref()
                    .map(|s| {
                        let st = self
                            .devices
                            .iter()
                            .find(|d| &d.serial == s)
                            .map(|d| d.state.as_str())
                            .unwrap_or("device");
                        if st == "device" {
                            s.clone()
                        } else {
                            format!("{s} [{st}]")
                        }
                    })
                    .unwrap_or_else(|| "No device".to_string());

                egui::ComboBox::from_id_salt("device_combo")
                    .selected_text(current_label)
                    .show_ui(ui, |ui| {
                        let devs = self.devices.clone();
                        for dev in devs {
                            let label = if dev.state == "device" {
                                dev.serial.clone()
                            } else {
                                format!("{} [{}]", dev.serial, dev.state)
                            };
                            let selected = self.selected_serial.as_deref() == Some(&dev.serial);
                            if ui.selectable_label(selected, label).clicked() {
                                self.select_device(dev.serial, ctx.clone());
                            }
                        }
                    });

                if ui
                    .add_enabled(self.adb_available && !self.busy, egui::Button::new("Refresh"))
                    .clicked()
                {
                    self.refresh_devices(ctx.clone());
                }

                ui.separator();
                ui.label("Connect IP:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.ip_input)
                        .hint_text("192.168.1.10:5555")
                        .desired_width(150.0),
                );
                if ui
                    .add_enabled(self.adb_available && !self.busy, egui::Button::new("Connect"))
                    .clicked()
                {
                    self.connect_ip(ctx.clone());
                }
            });

            let header = match (&self.selected_serial, &self.device_info) {
                (_, Some(info)) => format!(
                    "Selected Device: {} ({}) ({})",
                    info.display_name, info.model, info.serial
                ),
                (Some(s), None) => format!("Selected Device: {s}"),
                (None, None) => "Selected Device: None".to_string(),
            };
            ui.strong(header);
            ui.add_space(4.0);
        });

        // Bottom Status Bar
        egui::TopBottomPanel::bottom("status_bar").show(ctx, |ui| {
            ui.add_space(3.0);
            let color = match self.status_level {
                StatusLevel::Info => ui.visuals().text_color(),
                StatusLevel::Warning => egui::Color32::from_rgb(245, 166, 35),
                StatusLevel::Error => egui::Color32::from_rgb(235, 87, 87),
            };
            ui.colored_label(color, &self.status_msg);
            ui.add_space(3.0);
        });

        // Left Sidebar: Device Info
        egui::SidePanel::left("device_info_panel")
            .resizable(true)
            .default_width(220.0)
            .show(ctx, |ui| {
                ui.add_space(6.0);
                ui.heading("Device Information");
                ui.separator();
                let info = self.device_info.as_ref();
                ui.label(format!("Serial: {}", info.map(|i| i.serial.as_str()).unwrap_or("N/A")));
                ui.label(format!(
                    "Manufacturer: {}",
                    info.map(|i| i.manufacturer.as_str()).unwrap_or("N/A")
                ));
                ui.label(format!("Model: {}", info.map(|i| i.model.as_str()).unwrap_or("N/A")));
                ui.label(format!(
                    "Commercial Name: {}",
                    info.map(|i| i.display_name.as_str()).unwrap_or("N/A")
                ));
                ui.label(format!(
                    "Android Version: {}",
                    info.map(|i| i.version.as_str()).unwrap_or("N/A")
                ));
                ui.label(format!(
                    "Battery Level: {}",
                    info.map(|i| i.battery_level.as_str()).unwrap_or("N/A")
                ));
            });

        // Main Central Panel: Tabs
        let ready = self.current_device_ready() && !self.busy;
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.selectable_value(&mut self.active_tab, Tab::DeviceControl, "Device Control");
                ui.selectable_value(&mut self.active_tab, Tab::AppManagement, "App Management");
                ui.selectable_value(&mut self.active_tab, Tab::BloatwareAdvisor, "Bloatware Advisor");
                ui.selectable_value(&mut self.active_tab, Tab::Logcat, "Logcat");
            });
            ui.separator();

            match self.active_tab {
                Tab::DeviceControl => self.ui_device_control(ui, ctx, ready),
                Tab::AppManagement => self.ui_app_management(ui, ctx, ready),
                Tab::BloatwareAdvisor => self.ui_bloatware_advisor(ui, ctx, ready),
                Tab::Logcat => self.ui_logcat(ui, ctx, ready),
            }
        });

        // Confirmation Modal
        if let Some(pkgs) = self.confirm_uninstall.clone() {
            let mut open = true;
            egui::Window::new("Confirm Uninstallation")
                .collapsible(false)
                .resizable(false)
                .open(&mut open)
                .show(ctx, |ui| {
                    if self.app_filter == AppFilter::AllApps && self.active_tab == Tab::AppManagement
                    {
                        ui.colored_label(
                            egui::Color32::from_rgb(235, 87, 87),
                            "WARNING: All Apps mode is active. Removing critical system apps can brick your device!",
                        );
                    }
                    ui.label(format!(
                        "Are you sure you want to uninstall or disable {} package(s)?",
                        pkgs.len()
                    ));
                    egui::ScrollArea::vertical().max_height(200.0).show(ui, |ui| {
                        for p in &pkgs {
                            ui.monospace(p);
                        }
                    });
                    ui.add_space(8.0);
                    ui.horizontal(|ui| {
                        if ui.button("Cancel").clicked() {
                            self.confirm_uninstall = None;
                        }
                        if ui
                            .button(egui::RichText::new("Confirm Uninstall").color(egui::Color32::RED))
                            .clicked()
                        {
                            self.confirm_uninstall = None;
                            self.start_uninstall(pkgs, ctx.clone());
                        }
                    });
                });
            if !open {
                self.confirm_uninstall = None;
            }
        }

        // Package Details Modal
        if let Some(details) = self.details_modal.clone() {
            let mut open = true;
            egui::Window::new(format!("Details: {}", details.package_name))
                .default_size([480.0, 380.0])
                .open(&mut open)
                .show(ctx, |ui| {
                    ui.label(format!("Package: {}", details.package_name));
                    ui.label(format!("Version Name: {}", details.version_name));
                    ui.label(format!("Version Code: {}", details.version_code));
                    ui.label(format!("Installer: {}", details.installer));
                    ui.label(format!("First Install: {}", details.first_install_time));
                    ui.label(format!("Last Update: {}", details.last_update_time));
                    ui.label(format!("UID: {}", details.uid));
                    ui.separator();
                    ui.strong(format!("Permissions ({}):", details.permissions.len()));
                    egui::ScrollArea::vertical().show(ui, |ui| {
                        for perm in &details.permissions {
                            ui.monospace(perm);
                        }
                    });
                });
            if !open {
                self.details_modal = None;
            }
        }
    }
}

impl AdbGripperApp {
    fn ui_device_control(&mut self, ui: &mut egui::Ui, ctx: &egui::Context, ready: bool) {
        ui.add_space(10.0);
        for (label, mode, is_power_off) in [
            ("Reboot Normally", "", false),
            ("Reboot to Recovery", "recovery", false),
            ("Reboot to Bootloader", "bootloader", false),
            ("Power Off", "poweroff", true),
        ] {
            let btn = if is_power_off {
                egui::Button::new(egui::RichText::new(label).color(egui::Color32::WHITE))
                    .fill(egui::Color32::DARK_RED)
            } else {
                egui::Button::new(label)
            };
            if ui
                .add_enabled(ready, btn.min_size(egui::vec2(240.0, 34.0)))
                .clicked()
            {
                if let Some(serial) = self.selected_serial.clone() {
                    self.busy = true;
                    let tx = self.tx.clone();
                    let ctx_clone = ctx.clone();
                    let label_str = label.to_string();
                    let mode_str = mode.to_string();
                    thread::spawn(move || {
                        let res = if mode_str == "poweroff" {
                            adb::power_off_device(&serial).map(|_| "Power off command sent".to_string())
                        } else {
                            adb::reboot_device(&serial, &mode_str)
                                .map(|_| "Reboot command sent".to_string())
                        };
                        let _ = tx.send(BgEvent::ActionFinished(label_str, res, true));
                        ctx_clone.request_repaint();
                    });
                }
            }
            ui.add_space(6.0);
        }
    }

    fn ui_app_management(&mut self, ui: &mut egui::Ui, ctx: &egui::Context, ready: bool) {
        ui.horizontal(|ui| {
            ui.label("Install APK:");
            let apk_text = self
                .selected_apk
                .as_ref()
                .and_then(|p| p.file_name())
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_else(|| "No file selected".to_string());
            ui.label(apk_text);
            if ui.add_enabled(ready, egui::Button::new("Browse...")).clicked() {
                if let Some(path) = rfd::FileDialog::new()
                    .add_filter("APK files", &["apk"])
                    .pick_file()
                {
                    self.selected_apk = Some(path);
                }
            }
            let can_install = ready && self.selected_apk.as_ref().is_some_and(|p| p.exists());
            if ui.add_enabled(can_install, egui::Button::new("Install")).clicked() {
                if let (Some(serial), Some(apk)) =
                    (self.selected_serial.clone(), self.selected_apk.clone())
                {
                    self.busy = true;
                    self.set_status(
                        format!("Installing {}...", apk.file_name().unwrap_or_default().to_string_lossy()),
                        StatusLevel::Info,
                    );
                    let tx = self.tx.clone();
                    let ctx_clone = ctx.clone();
                    thread::spawn(move || {
                        let res = adb::install_apk(&serial, &apk.to_string_lossy())
                            .map(|_| "APK installed successfully.".to_string());
                        let _ = tx.send(BgEvent::ApkInstalled(res));
                        ctx_clone.request_repaint();
                    });
                }
            }
        });

        ui.separator();

        ui.horizontal(|ui| {
            ui.label("Show:");
            let prev_filter = self.app_filter;
            ui.selectable_value(&mut self.app_filter, AppFilter::UserApps, "User Apps");
            ui.selectable_value(&mut self.app_filter, AppFilter::AllApps, "All Apps");
            if self.app_filter != prev_filter && ready {
                self.refresh_packages(ctx.clone());
            }

            if ui.add_enabled(ready, egui::Button::new("Refresh List")).clicked() {
                self.refresh_packages(ctx.clone());
            }

            let sel_count = self.selected_packages.len();
            if ui
                .add_enabled(ready && sel_count == 1, egui::Button::new("Details"))
                .clicked()
            {
                if let (Some(serial), Some(pkg)) = (
                    self.selected_serial.clone(),
                    self.selected_packages.iter().next().cloned(),
                ) {
                    let tx = self.tx.clone();
                    let ctx_clone = ctx.clone();
                    thread::spawn(move || {
                        let res = adb::get_package_details(&serial, &pkg);
                        let _ = tx.send(BgEvent::PackageDetailsFetched(res));
                        ctx_clone.request_repaint();
                    });
                }
            }

            if ui
                .add_enabled(
                    ready && sel_count > 0,
                    egui::Button::new(egui::RichText::new("Uninstall Selected").color(egui::Color32::WHITE))
                        .fill(egui::Color32::DARK_RED),
                )
                .clicked()
            {
                let mut list: Vec<String> = self.selected_packages.iter().cloned().collect();
                list.sort();
                self.confirm_uninstall = Some(list);
            }
        });

        if self.app_filter == AppFilter::AllApps {
            ui.colored_label(
                egui::Color32::from_rgb(235, 87, 87),
                "Warning: Listing SYSTEM APPS. Uninstalling critical system apps can damage your device.",
            );
        } else {
            ui.colored_label(
                egui::Color32::from_rgb(245, 166, 35),
                "Caution: Listing USER APPS.",
            );
        }

        egui::ScrollArea::vertical().show(ui, |ui| {
            for pkg in &self.packages {
                let mut checked = self.selected_packages.contains(pkg);
                let label = match self.package_status_tags.get(pkg) {
                    Some(UninstallOutcome::Uninstalled) => format!("{pkg} (Uninstalled)"),
                    Some(UninstallOutcome::Disabled) => format!("{pkg} (Disabled)"),
                    Some(UninstallOutcome::Failed) => format!("{pkg} (Failed)"),
                    None => pkg.clone(),
                };
                if ui.checkbox(&mut checked, label).changed() {
                    if checked {
                        self.selected_packages.insert(pkg.clone());
                    } else {
                        self.selected_packages.remove(pkg);
                    }
                }
            }
        });
    }

    fn ui_bloatware_advisor(&mut self, ui: &mut egui::Ui, ctx: &egui::Context, ready: bool) {
        ui.horizontal(|ui| {
            let maker = self
                .bloatware_report
                .as_ref()
                .map(|r| r.brand_label)
                .unwrap_or("Not scanned");
            ui.strong(format!("Detected Maker: {maker}"));

            if ui.add_enabled(ready, egui::Button::new("Scan Device")).clicked() {
                self.scan_bloatware(ctx.clone());
            }

            let has_safe = self
                .bloatware_report
                .as_ref()
                .is_some_and(|r| !r.safe.is_empty());
            if ui
                .add_enabled(ready && has_safe, egui::Button::new("Select All Safe"))
                .clicked()
            {
                if let Some(report) = &self.bloatware_report {
                    for item in &report.safe {
                        self.selected_bloatware.insert(item.package.to_string());
                    }
                }
            }

            let has_any = self
                .bloatware_report
                .as_ref()
                .is_some_and(|r| !r.safe.is_empty() || !r.caution.is_empty());
            if ui
                .add_enabled(ready && has_any, egui::Button::new("Clear"))
                .clicked()
            {
                self.selected_bloatware.clear();
            }

            if ui
                .add_enabled(
                    ready && !self.selected_bloatware.is_empty(),
                    egui::Button::new(egui::RichText::new("Remove Selected").color(egui::Color32::WHITE))
                        .fill(egui::Color32::DARK_RED),
                )
                .clicked()
            {
                let mut list: Vec<String> = self.selected_bloatware.iter().cloned().collect();
                list.sort();
                self.confirm_uninstall = Some(list);
            }
        });

        let Some(report) = self.bloatware_report.clone() else {
            ui.label("Connect a device to automatically detect its maker and scan for safe-to-remove bloatware.");
            return;
        };

        ui.label(format!(
            "Found {} safe-to-remove app(s) (pre-selected) and {} removable app(s) with feature trade-offs.",
            report.safe.len(),
            report.caution.len()
        ));
        ui.separator();

        egui::ScrollArea::vertical().show(ui, |ui| {
            if report.safe.is_empty() && report.caution.is_empty() {
                ui.label("No known bloatware packages detected on this device.");
                return;
            }

            if !report.safe.is_empty() {
                ui.colored_label(
                    egui::Color32::from_rgb(76, 175, 80),
                    format!("Safe to Remove Without Risk ({})", report.safe.len()),
                );
                for item in &report.safe {
                    egui::Frame::group(ui.style()).show(ui, |ui| {
                        let mut checked = self.selected_bloatware.contains(item.package);
                        if ui
                            .checkbox(&mut checked, format!("{} ({})", item.name, item.package))
                            .changed()
                        {
                            if checked {
                                self.selected_bloatware.insert(item.package.to_string());
                            } else {
                                self.selected_bloatware.remove(item.package);
                            }
                        }
                        ui.label(format!("[{}] {}", item.source, item.description));
                    });
                }
                ui.add_space(8.0);
            }

            if !report.caution.is_empty() {
                ui.colored_label(
                    egui::Color32::from_rgb(245, 166, 35),
                    format!(
                        "Remove with Caution — Read Effect Before Removing ({})",
                        report.caution.len()
                    ),
                );
                for item in &report.caution {
                    egui::Frame::group(ui.style()).show(ui, |ui| {
                        let mut checked = self.selected_bloatware.contains(item.package);
                        if ui
                            .checkbox(&mut checked, format!("{} ({})", item.name, item.package))
                            .changed()
                        {
                            if checked {
                                self.selected_bloatware.insert(item.package.to_string());
                            } else {
                                self.selected_bloatware.remove(item.package);
                            }
                        }
                        ui.label(format!("[{}] {}", item.source, item.description));
                    });
                }
            }
        });
    }

    fn ui_logcat(&mut self, ui: &mut egui::Ui, ctx: &egui::Context, ready: bool) {
        ui.horizontal(|ui| {
            let running = self.logcat_handle.is_some();
            if ui
                .add_enabled(ready && !running, egui::Button::new("Start Logcat"))
                .clicked()
            {
                self.start_logcat(ctx.clone());
            }
            if ui
                .add_enabled(running, egui::Button::new("Stop Logcat"))
                .clicked()
            {
                self.stop_logcat();
            }
            if ui.button("Clear").clicked() {
                self.logcat_lines.clear();
            }
            if ui.button("Save Log").clicked() {
                if let Some(path) = rfd::FileDialog::new()
                    .set_file_name("logcat.txt")
                    .add_filter("Text files", &["txt"])
                    .save_file()
                {
                    let content = self.logcat_lines.join("\n");
                    match std::fs::write(&path, content) {
                        Ok(_) => self.set_status(
                            format!("Saved logcat to {}", path.display()),
                            StatusLevel::Info,
                        ),
                        Err(e) => self.set_status(format!("Failed to save log: {e}"), StatusLevel::Error),
                    }
                }
            }
        });

        ui.separator();
        egui::ScrollArea::vertical()
            .stick_to_bottom(true)
            .show(ui, |ui| {
                for line in &self.logcat_lines {
                    ui.monospace(line);
                }
            });
    }
}

fn load_icon() -> Option<egui::IconData> {
    let bytes = include_bytes!("../mon_icone.ico");
    let img = image::load_from_memory(bytes).ok()?.into_rgba8();
    let (width, height) = img.dimensions();
    Some(egui::IconData {
        rgba: img.into_raw(),
        width,
        height,
    })
}

fn main() -> eframe::Result<()> {
    let mut viewport = egui::ViewportBuilder::default()
        .with_inner_size([920.0, 640.0])
        .with_min_inner_size([640.0, 420.0]);
    if let Some(icon) = load_icon() {
        viewport = viewport.with_icon(std::sync::Arc::new(icon));
    }

    let options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    eframe::run_native(
        "ADB Gripper",
        options,
        Box::new(|cc| Ok(Box::new(AdbGripperApp::new(cc)))),
    )
}
