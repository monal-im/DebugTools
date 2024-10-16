import functools
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from LogViewer.storage import GlobalSettingsSingleton
from LogViewer.storage import SettingsSingleton
from shared.ui.utils import UiAutoloader

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class ChangeCurrentProfile(QtWidgets.QDialog):
    def __init__(self):
        self.setWindowTitle(f"Change Current Profile: {GlobalSettingsSingleton().getActiveProfile()}")
        self.uiLineEdit_Loglevel.setText(SettingsSingleton().getLoglevel())

        self.uiItemsLoglevel = []
        loglevels = SettingsSingleton().getLoglevels()
        for loglevelIndex in range(len(loglevels)):
            self.createLoglevel()
            uiItems = self.uiItemsLoglevel[-1]
            uiItems["nameLineEdit"].setText(list(loglevels.keys())[loglevelIndex])
            uiItems["valueLineEdit"].setText(str(list(loglevels.values())[loglevelIndex]))
        self.update()

        self.uiPushButton_addLoglevel.clicked.connect(self.createLoglevel)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.accept)

    def deleteLoglevel(self, uiItems):
        uiItems["nameLineEdit"].hide()
        uiItems["valueLineEdit"].hide()
        uiItems["deleteButton"].hide()
        del self.uiItemsLoglevel[self.uiItemsLoglevel.index(uiItems)]

    def createLoglevel(self):
        loglevelIndex = len(self.uiItemsLoglevel)
        nameLineEdit = QtWidgets.QLineEdit()
        self.uiGridLayout_loglevels.addWidget(nameLineEdit, loglevelIndex, 0)

        valueLineEdit = QtWidgets.QLineEdit()
        self.uiGridLayout_loglevels.addWidget(valueLineEdit, loglevelIndex, 1)

        deleteButton = QtWidgets.QPushButton()
        deleteButton.setText("del")
        self.uiGridLayout_loglevels.addWidget(deleteButton, loglevelIndex, 2)

        uiItems = {
            "nameLineEdit": nameLineEdit, 
            "valueLineEdit": valueLineEdit, 
            "deleteButton": deleteButton
            }

        deleteButton.clicked.connect(functools.partial(self.deleteLoglevel, uiItems))
        self.uiItemsLoglevel.append(uiItems)

    def accept(self, *args):
        # save loglevel
        newLoglevel = str(self.uiLineEdit_Loglevel.text())
        if newLoglevel != SettingsSingleton().getLoglevel():
            SettingsSingleton().setLoglevel(newLoglevel)

        # save loglevels
        loglevels = {}
        for item in self.uiItemsLoglevel:
            name = str(item["nameLineEdit"].text())
            value = item["valueLineEdit"].text()
            if value.isnumeric():
                value = int(value)
            elif value == "True":
                value = True
            elif value == "False":
                value = False
            loglevels[name] = value
        SettingsSingleton().setLoglevels(loglevels)

        # change colors in settings
        loglevelNames = SettingsSingleton().getLoglevelNames()
        colorNames    = SettingsSingleton().getColorNames()
        # add new colors
        for loglevelName in loglevelNames:
            if f"logline-{loglevelName.lower()}" not in colorNames:
                SettingsSingleton().addColorName(loglevelName)

        loglevelNames = [f"logline-{name.lower()}" for name in loglevelNames]
        logger.debug(f"{loglevelNames = }")
        logger.debug(f"{colorNames = }")
        # delete old colors
        for colorName in colorNames:
            if colorName.startswith("logline-"):
                if colorName not in loglevelNames:
                    SettingsSingleton().deleteColorName(colorName)

        logger.debug(SettingsSingleton().getColorNames())
        super().accept()
