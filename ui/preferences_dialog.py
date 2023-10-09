from PyQt5 import QtWidgets, uic, QtGui, QtCore
from storage import SettingsSingleton
import functools
import sys, os

from utils import paths

import logging
logger = logging.getLogger(__name__)

class DeletableQListWidget(QtWidgets.QListWidget):
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            self.takeItem(self.selectedIndexes()[0].row())
        else:
            super().keyPressEvent(event)

class PreferencesDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi(paths.get_ui_filepath("preferences_dialog.ui"), self)
        self.setWindowIcon(QtGui.QIcon(paths.get_art_filepath("monal_log_viewer.png")))

        self.colors = {}
        for colorName in SettingsSingleton().getColorNames():
            self.colors[colorName] = SettingsSingleton().getQColorTuple(colorName)
        self.history = {}
        self.misc = {}

        self._createUiTab_color()
        self._createHistory()
        self._createUiTab_misc()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self._restoreDefaults)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.close)

    def accept(self, *args):
        for color in self.colors:
            SettingsSingleton().setQColorTuple(color, self.colors[color])
        for entry in self.history:
            data = [self.history[data].item(item) for item in range(self.history[data].count())]
            SettingsSingleton().setComboboxHistory(entry, data)
        for miscItem in self.misc:
            SettingsSingleton()[miscItem] = SettingsSingleton().getMiscWidgetText(self.misc[miscItem])
        super().accept()

    def _createUiTab_color(self):
        for colorName in SettingsSingleton().getColorNames():
            colorSection = QtWidgets.QHBoxLayout()
            colorSection.addWidget(QtWidgets.QLabel(colorName, self))

            for button in self._createColorButton(colorName):
                colorSection.addWidget(button)

            self.uiGridLayout_colorTab.addLayout(colorSection)
        self.update()

    def _createColorButton(self, colorName):
        colorTuple = SettingsSingleton().getCssColorTuple(colorName)
        rgbTuple = SettingsSingleton().getColorTuple(colorName)
        buttons = []
        for index in range(len(colorTuple)):
            button = QtWidgets.QPushButton(self.uiTab_color)
            if colorTuple[index] != None:
                button.setText("rgb(%d, %d, %d)" % tuple(rgbTuple[index]))
                button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index], SettingsSingleton().getCssContrastColor(*rgbTuple[index])))
            else:
                button.setText("Add")
            button.clicked.connect(functools.partial(self._openColorPicker, colorName, index, button))
            button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(functools.partial(self._delColor, colorName, index, button))
            buttons.append(button)
        return buttons

    def _openColorPicker(self, colorName, index, button):
        if self.colors[colorName][index] != None:
            color = QtWidgets.QColorDialog.getColor(self.colors[colorName][index], parent=self)
        else:
            color = QtWidgets.QColorDialog.getColor(parent=self)

        if color.isValid():
            self.colors[colorName][index] = color

            colorTuple = self.colors[colorName]
            rgbColor = [colorTuple[index].red(), colorTuple[index].green(), colorTuple[index].blue()]
            button.setText("rgb(%d, %d, %d)" % tuple(rgbColor))
            button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index].name(), SettingsSingleton().getCssContrastColor(*rgbColor)))

    def _delColor(self, colorName, index, button):
        self.colors[colorName][index] = None
        button.setStyleSheet("")
        button.setText("Add")
    
    def _createUiTab_misc(self):
        for miscName, miscValue in SettingsSingleton().items():
            miscSection = QtWidgets.QHBoxLayout()
            miscSection.addWidget(QtWidgets.QLabel(miscName, self))
            widget = self._createMiscWidget(miscValue)
            miscSection.addWidget(widget)
            self.uiGridLayout_miscTab.addLayout(miscSection)
            self.misc[miscName] = widget
                
    def _createMiscWidget(self, item):
        if type(item) == int:
            widget = QtWidgets.QSpinBox()
            widget.setValue(item)
        elif type(item) == int:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(1)
            widget.setSingleStep(0.1)
            widget.setValue(item)
        elif type(item) == str:
            widget = QtWidgets.QLineEdit()
            widget.insert(item)
        elif type(item) == bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(item)
        return widget

    def _createHistory(self):
        for combobox in SettingsSingleton().getComboboxNames():
            historySection = QtWidgets.QVBoxLayout()
            deletableQListWidget = DeletableQListWidget()
            deletableQListWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            for item in SettingsSingleton().getComboboxHistoryByName(combobox):
                deletableQListWidget.addItem(QtWidgets.QListWidgetItem(item))

            addSection = QtWidgets.QHBoxLayout()
            lineEdit = QtWidgets.QLineEdit()
            button = QtWidgets.QPushButton()
            button.clicked.connect(functools.partial(self._addComboboxItem, deletableQListWidget, lineEdit))
            button.setText("Add")
            addSection.addWidget(button)
            addSection.addWidget(lineEdit) 
            historySection.addWidget(QtWidgets.QLabel(combobox, self))
            historySection.addWidget(deletableQListWidget)
            historySection.addLayout(addSection)
            self.uiVLayout_historyTab.addLayout(historySection)
            self.history[combobox] = deletableQListWidget

    def _addComboboxItem(self, listWidget, lineEdit):
        if lineEdit.text() != None:
            listWidget.addItem(QtWidgets.QListWidgetItem(lineEdit.text()))

    def _restoreDefaults(self):
        msgBox = QtWidgets.QMessageBox.warning(
            self,
            "Monal Log Viewer | WARNING", 
            "Make sure that nothing important is going on, due to the shutdown of this program!"
        )
        def deleteSettings():
            os.remove(paths.get_conf_filepath("settings.json"))
            sys.exit()
        msgBox.accepted.connect(deleteSettings)
        msgBox.show()