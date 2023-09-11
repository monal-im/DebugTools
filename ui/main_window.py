#!/usr/bin/python3

# file created at 25.06.2023

from storage import Rawlog, SettingsSingleton
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os
from utils import catch_exceptions, Search, LOGLEVELS, QueryStatus, matchQuery, MagicLineEdit
from ui_utils import Completer
import logging

logger = logging.getLogger(__name__)

class Main_Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi(os.path.join(os.path.dirname(sys.argv[0]), "ui/main_window.ui"), self)
        self.setWindowTitle("Monal Log Viewer")
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(sys.argv[0]), "monal_log_viewer.png")))
        self.resize(1400, 840)

        self.rawlog = Rawlog()
        self.search = None

        self.uiButton_previous.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowBack")))
        self.uiButton_previous.clicked.connect(self.searchPrevious)
        self.uiButton_next.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowForward")))
        self.uiButton_next.clicked.connect(self.searchNext)

        self.uiAction_open.triggered.connect(self.openLogFile)
        self.uiAction_close.triggered.connect(self.closeFile)
        self.uiAction_quit.triggered.connect(self.quit)
        self.uiAction_preferences.triggered.connect(self.preferences)
        self.uiAction_search.triggered.connect(self.openSearchwidget)

        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiWidget_listView.itemSelectionChanged.connect(self.loglineSelectionChanged)
        self.uiTable_characteristics.hide()
        self.uiFrame_search.hide()

        self.uiTable_characteristics.doubleClicked.connect(self.insertItem)
        MagicLineEdit(self.uiCombobox_searchInput)
        MagicLineEdit(self.uiCombobox_filterInput)

        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearch)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self).activated.connect(self.setStack)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self).activated.connect(self.getStack)
        self.stack = []

        self.currentDetailIndex = None
        self.currentFilterQuery = None


        #----------------WIP----------------#
        SettingsSingleton()

        #set enable false!!!

    def setCompleter(self, combobox):
        wordlist = self.rawlog.getCompleterList(lambda entry: entry["data"])
        wordlist += ["True", "False", "true", "false", "__index", "__rawlog"] + list(LOGLEVELS.keys())

        completer = Completer(wordlist, self)
        completer.setCompletionMode(Completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combobox.setCompleter(completer)
    
    def quit(self):
        sys.exit()

    @catch_exceptions(logger=logger)
    def openLogFile(self, *args):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "MLV | Open Logfile",
                                                            "", "Raw Log (*.rawlog)")
        if check:
            self.uistatusbar_state.showMessage("Extracting File...")

            def loader(entry):
                fg, bg = self.itemColorFactory(entry["flag"])
                item_with_color = QtWidgets.QListWidgetItem(entry["formattedMessage"])
                item_with_color.setForeground(fg)
                if bg != None:
                    item_with_color.setBackground(bg)
                return {"uiItem": item_with_color, "data": entry}

            progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: "+ file)
            self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader)

            self.uistatusbar_state.showMessage("Rendering File...")

            itemListsize = len(self.rawlog)
            for index in range(itemListsize):
                self.uiWidget_listView.addItem(self.rawlog[index]["uiItem"])
                if "__warning" in self.rawlog[index]["data"] and self.rawlog[index]["data"]["__warning"] == True:
                    self.QtWidgets.QMessageBox.warning(self, "File corruption detected", self.rawlog[index]["data"]["formattedMessage"])

            self.uistatusbar_state.showMessage(str("Done ✓ | file opened: " + file))

            self.setCompleter(self.uiCombobox_filterInput)
            self.setCompleter(self.uiCombobox_searchInput)
            
    def itemColorFactory(self, flag):
        if int(flag) == LOGLEVELS['ERROR']:  # ERROR
            return (QtGui.QColor(255, 0, 0),  QtGui.QColor(0, 0, 0))
        elif int(flag) == LOGLEVELS['WARNING']:  # WARNING
            return (QtGui.QColor(0, 255, 255),  QtGui.QColor(0, 0, 0))
        elif int(flag) == LOGLEVELS['INFO']:  # INFO
            return (QtGui.QColor(0, 0, 255), None)
        elif int(flag) == LOGLEVELS['DEBUG']:  # DEBUG
            return (QtGui.QColor(0, 255, 0), None)
        elif int(flag) == LOGLEVELS['VERBOSE']:  # VERBOSE
            return (QtGui.QColor(128, 128, 128), None)
        elif int(flag) == LOGLEVELS['STATUS']: # STATUS
            return (QtGui.QColor(0, 0, 0), QtGui.QColor(255, 0, 0))
        else:
            return (QtGui.QColor(0, 0, 0), QtGui.QColor(255, 122, 0))

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
    def insertItem(self, *args):
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
        pass

    @catch_exceptions(logger=logger)
    def openSearchwidget(self, *args):
        self.uiFrame_search.show()
        self.uiCombobox_searchInput.setFocus()  

    @catch_exceptions(logger=logger)
    def setComboboxStatusColor(self, combobox, status):
        if status == QueryStatus.EOF_REACHED:
            combobox.setStyleSheet('background-color: #0096FF') # blue
        if status == QueryStatus.QUERY_ERROR:
            combobox.setStyleSheet('background-color: #FF2400') # red
        if status == QueryStatus.QUERY_OK:
            combobox.setStyleSheet('background-color: #50C878') # green
        if status == QueryStatus.QUERY_EMPTY:
            combobox.setStyleSheet('background-color: #FFD700') # yellow

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

        self.uistatusbar_state.showMessage("You are currently in line "+str(result))
        logger.info("SEARCH RESULT: %s" % str(result))
        if result != None:
            self.uiWidget_listView.setCurrentRow(result)
        self.setComboboxStatusColor(self.uiCombobox_searchInput, self.search.getStatus())

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
        self.uistatusbar_state.showMessage("Cleared")
        self.uiCombobox_filterInput.setStyleSheet('') # grey

        for index in range(len(self.rawlog)):
            self.rawlog[index]["uiItem"].setHidden(False)
        
        self.currentFilterQuery = None

    def filter(self):
        query = self.uiCombobox_filterInput.currentText()

        result = matchQuery(query, self.rawlog)
        self.uistatusbar_state.showMessage("There are "+str(len(result["entries"]))+" results with your query!")
        self.setComboboxStatusColor(self.uiCombobox_filterInput, result["status"])
        self.updateComboboxHistory(query, self.uiCombobox_filterInput)

        for rawlogPosition in range(len(self.rawlog)):
            self.rawlog[rawlogPosition]["uiItem"].setHidden(rawlogPosition not in result["entries"])

        self.Settings.setcomboboxHistory(self.uiCombobox_filterInput)
        self.currentFilterQuery = query

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
        self.uistatusbar_state.showMessage("State saved ✓")

    def getStack(self):
        if len(self.stack) < 1:
            self.uistatusbar_state.showMessage("State was unable to load ✗")
            return
        
        stack = self.stack.pop()
        print(stack["detail"]["size"])

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

        self.uistatusbar_state.showMessage("State loaded ✓")