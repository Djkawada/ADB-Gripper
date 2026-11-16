//! Curated Android bloatware & service advisor database by manufacturer/brand.

use std::collections::HashSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Risk {
    /// Safe to uninstall/disable for user 0 without breaking core OS features.
    Safe,
    /// Removable, but disables a specific manufacturer feature or service.
    Caution,
}

#[derive(Clone, Debug)]
pub struct BloatwareItem {
    pub package: &'static str,
    pub name: &'static str,
    pub risk: Risk,
    pub description: &'static str,
    pub source: &'static str,
}

#[derive(Clone, Debug, Default)]
pub struct BloatwareReport {
    pub brand_key: &'static str,
    pub brand_label: &'static str,
    pub safe: Vec<BloatwareItem>,
    pub caution: Vec<BloatwareItem>,
}

type RawEntry = (&'static str, &'static str, Risk, &'static str);

const COMMON_BLOATWARE: &[RawEntry] = &[
    ("com.facebook.katana", "Facebook", Risk::Safe, "Preinstalled Facebook app. Removing frees storage and stops background sync; can be reinstalled from Play Store."),
    ("com.facebook.system", "Facebook App Installer", Risk::Safe, "Stub service used by Meta to silently install/update Facebook apps. Safe to remove with no OS impact."),
    ("com.facebook.appmanager", "Facebook App Manager", Risk::Safe, "Background updater for Meta apps. Safe to remove; Play Store handles updates if you use Facebook."),
    ("com.facebook.services", "Facebook Services", Risk::Safe, "Background telemetry and push helper for Meta apps. Safe to remove."),
    ("com.microsoft.appmanager", "Link to Windows Service", Risk::Caution, "Powers 'Link to Windows' / Phone Link PC integration. Remove only if you do not sync notifications or files with Windows."),
    ("com.microsoft.skydrive", "Microsoft OneDrive", Risk::Safe, "Preinstalled OneDrive cloud client. Safe to remove if you do not use OneDrive."),
    ("com.netflix.partner.activation", "Netflix Partner Activation", Risk::Safe, "Preload/partner tracking stub for Netflix. Safe to remove; Netflix still works normally if installed."),
    ("com.netflix.mediaclient", "Netflix", Risk::Safe, "Preinstalled Netflix app. Safe to remove and reinstall anytime from Play Store."),
    ("com.spotify.music", "Spotify", Risk::Safe, "Preinstalled Spotify stub/app. Safe to remove."),
    ("com.linkedin.android", "LinkedIn", Risk::Safe, "Preinstalled LinkedIn app. Safe to remove."),
    ("com.amazon.mShop.android.shopping", "Amazon Shopping", Risk::Safe, "Preinstalled Amazon shopping app. Safe to remove."),
    ("com.amazon.appmanager", "Amazon App Manager", Risk::Safe, "Background stub for preloaded Amazon apps. Safe to remove."),
    ("com.ironsrc.aura.appcloud", "AppCloud (ironSource)", Risk::Safe, "Adware/app recommendation installer bundled by carriers and OEMs. Safe and recommended to remove."),
    ("com.aura.oobe.samsung", "AppCloud OOBE", Risk::Safe, "Post-setup app recommendation installer. Safe to remove."),
    ("com.dti.folderlauncher", "DT Ignite / App Recommendations", Risk::Safe, "Carrier/OEM silent app installer and ad folder. Safe to remove."),
    ("com.google.android.apps.tachyon", "Google Meet (Duo)", Risk::Safe, "Preinstalled video calling app. Safe to remove if you do not use Google Meet."),
    ("com.google.android.videos", "Google TV", Risk::Safe, "Preinstalled Google TV / Movies app. Safe to remove."),
    ("com.google.android.apps.youtube.music", "YouTube Music", Risk::Safe, "Preinstalled YouTube Music client. Safe to remove if you use another music player."),
    ("com.google.android.apps.magazines", "Google News", Risk::Safe, "Preinstalled Google News reader. Safe to remove."),
    ("com.google.android.apps.books", "Google Play Books", Risk::Safe, "Preinstalled e-book reader. Safe to remove."),
    ("com.android.dreams.basic", "Basic Daydreams (Screensaver)", Risk::Safe, "Legacy Android screensaver service. Safe to remove if you do not use charging screensavers."),
    ("com.android.egg", "Android Easter Egg", Risk::Safe, "Hidden Android version Easter egg mini-game. Completely safe to remove."),
];

const XIAOMI_BLOATWARE: &[RawEntry] = &[
    ("com.miui.analytics", "MIUI Analytics", Risk::Safe, "Xiaomi telemetry and usage tracking service. Safe and recommended to remove; improves privacy and battery."),
    ("com.miui.msa.global", "MSA (MIUI System Ads)", Risk::Safe, "System-wide ad delivery service for MIUI/HyperOS. Removing stops ads in built-in Xiaomi apps."),
    ("com.xiaomi.joyose", "Joyose", Risk::Caution, "Telemetry + game thermal/performance tuning daemon. Removing improves privacy, but some games may lose MIUI game-turbo tuning."),
    ("com.miui.daemon", "MIUI Daemon", Risk::Safe, "Background telemetry collector sending device/app usage stats to Xiaomi. Safe to remove."),
    ("com.miui.bugreport", "Mi Feedback / Bug Report", Risk::Safe, "Xiaomi feedback and crash log reporter. Safe to remove."),
    ("com.xiaomi.mipicks", "GetApps (Mi App Store)", Risk::Safe, "Xiaomi's secondary app store (often pushes ad notifications). Safe to remove if you use Google Play Store."),
    ("com.mi.globalminusscreen", "App Vault", Risk::Safe, "Left-swipe home screen widget feed. Safe to remove if you prefer Google Discover or a clean home screen."),
    ("com.mi.globalbrowser", "Mi Browser", Risk::Safe, "Preinstalled Xiaomi web browser with news/ads. Safe to remove if you use Chrome, Firefox, or Brave."),
    ("com.miui.player", "Mi Music", Risk::Safe, "Xiaomi music player with online streaming ads. Safe to remove if you use another music app."),
    ("com.miui.videoplayer", "Mi Video", Risk::Safe, "Xiaomi video player with online feed/ads. Gallery still plays videos, or install VLC/MX Player."),
    ("com.miui.yellowpage", "Yellow Pages", Risk::Safe, "Caller ID / business directory plugin for China/global regions. Safe to remove."),
    ("com.xiaomi.glgm", "Mi Games / Game Center", Risk::Safe, "Xiaomi game store and promo hub. Safe to remove."),
    ("com.miui.hybrid", "Quick Apps Service Framework", Risk::Safe, "Framework for instant/web-wrapped mini-apps and ad links. Safe to remove."),
    ("com.miui.hybrid.accessory", "Quick Apps Accessory", Risk::Safe, "Companion service for Quick Apps. Safe to remove."),
    ("com.xiaomi.payment", "Mi Pay / Coin", Risk::Safe, "Xiaomi in-app billing service for Mi Themes/GetApps. Safe to remove if you don't buy Mi Store items."),
    ("com.miui.mishare.connectivity", "Mi Share", Risk::Caution, "Cross-device file sharing with Xiaomi/OPPO/vivo phones. Remove only if you don't use Mi Share (Quick Share still works)."),
    ("com.miui.cloudservice", "Xiaomi Cloud", Risk::Caution, "Syncs photos, notes, and contacts to Xiaomi Cloud and powers Find Device. Do NOT remove if you use Xiaomi Cloud or Find Device."),
    ("com.miui.cloudbackup", "Xiaomi Cloud Backup", Risk::Caution, "Automatic Xiaomi Cloud backup. Safe to remove if you rely on Google Backup instead."),
    ("com.miui.notes", "Mi Notes", Risk::Safe, "Preinstalled Xiaomi Notes app. Safe to remove if you use Google Keep or another notes app."),
    ("com.miui.compass", "Mi Compass", Risk::Safe, "Preinstalled compass utility. Safe to remove."),
    ("com.miui.weather2", "Mi Weather", Risk::Caution, "Preinstalled weather app and lock-screen weather widget. Removing disables the built-in weather widget."),
    ("com.miui.cleanmaster", "Cleaner", Risk::Safe, "Ad-supported storage cleaner powered by CleanMaster/Tencent. Safe to remove; Android/Files handles storage."),
    ("com.xiaomi.scanner", "Mi Scanner", Risk::Safe, "QR/document scanner app. Safe to remove if you use Google Lens or your camera's built-in QR reader."),
    ("com.miui.android.fashiongallery", "Wallpaper Carousel", Risk::Safe, "Lock-screen rotating ad/magazine wallpapers. Safe and recommended to remove."),
];

const SAMSUNG_BLOATWARE: &[RawEntry] = &[
    ("com.samsung.android.bixby.agent", "Bixby Voice", Risk::Safe, "Samsung's voice assistant. Safe to remove if you use Google Assistant / Gemini or no voice assistant."),
    ("com.samsung.android.bixby.wakeup", "Bixby Voice Wakeup", Risk::Safe, "Always-listening 'Hi Bixby' trigger. Safe to remove; saves battery."),
    ("com.samsung.android.app.spage", "Samsung Free / News", Risk::Safe, "Left-swipe home screen news & ad feed. Safe to remove."),
    ("com.samsung.android.game.gamehome", "Gaming Hub (Game Launcher)", Risk::Safe, "Samsung game aggregator with ads/promotions. Games still launch normally from the app drawer."),
    ("com.samsung.android.game.gos", "Game Optimizing Service (GOS)", Risk::Caution, "Throttles CPU/GPU in games for thermals/battery. Removing can improve sustained FPS but increases heat and battery drain."),
    ("com.samsung.android.ardrawing", "AR Doodle", Risk::Safe, "Camera AR drawing add-on. Safe to remove if unused."),
    ("com.samsung.android.aremoji", "AR Emoji", Risk::Safe, "Samsung animated avatar generator. Safe to remove."),
    ("com.samsung.android.arzone", "AR Zone", Risk::Safe, "Hub for AR Emoji / AR Doodle camera features. Safe to remove."),
    ("com.samsung.android.app.tips", "Samsung Tips", Risk::Safe, "User manual and feature tips notifications. Safe to remove."),
    ("com.samsung.android.kidsinstaller", "Samsung Kids Installer", Risk::Safe, "Stub installer for Samsung Kids mode. Safe to remove if you don't use Kids Mode."),
    ("com.samsung.android.app.sbrowseredge", "Samsung Internet Edge Panel", Risk::Safe, "Edge panel bookmarks shortcut for Samsung Internet. Safe to remove."),
    ("com.sec.android.app.sbrowser", "Samsung Internet Browser", Risk::Safe, "Preinstalled Samsung browser. Safe to remove if you use Chrome, Firefox, or Brave."),
    ("com.samsung.android.scloud", "Samsung Cloud", Risk::Caution, "Syncs Samsung Gallery, Notes, and settings. Remove only if you use Google Photos/Drive instead."),
    ("com.samsung.android.spay", "Samsung Wallet / Pay", Risk::Caution, "Tap-to-pay and digital passes. Remove only if you use Google Wallet or don't use NFC payments."),
    ("com.samsung.android.pass", "Samsung Pass", Risk::Caution, "Biometric password autofill for Samsung apps. Remove only if you use Bitwarden, 1Password, or Google Password Manager."),
    ("com.samsung.android.app.watchmanagerstub", "Galaxy Wearable Stub", Risk::Caution, "Helper for pairing Galaxy Watch/Buds. Keep if you own Samsung wearables."),
    ("com.samsung.android.mdx", "Link to Windows (Samsung)", Risk::Caution, "Integrates Samsung phone with Windows Phone Link. Safe to remove if you don't pair with Windows."),
    ("com.samsung.android.rubin.app", "Customization Service", Risk::Safe, "Samsung behavioral profiling for personalized ads and suggestions. Safe to remove."),
    ("com.samsung.android.da.daagent", "Dual Messenger", Risk::Caution, "Allows running two instances of WhatsApp/Telegram. Keep if you use Dual Messenger."),
    ("com.samsung.android.messaging", "Samsung Messages", Risk::Caution, "Samsung SMS app. Safe to remove ONLY if Google Messages (or another SMS app) is already set as default."),
];

const ONEPLUS_BLOATWARE: &[RawEntry] = &[
    ("com.oneplus.brickmode", "Zen Space (Zen Mode)", Risk::Safe, "Digital wellbeing lock-out timer. Safe to remove if unused."),
    ("com.oneplus.account", "OnePlus Account", Risk::Caution, "Required for Red Cable Club and OnePlus Cloud sync. Safe to remove if you don't use OnePlus cloud/membership."),
    ("com.heytap.cloud", "HeyTap Cloud", Risk::Caution, "OPPO/OnePlus cloud backup service. Safe to remove if you use Google Backup."),
    ("com.heytap.browser", "HeyTap / Internet Browser", Risk::Safe, "Preinstalled ColorOS/OxygenOS browser. Safe to remove."),
    ("com.heytap.market", "App Market", Risk::Safe, "Secondary OEM app store. Safe to remove if you use Google Play Store."),
    ("com.oplus.games", "OPlus Games", Risk::Caution, "Game Space overlay and performance profiles. Games run fine without it, but you lose the in-game sidebar."),
    ("com.coloros.weather2", "Weather (ColorOS/OxygenOS)", Risk::Caution, "Built-in weather app and home widget. Safe to remove if you use another weather app."),
];

const OPPO_BLOATWARE: &[RawEntry] = &[
    ("com.heytap.browser", "HeyTap Browser", Risk::Safe, "Preinstalled OPPO browser with news feed. Safe to remove."),
    ("com.heytap.market", "OPPO App Market", Risk::Safe, "Secondary app store. Safe to remove if using Google Play Store."),
    ("com.heytap.cloud", "HeyTap Cloud", Risk::Caution, "OPPO cloud backup. Safe to remove if using Google Backup."),
    ("com.coloros.gamespace", "Game Space", Risk::Caution, "In-game performance overlay. Games still run normally if removed."),
    ("com.oppo.quicksearchbox", "Global Search", Risk::Safe, "Swipe-down ad/app search overlay. Safe to remove."),
];

const REALME_BLOATWARE: &[RawEntry] = &[
    ("com.heytap.browser", "Realme / HeyTap Browser", Risk::Safe, "Preinstalled browser with notifications/ads. Safe to remove."),
    ("com.heytap.market", "App Market", Risk::Safe, "Secondary app store. Safe to remove if using Google Play Store."),
    ("com.realme.link", "Realme Link", Risk::Caution, "Companion app for Realme Buds/Watch. Keep if you use Realme wearables."),
    ("com.heytap.cloud", "HeyTap Cloud", Risk::Caution, "Realme cloud sync. Safe to remove if using Google Backup."),
];

const HUAWEI_BLOATWARE: &[RawEntry] = &[
    ("com.huawei.browser", "Huawei Browser", Risk::Safe, "Preinstalled Huawei browser. Safe to remove if using another browser."),
    ("com.huawei.himovie.overseas", "Huawei Video", Risk::Safe, "Huawei streaming video app. Safe to remove."),
    ("com.huawei.music", "Huawei Music", Risk::Safe, "Preinstalled music player. Safe to remove."),
    ("com.huawei.gameassistant", "Huawei AppAssistant", Risk::Caution, "Game acceleration/DND overlay. Games still work if removed."),
    ("com.huawei.hidisk", "Huawei Cloud", Risk::Caution, "Huawei Cloud Drive & backup. Keep if you use Huawei Cloud."),
    ("com.huawei.tips", "Huawei Tips", Risk::Safe, "Device tips and guides. Safe to remove."),
];

const HONOR_BLOATWARE: &[RawEntry] = &[
    ("com.hihonor.tips", "Honor Tips", Risk::Safe, "Device tips and tutorials. Safe to remove."),
    ("com.hihonor.video", "Honor Video", Risk::Safe, "Preinstalled video player/streaming app. Safe to remove."),
    ("com.hihonor.cloud", "Honor Cloud", Risk::Caution, "Honor Cloud backup. Keep if you use Honor Cloud."),
];

const MOTOROLA_BLOATWARE: &[RawEntry] = &[
    ("com.motorola.demo", "Motorola Retail Demo", Risk::Safe, "Store demo mode app. Safe to remove."),
    ("com.motorola.brapps", "Moto App Box", Risk::Safe, "Recommended/sponsored app installer. Safe to remove."),
    ("com.motorola.genie", "Device Help", Risk::Safe, "Motorola support & troubleshooting app. Safe to remove."),
    ("com.motorola.gamemode", "Moto Gametime", Risk::Caution, "Gaming DND and sidebar overlay. Games still run if removed."),
    ("com.motorola.moto", "Moto (Gestures & Actions)", Risk::Caution, "Controls chop-chop flashlight, twist-to-camera, and Peek Display. Keep if you use Moto gestures."),
];

pub fn normalize_brand(manufacturer: &str, brand: &str) -> (&'static str, &'static str) {
    for raw in [brand, manufacturer] {
        let token = raw.trim().to_lowercase();
        if token.contains("xiaomi") || token.contains("redmi") || token.contains("poco") || token.contains("blackshark") {
            return ("xiaomi", "Xiaomi / Redmi / POCO");
        }
        if token.contains("samsung") {
            return ("samsung", "Samsung");
        }
        if token.contains("oneplus") {
            return ("oneplus", "OnePlus");
        }
        if token.contains("oppo") {
            return ("oppo", "OPPO");
        }
        if token.contains("realme") {
            return ("realme", "Realme");
        }
        if token.contains("huawei") {
            return ("huawei", "Huawei");
        }
        if token.contains("honor") {
            return ("honor", "Honor");
        }
        if token.contains("motorola") || token == "moto" {
            return ("motorola", "Motorola");
        }
    }
    ("generic", "Generic Android")
}

fn brand_entries(brand_key: &str) -> &'static [RawEntry] {
    match brand_key {
        "xiaomi" => XIAOMI_BLOATWARE,
        "samsung" => SAMSUNG_BLOATWARE,
        "oneplus" => ONEPLUS_BLOATWARE,
        "oppo" => OPPO_BLOATWARE,
        "realme" => REALME_BLOATWARE,
        "huawei" => HUAWEI_BLOATWARE,
        "honor" => HONOR_BLOATWARE,
        "motorola" => MOTOROLA_BLOATWARE,
        _ => &[],
    }
}

