#!/usr/bin/python3

# file created at 25.06.2023

from storage import Rawlog
from PyQt5 import QtWidgets, uic, QtGui, QtCore, Qt
from PyQt5.QtWidgets import QStyle
import sys, os
from utils import catch_exceptions, Search, LOGLEVELS
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

        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearch)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

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
        self.uiTable_characteristics.setHorizontalHeaderLabels(["field", "value"])
        self.uiTable_characteristics.horizontalHeader().setSectionResizeMode(0, int(QtWidgets.QHeaderView.ResizeToContents))
        self.uiTable_characteristics.horizontalHeader().setSectionResizeMode(1, int(QtWidgets.QHeaderView.ResizeToContents))
        self.uiTable_characteristics.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft  | QtCore.Qt.Alignment(QtCore.Qt.TextWordWrap))
        selectedEntry = self.rawlog[self.uiWidget_listView.selectedIndexes()[0].row()].get('data')
        self.uiTable_characteristics.setRowCount(len(selectedEntry)+1)

        row = 1
        for key, value in selectedEntry.items():
            self.uiTable_characteristics.setItem(row,0, QtWidgets.QTableWidgetItem(key))
            self.uiTable_characteristics.setItem(row,1, QtWidgets.QTableWidgetItem(str(value)))
            row += 1
        
        self.uiTable_characteristics.show()

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
    def setComboboxStatusColor(self):
        status = self.search.getStatus()
        if status == self.search.EOF_REACHED:
            self.uiCombobox_searchInput.setStyleSheet('background-color: #0096FF') # blue
        if status == self.search.QUERY_ERROR:
            self.uiCombobox_searchInput.setStyleSheet('background-color: #FF2400') # red
        if status == self.search.QUERY_OK:
            self.uiCombobox_searchInput.setStyleSheet('background-color: #50C878') # green
        if status == self.search.QUERY_EMPTY:
            self.uiCombobox_searchInput.setStyleSheet('background-color: #FFD700') # yellow

    def updateComboboxHistory(self, query):
        if query.strip() == "":
            return

        if self.uiCombobox_searchInput.findText(query) == -1:
            self.uiCombobox_searchInput.insertItem(0, query)
            return
        
        self.uiCombobox_searchInput.removeItem(self.uiCombobox_searchInput.findText(query))
        self.uiCombobox_searchInput.insertItem(0, query)
        self.uiCombobox_searchInput.setCurrentText(query)

    def searchNext(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.next)

    def searchPrevious(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.previous)

    def _search(self, func):
        # bind self using our (newly created) self.search
        result = self._prepareSearch()
        if result == None:
            result = func(self.search)
        logger.info("SEARCH RESULT: %s" % str(result))
        if result != None:
            self.uiWidget_listView.setCurrentRow(result)
        self.setComboboxStatusColor()

    def _prepareSearch(self):
        query = self.uiCombobox_searchInput.currentText()
        if self.search != None:
            if self.search.getQuery() == query:
                return None
        
        startIndex = 0
        if len(self.uiWidget_listView.selectedIndexes()) > 0:
            startIndex = self.uiWidget_listView.selectedIndexes()[0].row()

        self.search = Search(self.rawlog, query, startIndex)
        self.updateComboboxHistory(query)
        return self.search.getCurrentResult()
    
    @catch_exceptions(logger=logger)
    def loglineSelectionChanged(self, *args):
        if self.search != None and len(self.uiWidget_listView.selectedIndexes()) > 0:
            self.search.setStartIndex(self.uiWidget_listView.selectedIndexes()[0].row())

    @catch_exceptions(logger=logger)
    def hideSearch(self):
        self.uiFrame_search.hide()
        self.search = None
            
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