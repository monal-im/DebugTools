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

        self._setColor()
        self._createUiTab_color()
        self._createHistory()
        self._createUiTab_misc()
        self._createDisplayText()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self._restoreDefaults)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(functools.partial(SettingsSingleton().storePreferences, self.values))
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.close)

    def _createUiTab_color(self):
        self.uiTab_colorWidgetList = []
        for colorName in SettingsSingleton().getColorNames():
            colorSection = QtWidgets.QHBoxLayout()
            colorSection.addWidget(QtWidgets.QLabel(colorName, self))
            self.values["color"].append({colorName: SettingsSingleton().getColorTuple(colorName)})

            for button in self._createColorButton(colorName):
                colorSection.addWidget(button)

            self.uiGridLayout_colorTab.addLayout(colorSection)
            self.uiTab_colorWidgetList.append(colorSection)
        self.update()

    def _createColorButton(self, colorName):
        colorTuple = self.colors[colorName]
        buttons = []
        for index in range(len(colorTuple)):
            button = QtWidgets.QPushButton(self.uiTab_color)
            if colorTuple[index] != None:
                rgbColor = [colorTuple[index].red(), colorTuple[index].green(), colorTuple[index].blue()]
                button.setText("rgb(%s)" % str(rgbColor).replace("[", "").replace("]", ""))
                button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index].name(), SettingsSingleton().getCssContrastColor(*rgbColor)))
            else:
                button.setText("Add")
            button.clicked.connect(functools.partial(self._openColorPicker, colorName, index))
            button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(functools.partial(self._delColor, colorName, index))
            buttons.append(button)
        return buttons

    def _setColor(self):
        self.colors = {}
        for colorName in SettingsSingleton().getColorNames():
            self.colors[colorName] = SettingsSingleton().getQColorTuple(colorName)

    def _openColorPicker(self, colorName, index):
        if self.colors[colorName][index] != None:
            color = QtWidgets.QColorDialog.getColor(self.colors[colorName][index], parent=self)
        else:
            color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.colors[colorName][index] = color

        for layout in self.uiTab_colorWidgetList:
            for index in range(layout.count()):
                layout.itemAt(index).widget().hide()
        
        self._createUiTab_color()

    def _delColor(self, colorName, index):
        self.colors[colorName][index] = None
        for layout in self.uiTab_colorWidgetList:
            for index in range(layout.count()):
                layout.itemAt(index).widget().hide()
        self._createUiTab_color()
    
    def _createUiTab_misc(self):
        for miscName, miscValue in SettingsSingleton().items():
            miscSection = QtWidgets.QHBoxLayout()
            miscSection.addWidget(QtWidgets.QLabel(miscName, self))
            widget = self._prepareMiscItems(miscValue)
            self.values["misc"].append({miscName: widget}) 
            miscSection.addWidget(widget)
            self.uiGridLayout_miscTab.addLayout(miscSection)
                
    def _prepareMiscItems(self, item):
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