import sys
import os 
import functools
from PyQt5 import QtWidgets, uic, QtGui, QtCore

from LogViewer.storage import SettingsSingleton
from .utils import PythonHighlighter, DeletableQListWidget
from shared.utils import Paths
from shared.ui.utils import UiAutoloader, catch_exceptions
import shared.ui.utils.helpers as sharedUiHelpers

import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class PreferencesDialog(QtWidgets.QDialog):
    def __init__(self):
        self.colors = {}
        for colorName in SettingsSingleton().getColorNames():
            self.colors[colorName] = SettingsSingleton().getQColorTuple(colorName)
        self.history = {}
        self.misc = {}
        self.formatter = {}
        self.loglevels = []

        self._createUiTab_color()
        self._createUiTab_history()
        self._createUiTab_misc()
        self._createUiTab_formatter()
        self._createUiTab_loglevels()

        self.buttonBox.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(self._restoreDefaults)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.accept)

    @catch_exceptions(logger=logger)
    def accept(self, *args):
        for colorName in self.colors:
            SettingsSingleton().setQColorTuple(colorName, self.colors[colorName])
        for comboboxName in self.history:
            data = [self.history[comboboxName].item(item).text() for item in range(self.history[comboboxName].count())]
            SettingsSingleton().setComboboxHistoryByName(comboboxName, data)
        for miscName in self.misc:
            SettingsSingleton()[miscName] = self._getMiscWidgetValue(miscName)
        SettingsSingleton().clearAllFormatters()
        for formatterNameLineEdit in self.formatter:
            SettingsSingleton().setFormatter(formatterNameLineEdit.text(), self.formatter[formatterNameLineEdit].toPlainText())
        loglevels = {}
        for loglevel in self.loglevels:
            loglevels = loglevels | {
                loglevel["fieldName"].text(): {"query": loglevel["query"].text(), "data": [loglevel["buttons"][button] for button in loglevel["buttons"]]}
            }
        SettingsSingleton().setLoglevels(loglevels)
        super().accept()

    def _getMiscWidgetValue(self, miscName):
        widget = self.misc[miscName]
        if isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        elif isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        elif isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        elif isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QtWidgets.QPushButton):
            if miscName == "font":
                return self.font.toString()
            else:
                return self.lastPath
        else:
            raise RuntimeError("Unknown misc widget type: %s" % str(widget))

    def _createUiTab_color(self):
        colorNames = SettingsSingleton().getColorNames()
        for colorIndex in range(len(colorNames)):
            self.uiGridLayout_colorTab.addWidget(QtWidgets.QLabel(colorNames[colorIndex], self), colorIndex, 0)
            buttons = self._createColorButton(colorNames[colorIndex])

            for buttonIndex in range(len(buttons)):
                self.uiGridLayout_colorTab.addWidget(buttons[buttonIndex], colorIndex, buttonIndex+1)
        self.update()

    @catch_exceptions(logger=logger)
    def _openColorPicker(self, colorName, index, button, *args):
        if self.colors[colorName][index] != None:
            color = QtWidgets.QColorDialog.getColor(self.colors[colorName][index], parent=self)
        else:
            color = QtWidgets.QColorDialog.getColor(parent=self)

        if color.isValid():
            self.colors[colorName][index] = color

            colorTuple = self.colors[colorName]
            rgbColor = [colorTuple[index].red(), colorTuple[index].green(), colorTuple[index].blue()]
            button.setText("rgb(%d, %d, %d)" % tuple(rgbColor))
            button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index].name(), sharedUiHelpers.getCssContrastColor(*rgbColor)))

    @catch_exceptions(logger=logger)
    def _delColor(self, colorName, index, button, colorType="color", *args):
        if colorType != "loglevel":
            self.colors[colorName][index] = None

        button.setStyleSheet("")
        button.setText("Add")

    def _createUiTab_misc(self):
        miscSection = QtWidgets.QFormLayout()
        for miscName, miscValue in SettingsSingleton().items():
            self.misc[miscName] = self._createMiscWidget(miscValue, miscName)
            miscSection.addRow(QtWidgets.QLabel(miscName, self), self.misc[miscName])
        miscSection.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        miscSection.setLabelAlignment(QtCore.Qt.AlignRight)
        self.uiGridLayout_miscTab.setAlignment(QtCore.Qt.AlignTop)
        self.uiGridLayout_miscTab.addLayout(miscSection)
                
    def _createMiscWidget(self, value, miscName):
        if type(value) == int:
            widget = QtWidgets.QSpinBox()
            widget.setMaximum(1024)
            widget.setValue(value)
        elif type(value) == float:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(1)
            widget.setSingleStep(0.1)
            widget.setValue(value)
        elif type(value) == bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
        elif type(value) == str:
            if miscName == "currentFormatter":
                widget = QtWidgets.QComboBox()
                widget.addItems(SettingsSingleton().getFormatterNames())
                widget.setCurrentText(value)
                self.currentFormatter = widget
            elif miscName == "font":
                widget = QtWidgets.QPushButton()
                self.font = SettingsSingleton().getQFont()
                widget.setText("%s, %s" % (self.font.family(), str(self.font.pointSize())))
                widget.setFont(self.font)
                widget.clicked.connect(functools.partial(self._changeFont, widget))
            elif miscName == "uiStyle":
                widget = QtWidgets.QComboBox()
                widget.addItems(sharedUiHelpers.getAvailableStyles())
                widget.setCurrentText(value)
            elif miscName == "lastPath":
                self.lastPath = SettingsSingleton().getLastPath()
                widget = QtWidgets.QPushButton()
                widget.setText(self.lastPath)
                def openLastDirDialog():
                    dirname = QtWidgets.QFileDialog.getExistingDirectory(self, "MLV | Choose default directory", self.lastPath)
                    if dirname != None and dirname != "":
                        self.lastPath = dirname
                        widget.setText(dirname)
                widget.clicked.connect(openLastDirDialog)
            else:
                widget = QtWidgets.QLineEdit()
                widget.setText(value)
        else:
            raise RuntimeError("Misc value type not implemented yet: %s" % str(type(value)))
        return widget
    
    @catch_exceptions(logger=logger)
    def _changeFont(self, widget, *args):
        fontDialog = QtWidgets.QFontDialog()
        font, valid = fontDialog.getFont(self.font)
        if valid:
            self.font = font
            widget.setText("%s, %s" % (font.family(), str(font.pointSize())))
            widget.setFont(font)

    def _createUiTab_history(self):
        for combobox in SettingsSingleton().getComboboxNames():
            historySection = QtWidgets.QVBoxLayout()
            deletableQListWidget = DeletableQListWidget()
            deletableQListWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            for item in SettingsSingleton().getComboboxHistoryByName(combobox):
                if item.strip() != "":
                    deletableQListWidget.addItem(QtWidgets.QListWidgetItem(item))

            addSection = QtWidgets.QHBoxLayout()
            lineEdit = QtWidgets.QLineEdit()
            button = QtWidgets.QPushButton("Add")
            button.clicked.connect(functools.partial(self._addComboboxItem, deletableQListWidget, lineEdit, combobox))
            addSection.addWidget(button)
            addSection.addWidget(lineEdit) 
            historySection.addWidget(QtWidgets.QLabel(combobox, self))
            historySection.addWidget(deletableQListWidget)
            historySection.addLayout(addSection)
            self.uiVLayout_historyTab.addLayout(historySection)
            self.history[combobox] = deletableQListWidget

    @catch_exceptions(logger=logger)
    def _addComboboxItem(self, listWidget, lineEdit, combobox, *args):
        if lineEdit.text() != None and lineEdit.text() not in [self.history[combobox].item(item).text() for item in range(self.history[combobox].count())]:
            listWidget.addItem(QtWidgets.QListWidgetItem(lineEdit.text()))

    def _createUiTab_formatter(self):
        self.syntaxHighlighters = {}
        names = SettingsSingleton().getFormatterNames()
        for index in range(len(names)+1):
            lineEdit, button, code = self._createFormatterEntry()
            if index < len(names):
                self.syntaxHighlighters[names[index]] = PythonHighlighter(code.document())
                lineEdit.setText(names[index])
                code.setPlainText(SettingsSingleton().getFormatter(names[index]))
                code.show()
                self.formatter[lineEdit] = code
                button.setText("Delete")
                button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogCancelButton")))
                button.disconnect()
                button.clicked.connect(functools.partial(self._deleteFormat, lineEdit, code, button))

    @catch_exceptions(logger=logger)
    def _deleteFormat(self, lineEdit, code, button, *args):
        if len(self.formatter) >= 2:
            del self.formatter[lineEdit]
            self.currentFormatter.removeItem(self.currentFormatter.findText(lineEdit.text()))
            lineEdit.hide()
            code.hide()
            button.hide()

    @catch_exceptions(logger=logger)
    def _addFormatter(self, lineEdit, code, button, *args):
        if lineEdit.text() != "" and code.toPlainText() != "":
            self.currentFormatter.addItem(lineEdit.text())
            self.formatter[lineEdit] = code
            self.syntaxHighlighters[lineEdit.text()] = PythonHighlighter(code.document())
            button.disconnect()
            button.setText("Delete")
            button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogCancelButton")))
            button.clicked.connect(functools.partial(self._deleteFormat, lineEdit, code, button))
            self._createFormatterEntry()

    def _createFormatterEntry(self):
        lineEdit = QtWidgets.QLineEdit()
        lineEdit.setPlaceholderText("Formatter name")
        code = QtWidgets.QPlainTextEdit()
        code.setPlaceholderText("def formatter(e, **g):\n\tglobals().update(g)\n\treturn \"%s %s\" % (e[\"timestamp\"], e[\"message\"])")
        self.syntaxHighlighters[""] = PythonHighlighter(code.document())
        button = QtWidgets.QPushButton("Create")
        horizonalLayout = QtWidgets.QHBoxLayout()
        verticalLayout = QtWidgets.QVBoxLayout()

        verticalLayout.setAlignment(QtCore.Qt.AlignTop)

        button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, "SP_DialogApplyButton")))
        button.clicked.connect(functools.partial(self._addFormatter, lineEdit, code, button))

        lineEdit.setMaximumWidth(200)
        button.setMaximumWidth(200)

        code.setTabStopWidth(code.fontMetrics().width(" ") * SettingsSingleton().getTabWidth())

        verticalLayout.addWidget(lineEdit)
        verticalLayout.addWidget(button)
        horizonalLayout.addLayout(verticalLayout)
        horizonalLayout.addWidget(code)
        self.uiVLayout_formatTabs.addLayout(horizonalLayout)

        return (lineEdit, button, code)

    def _createUiTab_loglevels(self):
        self.uiButton_addLoglevel.clicked.connect(self.addLoglevel)

        fieldNames = SettingsSingleton().getFieldNames()
        for fieldIndex in range(len(fieldNames)):
            fieldName = fieldNames[fieldIndex]
            uiLineEdit_fieldName = QtWidgets.QLineEdit()
            uiLineEdit_fieldName.setText(fieldName)
            self.uiGridLayout_loglevelsTab.addWidget(uiLineEdit_fieldName, fieldIndex, 0)
            uiLineEdit_query = QtWidgets.QLineEdit()
            uiLineEdit_query.setText(SettingsSingleton().getLoglevel(fieldName))
            self.uiGridLayout_loglevelsTab.addWidget(uiLineEdit_query, fieldIndex, 1)

            colorNames = SettingsSingleton().getLoglevelColorNames()
            buttons = self._createLoglevelColorButton(colorNames[fieldIndex])
            for buttonIndex in range(len(buttons)):
                self.uiGridLayout_loglevelsTab.addWidget(list(buttons.keys())[buttonIndex], fieldIndex, buttonIndex+2)

            delButton = QtWidgets.QPushButton()
            delButton.setText("Del")
            self.uiGridLayout_loglevelsTab.addWidget(delButton, fieldIndex, 5)

            uiItems = {
                "fieldName": uiLineEdit_fieldName,
                "query": uiLineEdit_query, 
                "buttons": buttons, 
                "delButton": delButton
            }
            self.loglevels.append(uiItems)
            delButton.clicked.connect(functools.partial(self.deleteLoglevel, uiItems))
        self.update()

    @catch_exceptions(logger=logger)
    def deleteLoglevel(self, uiItems, *args):
        for itemName in uiItems:
            if type(uiItems[itemName]) == dict:
                for button in list(uiItems[itemName].keys()):
                    button.hide()
            else:
                uiItems[itemName].hide()
        del self.loglevels[self.loglevels.index(uiItems)]

    @catch_exceptions(logger=logger)
    def addLoglevel(self, *args):
        lastRowIndex = self.uiGridLayout_loglevelsTab.rowCount()

        uiLineEdit_fieldName = QtWidgets.QLineEdit()
        self.uiGridLayout_loglevelsTab.addWidget(uiLineEdit_fieldName, lastRowIndex, 0)
        uiLineEdit_query = QtWidgets.QLineEdit()
        self.uiGridLayout_loglevelsTab.addWidget(uiLineEdit_query, lastRowIndex, 1)

        buttons = self._createLoglevelColorButton(None) #get index of item in dict in dict
        for buttonIndex in range(len(buttons)):
            self.uiGridLayout_loglevelsTab.addWidget(list(buttons.keys())[buttonIndex], lastRowIndex, buttonIndex+2)

        delButton = QtWidgets.QPushButton("Del")
        self.uiGridLayout_loglevelsTab.addWidget(delButton, lastRowIndex, 5)

        uiItems = {
            "fieldName": uiLineEdit_fieldName,
            "query": uiLineEdit_query, 
            "buttons": buttons, 
            "delButton": delButton
        }
        self.loglevels.append(uiItems)
        delButton.clicked.connect(functools.partial(self.deleteLoglevel, uiItems))
        self.update()

    def _createLoglevelColorButton(self, colorName):
        buttons = {}
        if colorName != None:
            colorTuple = SettingsSingleton().getLoglevelCssColorTuple(colorName)
            rgbTuple = SettingsSingleton().getLoglevelColorTuple(colorName)
            for index in range(len(colorTuple)):
                button = QtWidgets.QPushButton(self.uiTab_color)
                if colorTuple[index] != None:
                    button.setText("rgb(%d, %d, %d)" % tuple(rgbTuple[index]))
                    logger.debug("rgbTuple: %s" % str(rgbTuple[index]))
                    button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index], sharedUiHelpers.getCssContrastColor(*rgbTuple[index])))
                else:
                    button.setText("Transparent")
                button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                button.clicked.connect(functools.partial(self._openLoglevelColorPicker, button))
                button.customContextMenuRequested.connect(functools.partial(self._delLoglevelColor, button))
                buttons[button] = rgbTuple[index]
        else:
            for index in range(2):
                button = QtWidgets.QPushButton("Transparent", self.uiTab_color)
                button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                button.clicked.connect(functools.partial(self._openLoglevelColorPicker, button))
                button.customContextMenuRequested.connect(functools.partial(self._delLoglevelColor, button))
                buttons[button] = None
        return buttons

    def _createColorButton(self, colorName):
        colorTuple = SettingsSingleton().getCssColorTuple(colorName)
        rgbTuple = SettingsSingleton().getColorTuple(colorName)
        buttons = []
        for index in range(len(colorTuple)):
            button = QtWidgets.QPushButton(self.uiTab_color)
            if colorTuple[index] != None:
                button.setText("rgb(%d, %d, %d)" % tuple(rgbTuple[index]))
                logger.debug("rgbTuple: %s" % str(rgbTuple[index]))
                button.setStyleSheet("background-color: %s; color: %s;" % (colorTuple[index], sharedUiHelpers.getCssContrastColor(*rgbTuple[index])))
            else:
                button.setText("Transparent")
            button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.clicked.connect(functools.partial(self._openColorPicker, colorName, index, button))
            button.customContextMenuRequested.connect(functools.partial(self._delColor, colorName, index, button))
            buttons.append(button)
        return buttons

    @catch_exceptions(logger=logger)
    def _openLoglevelColorPicker(self, button, *args):
        loglevelIndex = None
        for index in range(len(self.loglevels)):
            if button in self.loglevels[index]["buttons"]:
                color = self.loglevels[index]["buttons"][button]
                loglevelIndex = index
        if color != None:
            color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*color), parent=self)
        else:
            color = QtWidgets.QColorDialog.getColor(parent=self)

        if color.isValid():
            rgbColor = [color.red(), color.green(), color.blue()]
            self.loglevels[loglevelIndex]["buttons"][button] = rgbColor
            button.setText("rgb(%d, %d, %d)" % tuple(rgbColor))
            button.setStyleSheet("background-color: %s; color: %s;" % ("#{:02x}{:02x}{:02x}".format(*rgbColor), sharedUiHelpers.getCssContrastColor(*rgbColor)))

    @catch_exceptions(logger=logger)
    def _delLoglevelColor(self, button, *args):
        for index in range(len(self.loglevels)):
            if button in self.loglevels[index]["buttons"]:
                self.loglevels[index]["buttons"][button] = None
        button.setText("Transparent")
        button.setStyleSheet("")

    @catch_exceptions(logger=logger)
    def _restoreDefaults(self, *args):
        msgBox = QtWidgets.QMessageBox.question(
            self,
            "Monal Log Viewer | WARNING", 
            "Do you really want to reset all settings and close this app?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        def deleteSettings():
            os.remove(Paths.get_default_conf_filepath("profile.generic.json"))
            sys.exit()
        if msgBox == QtWidgets.QMessageBox.Yes:
            deleteSettings()
            