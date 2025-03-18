import sys
import os 
import functools
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from shared.ui.utils import UiAutoloader, catch_exceptions

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class StackPopWindow(QtWidgets.QDialog):
    def __init__(self, names):
        #uiLabel_info
        #uiListWidget_items
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)
        if len(names) != 0:
            self.names = names
            for name in names:
                self.uiListWidget_items.addItem(f"{name}    |    {names[name]}")
        else:
            self.uiLabel_info.setText("There are currently no saved states!")

    @catch_exceptions(logger=logger)
    def accept(self, *args):
        if self.uiListWidget_items.selectedItems():
            self.index = self.uiListWidget_items.currentRow()
            super().accept()
        else:
            self.uiLabel_info.setText("Select a state!")

    @catch_exceptions(logger=logger)
    def getIndex(self):
        return list(self.names.keys())[self.index]
        