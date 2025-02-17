import sys
import os
import functools
import logging
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from LogViewer.storage import SettingsSingleton
from shared.utils import catch_exceptions
from shared.ui.utils import UiAutoloader


logger = logging.getLogger(__name__)

@UiAutoloader
class UdpWindow(QtWidgets.QDialog):
    @catch_exceptions(logger=logger)
    def __init__(self):

        logger.debug("Loading Combobox items...")
        self.uiLineEdit_key.setText(SettingsSingleton().getUdpEncryptionKey())
        self.uiLineEdit_host.setText(SettingsSingleton().getUdpHost())
        self.uiSpinBox_port.setValue(SettingsSingleton().getUdpPort())
    
    @catch_exceptions(logger=logger)
    def accept(self, *args):
        logger.info("Saving udp-rawlog streaming presets...")
        SettingsSingleton().setUdpEncryptionKey(self.uiLineEdit_key.text())
        SettingsSingleton().setUdpHost(self.uiLineEdit_host.text())
        SettingsSingleton().setUdpPort(self.uiSpinBox_port.value())

        super().accept()
