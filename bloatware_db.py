# ADB Gripper - Curated Android Bloatware & Service Advisor Database
# Copyright (C) 2025 Djkawada
# Licensed under GPLv3

"""
Curated database of preinstalled Android applications and background services
by manufacturer/brand, categorized by removal safety:
  - "safe": Safe to uninstall/disable for user 0 without breaking core OS features.
  - "caution": Removable, but disables a specific manufacturer feature or service.
"""

from __future__ import annotations

# Each entry: (package_name, display_name, risk, effect_explanation)
COMMON_BLOATWARE: list[tuple[str, str, str, str]] = [
    (
        "com.facebook.katana",
        "Facebook",
        "safe",
        "Preinstalled Facebook app. Removing frees storage and stops background sync; can be reinstalled from Play Store.",
    ),
    (
        "com.facebook.system",
        "Facebook App Installer",
        "safe",
        "Stub service used by Meta to silently install/update Facebook apps. Safe to remove with no OS impact.",
    ),
    (
        "com.facebook.appmanager",
        "Facebook App Manager",
        "safe",
        "Background updater for Meta apps. Safe to remove; Play Store handles updates if you use Facebook.",
    ),
    (
        "com.facebook.services",
        "Facebook Services",
        "safe",
        "Background telemetry and push helper for Meta apps. Safe to remove.",
    ),
    (
        "com.microsoft.appmanager",
        "Link to Windows Service",
        "caution",
        "Powers 'Link to Windows' / Phone Link PC integration. Remove only if you do not sync notifications or files with Windows.",
    ),
    (
        "com.microsoft.skydrive",
        "Microsoft OneDrive",
        "safe",
        "Preinstalled OneDrive cloud client. Safe to remove if you do not use OneDrive.",
    ),
    (
        "com.netflix.partner.activation",
        "Netflix Partner Activation",
        "safe",
        "Preload/partner tracking stub for Netflix. Safe to remove; Netflix still works normally if installed.",
    ),
    (
        "com.netflix.mediaclient",
        "Netflix",
        "safe",
        "Preinstalled Netflix app. Safe to remove and reinstall anytime from Play Store.",
    ),
    (
        "com.spotify.music",
        "Spotify",
        "safe",
        "Preinstalled Spotify stub/app. Safe to remove.",
    ),
    (
        "com.linkedin.android",
        "LinkedIn",
        "safe",
        "Preinstalled LinkedIn app. Safe to remove.",
    ),
    (
        "com.amazon.mShop.android.shopping",
        "Amazon Shopping",
        "safe",
        "Preinstalled Amazon shopping app. Safe to remove.",
    ),
    (
        "com.amazon.appmanager",
        "Amazon App Manager",
        "safe",
        "Background stub for preloaded Amazon apps. Safe to remove.",
    ),
    (
        "com.ironsrc.aura.appcloud",
        "AppCloud (ironSource)",
        "safe",
        "Adware/app recommendation installer bundled by carriers and OEMs. Safe and recommended to remove.",
    ),
    (
        "com.aura.oobe.samsung",
        "AppCloud OOBE",
        "safe",
        "Post-setup app recommendation installer. Safe to remove.",
    ),
    (
        "com.dti.folderlauncher",
        "DT Ignite / App Recommendations",
        "safe",
        "Carrier/OEM silent app installer and ad folder. Safe to remove.",
    ),
    (
        "com.google.android.apps.tachyon",
        "Google Meet (Duo)",
        "safe",
        "Preinstalled video calling app. Safe to remove if you do not use Google Meet.",
    ),
    (
        "com.google.android.videos",
        "Google TV",
        "safe",
        "Preinstalled Google TV / Movies app. Safe to remove.",
    ),
    (
        "com.google.android.apps.youtube.music",
        "YouTube Music",
        "safe",
        "Preinstalled YouTube Music client. Safe to remove if you use another music player.",
    ),
    (
        "com.google.android.apps.magazines",
        "Google News",
        "safe",
        "Preinstalled Google News reader. Safe to remove.",
    ),
    (
        "com.google.android.apps.books",
        "Google Play Books",
        "safe",
        "Preinstalled e-book reader. Safe to remove.",
    ),
    (
        "com.android.dreams.basic",
        "Basic Daydreams (Screensaver)",
        "safe",
        "Legacy Android screensaver service. Safe to remove if you do not use charging screensavers.",
    ),
    (
        "com.android.egg",
        "Android Easter Egg",
        "safe",
        "Hidden Android version Easter egg mini-game. Completely safe to remove.",
    ),
]

