[buildozer]
log_level = 2

[app]
title = Monal Mobile Crash Analyzer
package.name = MMCA
package.domain = im.monal

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = shared/*,MobileCrashAnalyzer/*
icon.filename = %(source.dir)s/MobileCrashAnalyzer/data/art/icon.png
presplash.filename = %(source.dir)s/MobileCrashAnalyzer/data/art/icon.png

requirements = python3,kivy,platformdirs,logging,jnius

orientation = portrait
fullscreen = 0

# android specific
android.minapi = 29
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.arch = armeabi-v7a
android.manifest.intent_filters = intent_filters.xml

# iOS specific
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0
