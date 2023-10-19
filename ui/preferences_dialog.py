from PyQt5 import QtWidgets, uic, QtGui, QtCore
from storage import SettingsSingleton
from ui.utils import PythonHighlighter, DeletableQListWidget
from utils import catch_exceptions
import functools
import sys, os 

from utils import paths

import logging
logger = logging.getLogger(__name__)

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
        self.formatter = {}

        self._createUiTab_color()
        self._createUiTab_history()
        self._createUiTab_misc()
        self._createUiTab_formatter()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self._restoreDefaults)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(super().accept)

    def accept(self, *args):
        for color in self.colors:
            SettingsSingleton().setQColorTuple(color, self.colors[color])
        for combobox in self.history:
            data = [self.history[combobox].item(item).text() for item in range(self.history[combobox].count())]
            SettingsSingleton().setComboboxHistoryByName(combobox, data)
        for miscItem in self.misc:
            SettingsSingleton()[miscItem] = self._getMiscWidgetText(self.misc[miscItem])
        for formatterName in self.formatter:
            SettingsSingleton().setFormatter(formatterName.text(), self.formatter[formatterName].toPlainText())
        super().accept()

    def _getMiscWidgetText(self, widget):
        if isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()

    def _createUiTab_color(self):
        for colorName in SettingsSingleton().getColorNames():
            colorSection = QtWidgets.QHBoxLayout()
            colorSection.setAlignment(QtCore.Qt.AlignTop)
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
            widget = self._createMiscWidget(miscValue, miscName)
            miscSection.addWidget(widget)
            self.uiGridLayout_miscTab.setAlignment(QtCore.Qt.AlignTop)
            self.uiGridLayout_miscTab.addLayout(miscSection)
            self.misc[miscName] = widget
                
    def _createMiscWidget(self, item, miscName):
        if type(item) == int:
            widget = QtWidgets.QSpinBox()
            widget.setValue(item)
            widget.setMaximum(240)
        elif type(item) == int:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(1)
            widget.setSingleStep(0.1)
            widget.setValue(item)
        elif type(item) == str:
            widget = QtWidgets.QComboBox()
            widget.addItems(SettingsSingleton().getFormatterNames())
            widget.setCurrentText(item)
        elif type(item) == bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(item)
        return widget

    def _createUiTab_history(self):
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

    def _createUiTab_formatter(self):
        self.syntaxHighlights = {}
        names = SettingsSingleton().getFormatterNames()
        for index in range(len(names)+1):
            lineEdit, button, plainText = self._createFormatterEntry()
            if index < len(names):
                self.syntaxHighlights[names[index]] = PythonHighlighter(plainText.document())
                lineEdit.setText(names[index])
                plainText.setPlainText(SettingsSingleton().getFormatter(names[index]))
                plainText.show()
                self.formatter[lineEdit] = plainText
                button.setText("Delete")
                button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogCancelButton")))
                button.disconnect()
                button.clicked.connect(functools.partial(self._deleteFormat, lineEdit, plainText, button))

    def _deleteFormat(self, lineEdit, plainText, button):
        del self.formatter[lineEdit]
        lineEdit.hide()
        plainText.hide()
        button.hide()

    def _addFormat(self, lineEdit, plainText, button):
        if lineEdit.text() != "" and plainText.toPlainText() != "":
            self.formatter[lineEdit] = plainText
            self.syntaxHighlights[lineEdit.text()] = PythonHighlighter(plainText.document())
            button.disconnect()
            button.setText("Delete")
            button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogCancelButton")))
            button.clicked.connect(functools.partial(self._deleteFormat, lineEdit, plainText, button))
            self._createFormatterEntry()

    def _createFormatterEntry(self):
        lineEdit = QtWidgets.QLineEdit()
        lineEdit.setPlaceholderText("Formatter name")
        plainText = QtWidgets.QPlainTextEdit()
        plainText.setPlaceholderText("retval = [...]")
        self.syntaxHighlights[""] = PythonHighlighter(plainText.document())
        button = QtWidgets.QPushButton()
        horizonalLayout = QtWidgets.QHBoxLayout()
        verticalLayout = QtWidgets.QVBoxLayout()

        verticalLayout.setAlignment(QtCore.Qt.AlignTop)

        button.setText("Create")
        button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogApplyButton")))
        button.clicked.connect(functools.partial(self._addFormat, lineEdit, plainText, button))

        verticalLayout.addWidget(lineEdit)
        verticalLayout.addWidget(button)
        horizonalLayout.addLayout(verticalLayout)
        horizonalLayout.addWidget(plainText)
        self.uiVLayout_formatTabs.addLayout(horizonalLayout)

        return (lineEdit, button, plainText)

    @catch_exceptions(logger=logger)
    def _restoreDefaults(self):
        msgBox = QtWidgets.QMessageBox.question(
            self,
            "Monal Log Viewer | WARNING", 
            "Do you really want to reset all settings and close this app?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        def deleteSettings():
            os.remove(paths.get_conf_filepath("settings.json"))
            sys.exit()
        if msgBox == QtWidgets.QMessageBox.Yes:
            deleteSettings()
        else:
            return
        msgBox.show()