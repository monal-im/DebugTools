#!/usr/bin/python3

# file created at 25.06.2023

from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os
import textwrap

from storage import Rawlog, SettingsSingleton
from ui.utils import Completer, MagicLineEdit, Statusbar
from utils import catch_exceptions, Search, QueryStatus, matchQuery, paths
from utils.constants import LOGLEVELS
from .preferences_dialog import PreferencesDialog

import logging
logger = logging.getLogger(__name__)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi(paths.get_ui_filepath("main_window.ui"), self)
        self.setWindowIcon(QtGui.QIcon(paths.get_art_filepath("monal_log_viewer.png")))
        SettingsSingleton().loadDimensions(self)

        self.rawlog = Rawlog()
        self.search = None
        self.statusbar = Statusbar(self.uistatusbar_state)

        self.uiButton_previous.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowBack")))
        self.uiButton_previous.clicked.connect(self.searchPrevious)
        self.uiButton_next.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowForward")))
        self.uiButton_next.clicked.connect(self.searchNext)

        self.uiAction_open.triggered.connect(self.openLogFile)
        self.uiAction_close.triggered.connect(self.closeFile)
        self.uiAction_quit.triggered.connect(self.quit)
        self.uiAction_preferences.triggered.connect(self.preferences)
        self.uiAction_search.triggered.connect(self.openSearchwidget)
        self.uiAction_export.triggered.connect(self.export)

        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiWidget_listView.itemSelectionChanged.connect(self.loglineSelectionChanged)
        self.uiTable_characteristics.hide()
        self.uiFrame_search.hide()

        self.uiTable_characteristics.doubleClicked.connect(self.pasteDetailItem)
        MagicLineEdit(self.uiCombobox_searchInput)
        MagicLineEdit(self.uiCombobox_filterInput)

        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearch)
        self.uiCombobox_searchInput.clear()
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)
        self.uiCombobox_searchInput.addItems(SettingsSingleton().getComboboxHistory(self.uiCombobox_searchInput))
        self.uiCombobox_searchInput.lineEdit().setText("")

        self.uiCombobox_filterInput.clear()
        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)
        self.uiCombobox_filterInput.addItems(SettingsSingleton().getComboboxHistory(self.uiCombobox_filterInput))
        self.uiCombobox_filterInput.lineEdit().setText("")

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self).activated.connect(self.setStack)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self).activated.connect(self.getStack)
        self.stack = []

        self.currentDetailIndex = None
        self.currentFilterQuery = None

        #set enable false!!!
    
    def quit(self):
        SettingsSingleton().storeSplitterDimension(self.uiSplitter_inspectLine)
        sys.exit()

    def closeEvent(self, event):
        SettingsSingleton().storeSplitterDimension(self.uiSplitter_inspectLine)
        sys.exit()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        SettingsSingleton().storeDimension(self)

    def export(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "MLV | Export file",
                                                            "", "Textfile (*.txt)")
            if check:
                status = self.rawlog.export_file(file, custom_store_callback = lambda entry: entry["data"] if not entry["uiItem"].isHidden() else None)
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Export was successful"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Export was unsuccessful"))

    def setCompleter(self, combobox):
        wordlist = self.rawlog.getCompleterList(lambda entry: entry["data"])
        wordlist += ["True", "False", "true", "false", "__index", "__rawlog"] + list(LOGLEVELS.keys())

        completer = Completer(wordlist, self)
        completer.setCompletionMode(Completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combobox.setCompleter(completer)

    @catch_exceptions(logger=logger)
    def openLogFile(self, *args):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Monal Log Viewer | Open Logfile",
                                                            "", "Raw Log (*.rawlog)")
        if check:
            self.statusbar.setText("Loading File: '%s'..." % os.path.basename(file))

            def loader(entry):
                fg, bg = self.itemColorFactory(entry["flag"])

                item_with_color = "\n".join([textwrap.fill(line, SettingsSingleton()["staticLineWrap"],
                    expand_tabs=False,
                    replace_whitespace=False,
                    drop_whitespace=False,
                    break_long_words=True,
                    break_on_hyphens=True,
                    max_lines=None
                ) if len(line) > SettingsSingleton()["staticLineWrap"] else line for line in self.getLogMessage(entry).strip().splitlines(keepends=False)])

                item_with_color = QtWidgets.QListWidgetItem(item_with_color)
                item_with_color.setForeground(fg)
                if bg != None:
                    item_with_color.setBackground(bg)
                return {"uiItem": item_with_color, "data": entry}

            progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: "+ file)
            self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader)

            self.statusbar.setText("Rendering File: '%s'..." % file)

            itemListsize = len(self.rawlog)
            for index in range(itemListsize):
                self.uiWidget_listView.addItem(self.rawlog[index]["uiItem"])
                if "__warning" in self.rawlog[index]["data"] and self.rawlog[index]["data"]["__warning"] == True:
                    self.QtWidgets.QMessageBox.warning(self, "File corruption detected", self.getLogMessage(self.rawlog[index]["data"]))

            self.file = file
            self.statusbar.showDynamicText(str("Done ✓ | file opened: " + os.path.basename(file)))

            self.setCompleter(self.uiCombobox_filterInput)
            self.setCompleter(self.uiCombobox_searchInput)

            self._updateStatusbar()
            
    def itemColorFactory(self, flag):
        return tuple(SettingsSingleton().getQColorTuple({v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}[flag]))
    
    def getLogMessage(self, entry):
        loc = {}
        keywords = {value: entry[value] for value in entry.keys()}
        try:
            exec(SettingsSingleton().getCurrentFormatter(), keywords, loc)
            return str(loc['retval'])
        except:
            return "Code execution failed, file couldn't be opened! ✗"
            
    @catch_exceptions(logger=logger)
    def inspectLine(self, *args):
        self.uiTable_characteristics.setHorizontalHeaderLabels(["path", "value"])
        self.uiTable_characteristics.horizontalHeader().setSectionResizeMode(0, int(QtWidgets.QHeaderView.ResizeToContents))
        self.uiTable_characteristics.horizontalHeader().setSectionResizeMode(1, int(QtWidgets.QHeaderView.ResizeToContents))
        self.uiTable_characteristics.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft  | QtCore.Qt.Alignment(QtCore.Qt.TextWordWrap))
        selectedEntry = self.rawlog[self.uiWidget_listView.selectedIndexes()[0].row()].get('data')
        self.uiTable_characteristics.setRowCount(len(selectedEntry)+1)

        def splitter(dictionary, path=[]):
            retval = []
            for key, value in dictionary.items():
                path.append(key)
                if type(value) == dict:
                    retval += splitter(value, path)
                else:
                    retval.append({
                        "path": path[0] + "".join(map(lambda value: "[%s]" % self.pythonize(value), path[1:])),
                        "value": self.pythonize(value)
                    })
                path.pop(-1)
            return retval

        row = 1
        for index in splitter(selectedEntry):
            self.uiTable_characteristics.setItem(row,0, QtWidgets.QTableWidgetItem(index['path']))
            self.uiTable_characteristics.setItem(row,1, QtWidgets.QTableWidgetItem(index['value']))
            row += 1
        
        self.uiTable_characteristics.show()
        SettingsSingleton().loadSplitterDimensions(self.uiSplitter_inspectLine)
        self.currentDetailIndex = self.uiWidget_listView.selectedIndexes()[0].row()

    @catch_exceptions(logger=logger)
    def focusChangedEvent(self, oldWidget, newWidget):
        if type(oldWidget) == QtWidgets.QComboBox:
            self.selectedCombobox = oldWidget

    def pythonize(self, value):
        if type(value) == int or type(value) == float or type(value) == bool:
            return str(value)
        return "'%s'" % str(value)
    
    @catch_exceptions(logger=logger)
    def pasteDetailItem(self, *args):
        self.selectedCombobox.setFocus()
        self.selectedCombobox.lineEdit().insert(self.uiTable_characteristics.currentItem().text())
            
    @catch_exceptions(logger=logger)
    def closeFile(self, *args):
        self.uiWidget_listView.clear()
        self.uiTable_characteristics.hide()
        self.uiTable_characteristics.hide()
        self.uiFrame_search.hide()

    @catch_exceptions(logger=logger)
    def preferences(self, *args):
        self.preferencesDialog = PreferencesDialog()
        self.preferencesDialog.show()

    @catch_exceptions(logger=logger)
    def openSearchwidget(self, *args):
        self.uiFrame_search.show()
        self.uiCombobox_searchInput.setFocus()  

    @catch_exceptions(logger=logger)
    def setComboboxStatusColor(self, combobox, status):
        table = {
            QueryStatus.EOF_REACHED: "background-color: %s" % SettingsSingleton().getCssColor("combobox-eof_reached"),
            QueryStatus.QUERY_ERROR: "background-color: %s" % SettingsSingleton().getCssColor("combobox-query_error"),
            QueryStatus.QUERY_OK: "background-color: %s" % SettingsSingleton().getCssColor("combobox-query_ok"),
            QueryStatus.QUERY_EMPTY: "background-color: %s" % SettingsSingleton().getCssColor("combobox-query_empty")
        }
        combobox.setStyleSheet(table[status])

    def searchNext(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.next)

    def searchPrevious(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.previous)

    def _search(self, func):
        result = self._prepareSearch()  # create search instance (to be bound below)
        if result == None:
            result = func(self.search)  # bind self using our (newly created) self.search

        logger.info("SEARCH RESULT: %s" % str(result))
        if result != None:
            self.uiWidget_listView.setCurrentRow(result)
        self.setComboboxStatusColor(self.uiCombobox_searchInput, self.search.getStatus())

        self._updateStatusbar()

    def _prepareSearch(self):
        query = self.uiCombobox_searchInput.currentText()
        if self.search != None:
            if self.search.getQuery() == query:
                return None
        
        startIndex = 0
        if len(self.uiWidget_listView.selectedIndexes()) > 0:
            startIndex = self.uiWidget_listView.selectedIndexes()[0].row()

        self.search = Search(self.rawlog, query, startIndex)
        self.updateComboboxHistory(query, self.uiCombobox_searchInput)
        SettingsSingleton().setComboboxHistory(self.uiCombobox_searchInput, [self.uiCombobox_searchInput.itemText(i) for i in range(self.uiCombobox_filterInput.count())])

        return self.search.getCurrentResult()
    
    @catch_exceptions(logger=logger)
    def loglineSelectionChanged(self, *args):
        if self.search != None and len(self.uiWidget_listView.selectedIndexes()) > 0:
            self.search.setStartIndex(self.uiWidget_listView.selectedIndexes()[0].row())

    @catch_exceptions(logger=logger)
    def hideSearch(self):
        self.uiFrame_search.hide()
        self.search = None

    def clearFilter(self):
        self.uiCombobox_filterInput.setCurrentText("")
        self.uiCombobox_filterInput.setStyleSheet('')

        for index in range(len(self.rawlog)):
            self.rawlog[index]["uiItem"].setHidden(False)

        self.currentFilterQuery = None
        self.statusbar.showDynamicText("Filter cleared")
        self._updateStatusbar()

    def filter(self):
        query = self.uiCombobox_filterInput.currentText()

        result = matchQuery(query, self.rawlog)
        self.setComboboxStatusColor(self.uiCombobox_filterInput, result["status"])
        self.updateComboboxHistory(query, self.uiCombobox_filterInput)

        for rawlogPosition in range(len(self.rawlog)):
            self.rawlog[rawlogPosition]["uiItem"].setHidden(rawlogPosition not in result["entries"])

        SettingsSingleton().setComboboxHistory(self.uiCombobox_filterInput, [self.uiCombobox_filterInput.itemText(i) for i in range(self.uiCombobox_filterInput.count())])
        self.currentFilterQuery = query

        self._updateStatusbar()

    def updateComboboxHistory(self, query, combobox):
        if query.strip() == "":
            return

        if combobox.findText(query) != -1:
            combobox.removeItem(combobox.findText(query))
        combobox.insertItem(0, query)
        combobox.setCurrentText(query)

    @catch_exceptions(logger=logger)
    def progressDialog(self, title, label):
        progressBar = QtWidgets.QProgressDialog(label, 'OK', 0, 100, self)
        progressBar.setWindowTitle(title)
        progressBar.setGeometry(200, 200, 650, 100)
        progressBar.setCancelButton(None)
        progressBar.setAutoClose(True)
        progressBar.setValue(0)

        # we need to do this because we can't write primitive datatypes from within our closure
        oldpercentage = {"value": 0}

        def update_progressbar(readsize, filesize):
            currentpercentage = int(readsize/filesize*100)
            if currentpercentage != oldpercentage["value"]:
                progressBar.setValue(currentpercentage)
                QtWidgets.QApplication.processEvents()
            oldpercentage["value"] = currentpercentage

        progressBar.show()
        return (progressBar, update_progressbar)
    
    def setStack(self):
        selectedLine = None
        if self.uiWidget_listView.selectedIndexes():
            selectedLine = self.uiWidget_listView.selectedIndexes()[0].row()

        state = {
            "selectedLine": selectedLine, 
            "detail": {
                "isOpen": not self.uiTable_characteristics.isHidden(), 
                "size": self.uiTable_characteristics.height(), 
                "currentDetailIndex": self.currentDetailIndex
            }, 
            "search": {
                "isOpen": not self.uiFrame_search.isHidden(), 
                "instance": self.search, 
                "currentText": self.uiCombobox_searchInput.currentText(), 
            },
            "filter": {
                "currentFilterQuery": self.currentFilterQuery, 
                "currentText": self.uiCombobox_filterInput.currentText()
            }
        }
        self.stack.append(state)
        self.statusbar.showDynamicText("State saved ✓")

    def getStack(self):
        if len(self.stack) < 1:
            self.statusbar.showDynamicText("Unable to load state ✗")
            return
        
        stack = self.stack.pop()

        #unpacking details
        if stack["detail"]["isOpen"]:
            self.uiWidget_listView.setCurrentRow(stack["detail"]["currentDetailIndex"])
            self.inspectLine()
            self.uiTable_characteristics.setFixedHeight(stack["detail"]["size"])
            if stack["detail"]["size"] == 0:
                self.uiTable_characteristics.setFixedHeight(800)

        #unpacking search
        if stack["search"]["isOpen"]:
            self.uiCombobox_searchInput.setCurrentText(stack["search"]["currentText"])
            if stack["search"]["active"]:
                self.uiWidget_listView.setCurrentRow(stack["search"]["currentPosition"])
                self.searchNext()

        #unpacking filter
        self.uiCombobox_filterInput.setCurrentText(stack["filter"]["currentText"])
        if stack["filter"]["active"]:
            self.filter()

        self.statusbar.showDynamicText("State loaded ✓")

    def _updateStatusbar(self):
        text = ""

        if len(self.rawlog) > 0:
            text += "%s:" % os.path.basename(self.file)

        if self.currentFilterQuery != None:
            text += " %d/%d" % (
                len([item for item in self.rawlog if not item["uiItem"].isHidden()]),
                len(self.rawlog)
            )
        else:
            text += " %d" % len(self.rawlog)
            
        if self.search != None:
            if len(self.search) != 0:
                text += ", search: %d/%d" % (self.search.getPosition(), len(self.search))
            else:
                text += ", search: no result!"

        self.statusbar.setText(text)