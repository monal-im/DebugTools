[buildozer]
log_level = 2

[app]
title = Mobile Log Viewer
package.name = MobileLogViewer
package.domain = im.monal

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = shared/*,MobileLogViewer/*
icon.filename = %(source.dir)s/MobileLogViewer/data/art/icon.png
presplash.filename = %(source.dir)s/MobileLogViewer/data/art/icon.png

requirements = python3,kivy,platformdirs,logging,jnius

orientation = portrait
fullscreen = 0

# android specific
android.minapi = 29
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION
android.arch = armeabi-v7a
android.manifest.intent_filters = intent_filters.xml

# iOS specific
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.7.0