BRAND_BLOATWARE: dict[str, list[tuple[str, str, str, str]]] = {
    "xiaomi": [
        (
            "com.miui.analytics",
            "MIUI Analytics",
            "safe",
            "Xiaomi telemetry and usage tracking service. Safe and recommended to remove; improves privacy and battery.",
        ),
        (
            "com.miui.msa.global",
            "MSA (MIUI System Ads)",
            "safe",
            "System-wide ad delivery service for MIUI/HyperOS. Removing stops ads in built-in Xiaomi apps.",
        ),
        (
            "com.xiaomi.joyose",
            "Joyose",
            "caution",
            "Telemetry + game thermal/performance tuning daemon. Removing improves privacy, but some games may lose MIUI game-turbo tuning.",
        ),
        (
            "com.miui.daemon",
            "MIUI Daemon",
            "safe",
            "Background telemetry collector sending device/app usage stats to Xiaomi. Safe to remove.",
        ),
        (
            "com.miui.bugreport",
            "Mi Feedback / Bug Report",
            "safe",
            "Xiaomi feedback and crash log reporter. Safe to remove.",
        ),
        (
            "com.xiaomi.mipicks",
            "GetApps (Mi App Store)",
            "safe",
            "Xiaomi's secondary app store (often pushes ad notifications). Safe to remove if you use Google Play Store.",
        ),
        (
            "com.mi.globalminusscreen",
            "App Vault",
            "safe",
            "Left-swipe home screen widget feed. Safe to remove if you prefer Google Discover or a clean home screen.",
        ),
        (
            "com.mi.globalbrowser",
            "Mi Browser",
            "safe",
            "Preinstalled Xiaomi web browser with news/ads. Safe to remove if you use Chrome, Firefox, or Brave.",
        ),
        (
            "com.miui.player",
            "Mi Music",
            "safe",
            "Xiaomi music player with online streaming ads. Safe to remove if you use another music app.",
        ),
        (
            "com.miui.videoplayer",
            "Mi Video",
            "safe",
            "Xiaomi video player with online feed/ads. Note: Gallery still plays videos, or install VLC/MX Player.",
        ),
        (
            "com.miui.yellowpage",
            "Yellow Pages",
            "safe",
            "Caller ID / business directory plugin for China/global regions. Safe to remove.",
        ),
        (
            "com.xiaomi.glgm",
            "Mi Games / Game Center",
            "safe",
            "Xiaomi game store and promo hub. Safe to remove.",
        ),
        (
            "com.miui.hybrid",
            "Quick Apps Service Framework",
            "safe",
            "Framework for instant/web-wrapped mini-apps and ad links. Safe to remove.",
        ),
        (
            "com.miui.hybrid.accessory",
            "Quick Apps Accessory",
            "safe",
            "Companion service for Quick Apps. Safe to remove.",
        ),
        (
            "com.xiaomi.payment",
            "Mi Pay / Coin",
            "safe",
            "Xiaomi in-app billing service for Mi Themes/GetApps. Safe to remove if you don't buy Mi Store items.",
        ),
        (
            "com.miui.mishare.connectivity",
            "Mi Share",
            "caution",
            "Cross-device file sharing with Xiaomi/OPPO/vivo phones. Remove only if you don't use Mi Share (Quick Share still works).",
        ),
        (
            "com.miui.cloudservice",
            "Xiaomi Cloud",
            "caution",
            "Syncs photos, notes, and contacts to Xiaomi Cloud and powers Find Device. Do NOT remove if you use Xiaomi Cloud or Find Device.",
        ),
        (
            "com.miui.cloudbackup",
            "Xiaomi Cloud Backup",
            "caution",
            "Automatic Xiaomi Cloud backup. Safe to remove if you rely on Google Backup instead.",
        ),
        (
            "com.miui.notes",
            "Mi Notes",
            "safe",
            "Preinstalled Xiaomi Notes app. Safe to remove if you use Google Keep or another notes app.",
        ),
        (
            "com.miui.compass",
            "Mi Compass",
            "safe",
            "Preinstalled compass utility. Safe to remove.",
        ),
        (
            "com.miui.weather2",
            "Mi Weather",
            "caution",
            "Preinstalled weather app and lock-screen weather widget. Removing disables the built-in weather widget.",
        ),
        (
            "com.miui.cleanmaster",
            "Cleaner",
            "safe",
            "Ad-supported storage cleaner powered by CleanMaster/Tencent. Safe to remove; Android/Files handles storage.",
        ),
        (
            "com.xiaomi.scanner",
            "Mi Scanner",
            "safe",
            "QR/document scanner app. Safe to remove if you use Google Lens or your camera's built-in QR reader.",
        ),
        (
            "com.miui.android.fashiongallery",
            "Wallpaper Carousel",
            "safe",
            "Lock-screen rotating ad/magazine wallpapers. Safe and recommended to remove.",
        ),
    ],
    "samsung": [
        (
            "com.samsung.android.bixby.agent",
            "Bixby Voice",
            "safe",
            "Samsung's voice assistant. Safe to remove if you use Google Assistant / Gemini or no voice assistant.",
        ),
        (
            "com.samsung.android.bixby.wakeup",
            "Bixby Voice Wakeup",
            "safe",
            "Always-listening 'Hi Bixby' trigger. Safe to remove; saves battery.",
        ),
        (
            "com.samsung.android.app.spage",
            "Samsung Free / News",
            "safe",
            "Left-swipe home screen news & ad feed. Safe to remove.",
        ),
        (
            "com.samsung.android.game.gamehome",
            "Gaming Hub (Game Launcher)",
            "safe",
            "Samsung game aggregator with ads/promotions. Games still launch normally from the app drawer.",
        ),
        (
            "com.samsung.android.game.gos",
            "Game Optimizing Service (GOS)",
            "caution",
            "Throttles CPU/GPU in games for thermals/battery. Removing can improve sustained FPS but increases heat and battery drain.",
        ),
        (
            "com.samsung.android.ardrawing",
            "AR Doodle",
            "safe",
            "Camera AR drawing add-on. Safe to remove if unused.",
        ),
        (
            "com.samsung.android.aremoji",
            "AR Emoji",
            "safe",
            "Samsung animated avatar generator. Safe to remove.",
        ),
        (
            "com.samsung.android.arzone",
            "AR Zone",
            "safe",
            "Hub for AR Emoji / AR Doodle camera features. Safe to remove.",
        ),
        (
            "com.samsung.android.app.tips",
            "Samsung Tips",
            "safe",
            "User manual and feature tips notifications. Safe to remove.",
        ),
        (
            "com.samsung.android.kidsinstaller",
            "Samsung Kids Installer",
            "safe",
            "Stub installer for Samsung Kids mode. Safe to remove if you don't use Kids Mode.",
        ),
        (
            "com.samsung.android.app.sbrowseredge",
            "Samsung Internet Edge Panel",
            "safe",
            "Edge panel bookmarks shortcut for Samsung Internet. Safe to remove.",
        ),
        (
            "com.sec.android.app.sbrowser",
            "Samsung Internet Browser",
            "safe",
            "Preinstalled Samsung browser. Safe to remove if you use Chrome, Firefox, or Brave.",
        ),
        (
            "com.samsung.android.scloud",
            "Samsung Cloud",
            "caution",
            "Syncs Samsung Gallery, Notes, and settings. Remove only if you use Google Photos/Drive instead.",
        ),
        (
            "com.samsung.android.spay",
            "Samsung Wallet / Pay",
            "caution",
            "Tap-to-pay and digital passes. Remove only if you use Google Wallet or don't use NFC payments.",
        ),
        (
            "com.samsung.android.pass",
            "Samsung Pass",
            "caution",
            "Biometric password autofill for Samsung apps. Remove only if you use Bitwarden, 1Password, or Google Password Manager.",
        ),
        (
            "com.samsung.android.app.watchmanagerstub",
            "Galaxy Wearable Stub",
            "caution",
            "Helper for pairing Galaxy Watch/Buds. Keep if you own Samsung wearables.",
        ),
        (
            "com.samsung.android.mdx",
            "Link to Windows (Samsung)",
            "caution",
            "Integrates Samsung phone with Windows Phone Link. Safe to remove if you don't pair with Windows.",
        ),
        (
            "com.samsung.android.rubin.app",
            "Customization Service",
            "safe",
            "Samsung behavioral profiling for personalized ads and suggestions. Safe to remove.",
        ),
        (
            "com.samsung.android.da.daagent",
            "Dual Messenger",
            "caution",
            "Allows running two instances of WhatsApp/Telegram. Keep if you use Dual Messenger.",
        ),
        (
            "com.samsung.android.messaging",
            "Samsung Messages",
            "caution",
            "Samsung SMS app. Safe to remove ONLY if Google Messages (or another SMS app) is already set as default.",
        ),
    ],
    "oneplus": [
        (
            "com.oneplus.brickmode",
            "Zen Space (Zen Mode)",
            "safe",
            "Digital wellbeing lock-out timer. Safe to remove if unused.",
        ),
        (
            "com.oneplus.account",
            "OnePlus Account",
            "caution",
            "Required for Red Cable Club and OnePlus Cloud sync. Safe to remove if you don't use OnePlus cloud/membership.",
        ),
        (
            "com.heytap.cloud",
            "HeyTap Cloud",
            "caution",
            "OPPO/OnePlus cloud backup service. Safe to remove if you use Google Backup.",
        ),
        (
            "com.heytap.browser",
            "HeyTap / Internet Browser",
            "safe",
            "Preinstalled ColorOS/OxygenOS browser. Safe to remove.",
        ),
        (
            "com.heytap.market",
            "App Market",
            "safe",
            "Secondary OEM app store. Safe to remove if you use Google Play Store.",
        ),
        (
            "com.oplus.games",
            "OPlus Games",
            "caution",
            "Game Space overlay and performance profiles. Games run fine without it, but you lose the in-game sidebar.",
        ),
        (
            "com.coloros.weather2",
            "Weather (ColorOS/OxygenOS)",
            "caution",
            "Built-in weather app and home widget. Safe to remove if you use another weather app.",
        ),
    ],
    "oppo": [
        (
            "com.heytap.browser",
            "HeyTap Browser",
            "safe",
            "Preinstalled OPPO browser with news feed. Safe to remove.",
        ),
        (
            "com.heytap.market",
            "OPPO App Market",
            "safe",
            "Secondary app store. Safe to remove if using Google Play Store.",
        ),
        (
            "com.heytap.cloud",
            "HeyTap Cloud",
            "caution",
            "OPPO cloud backup. Safe to remove if using Google Backup.",
        ),
        (
            "com.coloros.gamespace",
            "Game Space",
            "caution",
            "In-game performance overlay. Games still run normally if removed.",
        ),
        (
            "com.oppo.quicksearchbox",
            "Global Search",
            "safe",
            "Swipe-down ad/app search overlay. Safe to remove.",
        ),
    ],
    "realme": [
        (
            "com.heytap.browser",
            "Realme / HeyTap Browser",
            "safe",
            "Preinstalled browser with notifications/ads. Safe to remove.",
        ),
        (
            "com.heytap.market",
            "App Market",
            "safe",
            "Secondary app store. Safe to remove if using Google Play Store.",
        ),
        (
            "com.realme.link",
            "Realme Link",
            "caution",
            "Companion app for Realme Buds/Watch. Keep if you use Realme wearables.",
        ),
        (
            "com.heytap.cloud",
            "HeyTap Cloud",
            "caution",
            "Realme cloud sync. Safe to remove if using Google Backup.",
        ),
    ],
    "huawei": [
        (
            "com.huawei.browser",
            "Huawei Browser",
            "safe",
            "Preinstalled Huawei browser. Safe to remove if using another browser.",
        ),
        (
            "com.huawei.himovie.overseas",
            "Huawei Video",
            "safe",
            "Huawei streaming video app. Safe to remove.",
        ),
        (
            "com.huawei.music",
            "Huawei Music",
            "safe",
            "Preinstalled music player. Safe to remove.",
        ),
        (
            "com.huawei.gameassistant",
            "Huawei AppAssistant",
            "caution",
            "Game acceleration/DND overlay. Games still work if removed.",
        ),
        (
            "com.huawei.hidisk",
            "Huawei Cloud",
            "caution",
            "Huawei Cloud Drive & backup. Keep if you use Huawei Cloud.",
        ),
        (
            "com.huawei.tips",
            "Huawei Tips",
            "safe",
            "Device tips and guides. Safe to remove.",
        ),
    ],
    "honor": [
        (
            "com.hihonor.tips",
            "Honor Tips",
            "safe",
            "Device tips and tutorials. Safe to remove.",
        ),
        (
            "com.hihonor.video",
            "Honor Video",
            "safe",
            "Preinstalled video player/streaming app. Safe to remove.",
        ),
        (
            "com.hihonor.cloud",
            "Honor Cloud",
            "caution",
            "Honor Cloud backup. Keep if you use Honor Cloud.",
        ),
    ],
    "motorola": [
        (
            "com.motorola.demo",
            "Motorola Retail Demo",
            "safe",
            "Store demo mode app. Safe to remove.",
        ),
        (
            "com.motorola.brapps",
            "Moto App Box",
            "safe",
            "Recommended/sponsored app installer. Safe to remove.",
        ),
        (
            "com.motorola.genie",
            "Device Help",
            "safe",
            "Motorola support & troubleshooting app. Safe to remove.",
        ),
        (
            "com.motorola.gamemode",
            "Moto Gametime",
            "caution",
            "Gaming DND and sidebar overlay. Games still run if removed.",
        ),
        (
            "com.motorola.moto",
            "Moto (Gestures & Actions)",
            "caution",
            "Controls chop-chop flashlight, twist-to-camera, and Peek Display. Keep if you use Moto gestures.",
        ),
    ],
}

