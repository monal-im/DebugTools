from jnius import autoclass, cast
from android import activity, mActivity, permissions

J_Intent = autoclass("android.content.Intent")
J_PythonActivity = autoclass('org.kivy.android.PythonActivity')
J_Environment = autoclass("android.os.Environment")
J_Settings = autoclass("android.provider.Settings")
J_Uri = autoclass("android.net.Uri")

import logging
logger = logging.getLogger(__name__)

# See: https://stackoverflow.com/questions/64849485/why-is-filemanager-not-working-on-android-kivymd
def permissions_external_storage(self, *args):                  
    if not J_Environment.isExternalStorageManager():
        try:
            logger.debug("Ask for ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION")
            context = mActivity.getApplicationContext()
            uri = J_Uri.parse("package:" + context.getPackageName())
            intent = J_Intent(J_Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, uri)
        except Exception as e:
            logger.debug("ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION Failed! Open ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION")
            intent = J_Intent(J_Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
        currentActivity = cast("android.app.Activity", J_PythonActivity.mActivity)
        currentActivity.startActivityForResult(intent, 101)