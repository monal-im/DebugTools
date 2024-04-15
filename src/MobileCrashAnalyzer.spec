[app]

title = Monal Mobile Crash Analyzer
package.name = MMCA
package.domain = org.test

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = shared/*,MobileCrashAnalyzer/*
icon.filename = %(source.dir)s/MobileCrashAnalyzer/data/art/icon.png
presplash.filename = %(source.dir)s/MobileCrashAnalyzer/data/art/icon.png

version = 0.1
requirements = python3,kivy,platformdirs,logging

orientation = portrait
fullscreen = 0
android.arch = armeabi-v7a

# iOS specific
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0

[buildozer]
log_level = 2