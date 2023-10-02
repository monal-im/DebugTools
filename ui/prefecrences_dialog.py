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

        self.values = {"color": [], "history": [], "misc": [], "displayText": []}

        self._createUiTab_color()
        self._createHistory()
        self._createUiTab_misc()
        self._createDisplayText()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self._restoreDefaults)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(functools.partial(SettingsSingleton().storePreferences, self.values))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.close)

    def _createUiTab_color(self):
        self.uiTab_colorWidgetList = []
        for colorIndex in range(len(SettingsSingleton().data["color"])):
            colorSection = QtWidgets.QHBoxLayout()
            color = list(SettingsSingleton().data["color"].keys())[colorIndex]
            label = QtWidgets.QLabel(self)
            label.setText(color)
            colorSection.addWidget(label)
            self.values["color"].append({color: SettingsSingleton().data["color"][color]["data"]})

            for position in range(len(SettingsSingleton().data["color"][color].keys())):
                colorSection.addWidget(self._createColorButton(colorIndex, position, "create"))

            self.uiGridLayout_colorTab.addLayout(colorSection)
            self.uiTab_colorWidgetList.append(colorSection)

    def _createColorButton(self, column, row, color=None):
        button = QtWidgets.QPushButton(self.uiTab_color)
        if color == "create":
            entry = SettingsSingleton().data["color"][list(SettingsSingleton().data["color"].keys())[column]]["data"][row]
        else:
            entry = color
        
        if entry != None:
            backgroundColor = "rgb("+ str(entry).replace("[", "").replace("]", "") + ")"
            r, g, b = entry
            foregroundColor = "rgb("+ str(self.get_luminance(r, g, b)).replace("[", "").replace("]", "") +")"
            button.setText(backgroundColor)
            button.setStyleSheet("background-color:"+backgroundColor+"; color: "+foregroundColor+"")
        else:
            button.setText("Add")
        button.clicked.connect(functools.partial(self._openColorPicker, column, row))
        button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        button.customContextMenuRequested.connect(functools.partial(self._deleteColor, column, row))
        button.show()
        return button
    
    def _openColorPicker(self, column, row):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self._setColor(column, row, color.name())

    def _deleteColor(self, column, row):
        self._setColor(column, row)

    def _setColor(self, column, row, color=None):
        name = list(SettingsSingleton().data["color"].keys())[column]
        colorRange = SettingsSingleton().getCssColorTuple(name)
        colorRange[row] = color
        self.values["color"][column][list(self.values["color"][column].keys())[0]][row] = self.returnRGBColor(color)
        layout = self.uiTab_colorWidgetList[column]
        itemToChange = layout.takeAt(row+1)
        layout.removeItem(itemToChange)
        layout.insertWidget(row+1, self._createColorButton(column,row, self.returnRGBColor(color)))

    def returnRGBColor(self, color):
        if color == None:
            color = None
        else:
            color = list(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        return color

    # see https://stackoverflow.com/a/3943023
    def get_luminance(self, r, g, b):
        colors = []
        for c in (r, g, b):
            c = c / 255.0
            if c <= 0.04045:
                c = c/12.92
            else:
                c = ((c+0.055)/1.055) ** 2.4
            colors.append(c)
        if 0.2126 * colors[0] + 0.7152 * colors[1] + 0.0722 * colors[2] > 0.179:
            return [0, 0, 0]
        return [255, 255, 255]
    
    def _createUiTab_misc(self):
        for entry in SettingsSingleton().data["misc"]:
            miscSection = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel()
            label.setText(entry)
            miscSection.addWidget(label)
            widget = self._createMiscItems(SettingsSingleton().data["misc"][entry], entry)
            self.values["misc"].append({entry: widget}) 
            miscSection.addWidget(widget)
            self.uiGridLayout_miscTab.addLayout(miscSection)
                
    def _createMiscItems(self, item, entry):
        if type(item) == int:
            widget = QtWidgets.QSpinBox()
            widget.setMaximum(170)
            widget.setValue(item)

        if type(item) == str:
            widget = QtWidgets.QLineEdit()
            widget.insert(item)

        if type(item) == bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(item)

        return widget

    def _createHistory(self):
        for combobox in SettingsSingleton().data["combobox"]:
            historySection = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel()
            label.setText(combobox)
            deletableQListWidget = DeletableQListWidget()
            deletableQListWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            for item in SettingsSingleton().data["combobox"][combobox]:
                listWidgetItem = QtWidgets.QListWidgetItem(item)
                deletableQListWidget.addItem(listWidgetItem)

            addSection = QtWidgets.QHBoxLayout()
            lineEdit = QtWidgets.QLineEdit()
            button = QtWidgets.QPushButton()
            button.clicked.connect(functools.partial(self._addComboboxItem, deletableQListWidget, lineEdit))
            button.setText("Add")
            addSection.addWidget(button)
            addSection.addWidget(lineEdit)
            self.values["history"].append({combobox: deletableQListWidget}) 
            historySection.addWidget(label)
            historySection.addWidget(deletableQListWidget)
            historySection.addLayout(addSection)
            self.uiVLayout_historyTab.addLayout(historySection)

    def _addComboboxItem(self, listWidget, lineEdit):
        if lineEdit.text() != None:
            listWidget.addItem(QtWidgets.QListWidgetItem(lineEdit.text()))

    def _restoreDefaults(self):
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setIcon(QtWidgets.QMessageBox.Information) 
        msgBox.setText("Make shure that nothing important is going on, due to the shutdown of this program!")
        def deleteSettings():
            os.remove(paths.get_conf_filepath("settings.json"))
            sys.exit()
        msgBox.accepted.connect(deleteSettings)
        msgBox.show()

    def _createDisplayText(self):
        for entry in SettingsSingleton().data["displayText"]:
            qVLayout = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel()
            label.setText(entry)
            textBox = QtWidgets.QPlainTextEdit()
            textBox.insertPlainText(SettingsSingleton().data["displayText"][entry])
            textBox.show()
            qVLayout.addWidget(label)
            qVLayout.addWidget(textBox)
            self.uiVLayout_displayTextTab.addLayout(qVLayout)
            self.values["displayText"].append({entry: textBox})