BRAND_ALIASES: dict[str, str] = {
    "xiaomi": "xiaomi",
    "redmi": "xiaomi",
    "poco": "xiaomi",
    "blackshark": "xiaomi",
    "samsung": "samsung",
    "oneplus": "oneplus",
    "oppo": "oppo",
    "realme": "realme",
    "huawei": "huawei",
    "honor": "honor",
    "motorola": "motorola",
    "moto": "motorola",
}

BRAND_DISPLAY_NAMES: dict[str, str] = {
    "xiaomi": "Xiaomi / Redmi / POCO",
    "samsung": "Samsung",
    "oneplus": "OnePlus",
    "oppo": "OPPO",
    "realme": "Realme",
    "huawei": "Huawei",
    "honor": "Honor",
    "motorola": "Motorola",
    "generic": "Generic Android",
}


def normalize_brand(manufacturer: str = "", brand: str = "") -> str:
    """Maps raw ro.product.manufacturer / ro.product.brand values to a canonical brand key."""
    for raw in (brand, manufacturer):
        token = (raw or "").strip().lower()
        if token in BRAND_ALIASES:
            return BRAND_ALIASES[token]
        for alias, canonical in BRAND_ALIASES.items():
            if alias in token:
                return canonical
    return "generic"


def classify_installed_packages(
    installed_packages: list[str],
    manufacturer: str = "",
    brand: str = "",
) -> dict:
    """
    Matches installed packages on the connected device against the bloatware database
    for the detected maker + cross-brand common bloatware.

    Returns:
        {
            "brand_key": str,
            "brand_label": str,
            "safe": list[dict],
            "caution": list[dict],
        }
    """
    brand_key = normalize_brand(manufacturer, brand)
    brand_label = BRAND_DISPLAY_NAMES.get(brand_key, "Generic Android")
    installed_set = set(installed_packages or [])

    candidates: list[tuple[str, str, str, str, str]] = []
    for pkg, name, risk, desc in BRAND_BLOATWARE.get(brand_key, []):
        candidates.append((pkg, name, risk, desc, brand_label))
    for pkg, name, risk, desc in COMMON_BLOATWARE:
        candidates.append((pkg, name, risk, desc, "Common / Third-Party"))

    seen: set[str] = set()
    safe_list: list[dict] = []
    caution_list: list[dict] = []

    for pkg, name, risk, desc, source_brand in candidates:
        if pkg in installed_set and pkg not in seen:
            seen.add(pkg)
            entry = {
                "package": pkg,
                "name": name,
                "risk": risk,
                "description": desc,
                "source": source_brand,
            }
            if risk == "safe":
                safe_list.append(entry)
            else:
                caution_list.append(entry)

    safe_list.sort(key=lambda item: item["name"].lower())
    caution_list.sort(key=lambda item: item["name"].lower())

    return {
        "brand_key": brand_key,
        "brand_label": brand_label,
        "safe": safe_list,
        "caution": caution_list,
    }