pub fn classify_installed_packages(
    installed_packages: &[String],
    manufacturer: &str,
    brand: &str,
) -> BloatwareReport {
    let (brand_key, brand_label) = normalize_brand(manufacturer, brand);
    let installed: HashSet<&str> = installed_packages.iter().map(String::as_str).collect();
    let mut seen: HashSet<&'static str> = HashSet::new();

    let mut safe = Vec::new();
    let mut caution = Vec::new();

    for (entries, source) in [
        (brand_entries(brand_key), brand_label),
        (COMMON_BLOATWARE, "Common / Third-Party"),
    ] {
        for &(pkg, name, risk, description) in entries {
            if installed.contains(pkg) && seen.insert(pkg) {
                let item = BloatwareItem {
                    package: pkg,
                    name,
                    risk,
                    description,
                    source,
                };
                match risk {
                    Risk::Safe => safe.push(item),
                    Risk::Caution => caution.push(item),
                }
            }
        }
    }

    safe.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    caution.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));

    BloatwareReport {
        brand_key,
        brand_label,
        safe,
        caution,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classifies_xiaomi_and_common_bloatware() {
        let pkgs = vec![
            "com.miui.analytics".to_string(),
            "com.xiaomi.joyose".to_string(),
            "com.facebook.services".to_string(),
            "com.android.settings".to_string(),
        ];
        let report = classify_installed_packages(&pkgs, "Xiaomi", "Redmi");
        assert_eq!(report.brand_key, "xiaomi");
        assert_eq!(report.safe.len(), 2);
        assert!(report.safe.iter().all(|i| i.risk == Risk::Safe));
        assert_eq!(report.caution.len(), 1);
        assert_eq!(report.caution[0].risk, Risk::Caution);
    }

    #[test]
    fn classifies_samsung_bloatware() {
        let pkgs = vec![
            "com.samsung.android.bixby.agent".to_string(),
            "com.samsung.android.game.gos".to_string(),
        ];
        let report = classify_installed_packages(&pkgs, "samsung", "samsung");
        assert_eq!(report.brand_key, "samsung");
        assert_eq!(report.safe.len(), 1);
        assert_eq!(report.caution.len(), 1);
    }
}
