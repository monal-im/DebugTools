[app]

title = Monal Mobile Crash Analyzer
package.name = MMCA
package.domain = monal-im.org

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version.filename = src/MobileCrashAnalyzer.py

version = 0.1
requirements = python3,kivy

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