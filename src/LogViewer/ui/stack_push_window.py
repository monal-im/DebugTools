import sys
import os 
import functools
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from shared.ui.utils import UiAutoloader, catch_exceptions

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class StackPushWindow(QtWidgets.QDialog):
    def __init__(self, names):
        self.uiLineEdit_name.setText(self.generateUniqueName(names))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.names = names

    @catch_exceptions(logger=logger)
    def accept(self, *args):
        userInput = self.uiLineEdit_name.text()
        if len(userInput) != 0 and userInput not in self.names:
            self.name = userInput
            super().accept()
        elif userInput in self.names:
            self.uiLabel_info.setText("Please enter a name that doesn't exist yet!")
        else:
            self.uiLabel_info.setText("Please enter a name for this entry bellow!")

    @catch_exceptions(logger=logger)
    def getName(self):
        return self.name
    
    def generateUniqueName(self, names):
        presentStacks = [entry for entry in names if entry.startswith("Stack #")]

        uniqueId = 1
        uniqueName = f"Stack #{uniqueId}"
        while uniqueName in names:
            uniqueId += 1
            uniqueName = f"Stack #{uniqueId}"

        return uniqueName