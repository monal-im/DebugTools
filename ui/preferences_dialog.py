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
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Discard).clicked.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.accept)

    def accept(self, *args):
        for colorName in self.colors:
            SettingsSingleton().setQColorTuple(colorName, self.colors[colorName])
        for comboboxName in self.history:
            data = [self.history[comboboxName].item(item).text() for item in range(self.history[comboboxName].count())]
            SettingsSingleton().setComboboxHistoryByName(comboboxName, data)
        for miscName in self.misc:
            SettingsSingleton()[miscName] = self._getMiscWidgetValue(self.misc[miscName])
        SettingsSingleton().clearAllFormatters()
        for formatterNameLineEdit in self.formatter:
            SettingsSingleton().setFormatter(formatterNameLineEdit.text(), self.formatter[formatterNameLineEdit].toPlainText())
        super().accept()

    def _getMiscWidgetValue(self, widget):
        if isinstance(widget, QtWidgets.QSpinBox):
            return widget.value()
        if isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()
        if isinstance(widget, QtWidgets.QComboBox):
            return widget.currentText()
        if isinstance(widget, QtWidgets.QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QtWidgets.QPushButton):
            return SettingsSingleton().getFontParameterList(self.font)

    def _createUiTab_color(self):
        colorNames = SettingsSingleton().getColorNames()
        for colorIndex in range(len(colorNames)):
            self.uiGridLayout_colorTab.addWidget(QtWidgets.QLabel(colorNames[colorIndex], self), colorIndex, 0)
            buttons = self._createColorButton(colorNames[colorIndex])

            for buttonIndex in range(len(buttons)):
                self.uiGridLayout_colorTab.addWidget(buttons[buttonIndex], colorIndex, buttonIndex+1)
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
                
    def _createMiscWidget(self, value, miscName):
        if type(value) == int:
            widget = QtWidgets.QSpinBox()
            widget.setMaximum(1024)
            widget.setValue(value)
        elif type(value) == int:
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(1)
            widget.setSingleStep(0.1)
            widget.setValue(value)
        elif type(value) == str and miscName != "currentFormatter" and miscName != "font":
            widget = QtWidgets.QLineEdit()
            widget.setText(value)
        elif type(value) == str and miscName == "currentFormatter":
            widget = QtWidgets.QComboBox()
            widget.addItems(SettingsSingleton().getFormatterNames())
            widget.setCurrentText(value)
            self.currrentFormatter = widget
        elif type(value) == str and miscName == "font":
            widget = QtWidgets.QPushButton()
            self.font = SettingsSingleton().getQFont(value)
            displayValue = QtGui.QFontInfo(SettingsSingleton().getQFont(value))
            widget.setText("%s, %s" % (displayValue.family(), str(displayValue.pointSize())))
            widget.setFont(QtGui.QFont(QtGui.QFont.family(self.font), QtGui.QFont.pointSize(self.font)))
            widget.clicked.connect(functools.partial(self._changeFont, widget))
        elif type(value) == bool:
            widget = QtWidgets.QCheckBox()
            widget.setChecked(value)
        else:
            raise RuntimeError("Misc value type not implemented yet: %s" % str(type(value)))
        return widget
    
    def _changeFont(self, widget):
        fontDialog = QtWidgets.QFontDialog()
        font, valid = fontDialog.getFont(QtGui.QFont(QtGui.QFont.family(self.font), QtGui.QFont.pointSize(self.font)))
        if valid:
            self.font = font
            displayValue = QtGui.QFontInfo(font)
            widget.setText("%s, %s" % (displayValue.family(), str(displayValue.pointSize())))
            widget.setFont(QtGui.QFont(font.family(), int(font.pointSize())))

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

    def _deleteFormat(self, lineEdit, code, button):
        if len(self.formatter) >= 2:
            del self.formatter[lineEdit]
            self.currrentFormatter.removeItem(self.currrentFormatter.findText(lineEdit.text()))
            lineEdit.hide()
            code.hide()
            button.hide()

    def _addFormatter(self, lineEdit, code, button):
        if lineEdit.text() != "" and code.toPlainText() != "":
            self.currrentFormatter.addItem(lineEdit.text())
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
        button = QtWidgets.QPushButton()
        horizonalLayout = QtWidgets.QHBoxLayout()
        verticalLayout = QtWidgets.QVBoxLayout()

        verticalLayout.setAlignment(QtCore.Qt.AlignTop)

        button.setText("Create")
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

    @catch_exceptions(logger=logger)
    def _restoreDefaults(self, *args):
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
        msgBox.show()