from PyQt5 import QtWidgets, QtGui

from shared.utils import catch_exceptions, Paths
from LogViewer.utils.version import VERSION
from shared.ui.utils import UiAutoloader

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class AboutDialog(QtWidgets.QDialog):
    @catch_exceptions(logger=logger)
    def __init__(self):
        self.uiLabel_version.setText(VERSION)
        self.uiLabel_configDir.setText(Paths.user_data_dir())
        self.uiLabel_loggerDir.setText(Paths.user_log_dir())
