[app]
title = Expiry Tracker
package.name = expirytracker
package.domain = org.expirytracker
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 1.0

# Requirements
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,pymongo,python-barcode,python-dateutil

# Android specific
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.gradle_dependencies = org.tensorflow:tensorflow-lite-support:0.1.0,org.tensorflow:tensorflow-lite-metadata:0.1.0

# Include your assets
android.presplash_color = #FFFFFF
android.presplash_lottie = "path/to/your/splash.json"  # If you have a splash animation
android.icon.filename = Assets/icon.png  # Your app icon
android.allow_backup = True

# Include additional files
android.add_src = Assets/

# Include fonts
android.add_assets = Fonts/*.ttf

[buildozer]
log_level = 2
warn_on_root = 1 