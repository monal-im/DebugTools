from PyQt5 import QtWidgets, uic, QtGui, QtCore

from LogViewer.storage import GlobalSettingsSingleton
from shared.ui.utils import UiAutoloader, catch_exceptions

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class NewProfileDialog(QtWidgets.QDialog):
    def __init__(self):
        logger.debug("Creating NewProfileDialog...")
        self.name = ""
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)

    @catch_exceptions(logger=logger)
    def accept(self, *args):
        self.name = self.uiLineEdit_newProfileTitle.text()
        if GlobalSettingsSingleton().isNameExisting(self.name):
            self.uiLineEdit_newProfileTitle.setStyleSheet("color: red;")
        else:
            super().accept()

    @catch_exceptions(logger=logger)
    def getName(self):
        return self.name