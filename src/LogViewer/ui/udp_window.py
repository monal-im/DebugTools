import sys
import os
import functools
import logging
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from LogViewer.storage import SettingsSingleton
from shared.utils import catch_exceptions


logger = logging.getLogger(__name__)

class UdpWindow(QtWidgets.QDialog):
    @catch_exceptions(logger=logger)
    def __init__(self):
        super().__init__()
        logger.debug("Loading Ui...")
        uic.loadUi(os.path.join(os.path.dirname(__file__), os.path.splitext(__file__)[0]+".ui"), self)

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
