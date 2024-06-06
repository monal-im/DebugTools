from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os, functools

from LogViewer.storage import SettingsSingleton
from LogViewer.utils import Search, AbortSearch, QueryStatus, matchQuery
import LogViewer.utils.helpers as helpers
from .utils import Completer, MagicLineEdit, Statusbar, RawlogModel, LazyItemModel
from .preferences_dialog import PreferencesDialog
from shared.storage import Rawlog
from shared.ui.utils import UiAutoloader
from shared.utils import catch_exceptions
import shared.ui.utils.helpers as sharedUiHelpers
from shared.utils.constants import LOGLEVELS
                
import logging
logger = logging.getLogger(__name__)

@UiAutoloader
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        SettingsSingleton().loadDimensions(self)
        self.rawlog = Rawlog()
        self.file = None
        self.search = None
        self.statusbar = Statusbar(self.uiStatusbar_main, self.uiMenuBar_main)
        self.currentFilterQuery = None
        self.stack = []
        self.selectedCombobox = self.uiCombobox_filterInput

        self.queryStatus2colorMapping = {
            QueryStatus.EOF_REACHED:    SettingsSingleton().getColor("combobox-eof_reached"),
            QueryStatus.QUERY_ERROR:    SettingsSingleton().getColor("combobox-query_error"),
            QueryStatus.QUERY_OK:       SettingsSingleton().getColor("combobox-query_ok"),
            QueryStatus.QUERY_EMPTY:    SettingsSingleton().getColor("combobox-query_empty"),
        }

        self.toggleUiItems()

        QtWidgets.QShortcut(QtGui.QKeySequence("CTRL+C"), self).activated.connect(self.copyToClipboard)

        self.uiButton_previous.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowBack")))
        self.uiButton_previous.clicked.connect(self.searchPrevious)
        self.uiButton_next.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowForward")))
        self.uiButton_next.clicked.connect(self.searchNext)

        self.uiAction_open.triggered.connect(self.openFileBrowser)
        self.uiAction_close.triggered.connect(self.closeFile)
        self.uiAction_quit.triggered.connect(self.quit)
        self.uiAction_preferences.triggered.connect(self.preferences)
        self.uiAction_search.triggered.connect(self.openSearchWidget)
        self.uiAction_export.triggered.connect(self.export)
        self.uiAction_save.triggered.connect(self.save)
        self.uiAction_inspectLine.triggered.connect(self.inspectLine)
        self.uiAction_about.triggered.connect(sharedUiHelpers.action_about)
        self.uiAction_pushStack.triggered.connect(self.pushStack)
        self.uiAction_popStack.triggered.connect(self.popStack)
        self.uiAction_goToRow.triggered.connect(self.openGoToRowWidget)
        self.uiAction_firstRow.triggered.connect(self.goToFirstRow)
        self.uiAction_lastRow.triggered.connect(self.goToLastRow)
        self.uiAction_firstRowInViewport.triggered.connect(self.goToFirstRowInViewport)
        self.uiAction_lastRowInViewport.triggered.connect(self.goToLastRowInViewport)

        self.uiWidget_listView.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiWidget_listView.clicked.connect(self.listViewClicked)
        self.uiFrame_search.hide()

        self.uiButton_goToRow.setIcon(self.style().standardIcon(getattr(QStyle, "SP_CommandLink")))
        self.uiButton_goToRow.clicked.connect(self.goToRow)
        #self.uiSpinBox_goToRow.valueChanged.connect(self.goToRow)
        self.uiFrame_goToRow.hide()

        self.uiTable_characteristics.doubleClicked.connect(self.pasteDetailItem)
        MagicLineEdit(self.uiCombobox_searchInput)
        MagicLineEdit(self.uiCombobox_filterInput)

        self.uiCombobox_searchInput.currentTextChanged.connect(self.uiCombobox_inputChanged)
        self.uiCombobox_filterInput.currentTextChanged.connect(self.uiCombobox_inputChanged)

        self.loadComboboxHistory(self.uiCombobox_searchInput)
        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearchOrGoto)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

        self.loadComboboxHistory(self.uiCombobox_filterInput)
        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)
        self.uiSplitter_inspectLine.splitterMoved.connect(functools.partial(SettingsSingleton().storeState, self.uiSplitter_inspectLine))
        SettingsSingleton().loadState(self.uiSplitter_inspectLine)

        self.hideInspectLine()

    @catch_exceptions(logger=logger)
    def quit(self):
        sys.exit()

    @catch_exceptions(logger=logger)
    def closeEvent(self, event):
        sys.exit()

    @catch_exceptions(logger=logger)
    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        SettingsSingleton().storeDimension(self)
    
    def toggleUiItems(self):
        self.uiAction_close.setEnabled(self.file != None)
        self.uiAction_quit.setEnabled(True)
        self.uiAction_open.setEnabled(True)
        self.uiAction_inspectLine.setEnabled(self.file != None)
        self.uiAction_preferences.setEnabled(True)
        self.uiAction_export.setEnabled(self.file != None)
        self.uiAction_pushStack.setEnabled(self.file != None)
        self.uiAction_popStack.setEnabled(self.file != None and len(self.stack) != 0)
        self.uiAction_search.setEnabled(self.file != None)
        self.uiAction_save.setEnabled(self.file != None)
        self.uiAction_goToRow.setEnabled(self.file != None)
        self.uiAction_firstRow.setEnabled(self.file != None)
        self.uiAction_lastRow.setEnabled(self.file != None)
        self.uiButton_previous.setEnabled(self.file != None and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_next.setEnabled(self.file != None and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_filterClear.setEnabled(self.file != None and self.currentFilterQuery != None)
        self.uiButton_goToRow.setEnabled(self.file != None)
        self.uiSpinBox_goToRow.setEnabled(self.file != None)
        self.uiCombobox_searchInput.setEnabled(self.file != None)
        self.uiCombobox_filterInput.setEnabled(self.file != None)
        self.uiAction_lastRowInViewport.setEnabled(self.file != None)
        self.uiAction_firstRowInViewport.setEnabled(self.file != None)

    def export(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this text logfile", SettingsSingleton().getLastPath(), "Compressed logfile (*.log.gz)(*.log.gz);;Logfile (*.log)(*.log);;All files (*)")
            if check:
                SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
                formatter = self.createFormatter()
                status = self.rawlog.export_file(file, custom_store_callback = lambda entry: entry["data"] if not self.uiWidget_listView.isRowHidden(self.rawlogModel.indexFromItem(entry["uiItem"]).row()) else None, formatter = lambda entry: self.createFormatterText(formatter, entry))
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Log export was successful"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not export log"))

    def save(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this rawlog logfile", SettingsSingleton().getLastPath(), "Compressed Monal rawlog (*.rawlog.gz)(*.rawlog.gz);;Monal rawlog (*.rawlog)(*.rawlog);;All files (*)")
            if check:
                SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
                status = self.rawlog.store_file(file, custom_store_callback = lambda entry: entry["data"] if not self.uiWidget_listView.isRowHidden(self.rawlogModel.indexFromItem(entry["uiItem"]).row()) else None)
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Rawlog saved successfully"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not save warlow"))   

    @catch_exceptions(logger=logger)
    def openFileBrowser(self, *args):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Open rawlog logfile", SettingsSingleton().getLastPath(), "Monal rawlog (*.rawlog.gz *.rawlog)(*.rawlog.gz *.rawlog);;All files (*)")
        if check:
            SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
            self.openLogFile(file)

    def openLogFile(self, file):
        self.closeFile()
        
        self.statusbar.setText("Loading File: '%s'..." % os.path.basename(file))
        self.rawlog = Rawlog()
        self.search = None
        
        def loader(entry):
            # directly warn about file corruptions when they happen to allow the user to abort the loading process
            # using the cancel button in the progressbar window
            if "__warning" in entry and entry["__warning"] == True:
                QtWidgets.QMessageBox.warning(self, "File corruption detected", entry["message"])
            
            return {"data": entry, "visible": True}
        
        progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: %s" % os.path.basename(file), True)
        try:
            # don't pretend something was loaded if the loading was aborted
            if self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader) != True:
                self.closeFile()        # reset our ui to a sane state
                progressbar.hide()
                self.statusbar.setText("")
                return
        except Exception as error:
            progressbar.hide()
            QtWidgets.QMessageBox.critical(
                self,
                "Monal Log Viewer | ERROR", 
                "Exception in query:\n%s: %s" % (str(type(error).__name__), str(error)),
                QtWidgets.QMessageBox.Ok
            )
            return
        
        self.rawlogModel = RawlogModel(self.rawlog, self.uiWidget_listView)
        self.lazyItemModel = LazyItemModel(self.rawlogModel)
        self.uiWidget_listView.setModel(self.lazyItemModel)
        #self.lazyItemModel.setVisible(0, 2)
        #self.lazyItemModel.setVisible(8, 10)
        #self.lazyItemModel.setVisible(50, 100)
        #self.lazyItemModel.setVisible(100, 200)
        self.lazyItemModel.setVisible(0, 100)

        progressbar.hide()

        if self.file != file:
            self.stack.clear()

        self.file = file

        # abort our current search if we have an active search but no search query in our input box
        if len(self.uiCombobox_searchInput.currentText().strip()) != 0:
            self.search = None
        
        if self.search != None:
            # set self.search to None to retrigger a new search using the new rawlog (new file) rather than the old one
            self.search = None 
            self.uiFrame_goToRow.hide()
            self.uiFrame_search.show()
            self.searchNext()

        self.statusbar.showDynamicText(str("Done ✓ | file opened: " + os.path.basename(file)))

        self.setCompleter(self.uiCombobox_filterInput)
        self.setCompleter(self.uiCombobox_searchInput)

        self.uiSpinBox_goToRow.setMaximum(len(self.rawlog) - 1)

        self._updateStatusbar()
        self.toggleUiItems()
    
    def setCompleter(self, combobox):
        wordlist = self.rawlog.getCompleterList(lambda entry: entry["data"])
        wordlist += ["True", "False", "true", "false"] + list(LOGLEVELS.keys())

        completer = Completer(wordlist, self)
        combobox.setCompleter(completer)

    @catch_exceptions(logger=logger)
    def inspectLine(self, *args):
        if len(self.getRealSelectedIndexes()) != 0:
            if self.currentDetailIndex != self.getRealSelectedIndexes()[0].row():
                def splitter(dictionary, path=[]):
                    retval = []
                    for key, value in dictionary.items():
                        path.append(key)
                        if type(value) == dict:
                            retval += splitter(value, path)
                        else:
                            retval.append({
                                "name": path[0] + "".join(map(lambda value: "[%s]" % helpers.pythonize(value), path[1:])),
                                "value": helpers.pythonize(value)
                            })
                        path.pop(-1)
                    return retval
                
                selectedEntry = self.rawlog[self.getRealSelectedIndexes()[0].row()].get("data")
                details_table_data = splitter(selectedEntry)
                logger.debug("details table data: %s" % details_table_data)
                
                self.uiTable_characteristics.setHorizontalHeaderLabels(["Name", "Value"])
                self.uiTable_characteristics.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft  | QtCore.Qt.Alignment(QtCore.Qt.TextWordWrap))
                self.uiTable_characteristics.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
                self.uiTable_characteristics.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
                self.uiTable_characteristics.horizontalHeader().setStretchLastSection(True)
                self.uiTable_characteristics.setRowCount(len(details_table_data))
                
                # now fill our table
                row = 0
                for entry in splitter(selectedEntry):
                    self.uiTable_characteristics.setItem(row, 0, QtWidgets.QTableWidgetItem(entry["name"]))
                    self.uiTable_characteristics.setItem(row, 1, QtWidgets.QTableWidgetItem(entry["value"]))
                    row += 1
                
                self.uiTable_characteristics.show()
                self.currentDetailIndex = self.getRealSelectedIndexes()[0].row()
                self.uiAction_inspectLine.setData(True)
                self.uiAction_inspectLine.setChecked(True)
            else:
                self.hideInspectLine()
    
    @catch_exceptions(logger=logger)
    def hideInspectLine(self, *args):
        self.currentDetailIndex = None
        self.uiTable_characteristics.hide()
        self.uiAction_inspectLine.setData(False)
        self.uiAction_inspectLine.setChecked(False)

    @catch_exceptions(logger=logger)
    def focusChangedEvent(self, oldWidget, newWidget):
        if type(oldWidget) == QtWidgets.QComboBox:
            self.selectedCombobox = oldWidget
    
    @catch_exceptions(logger=logger)
    def pasteDetailItem(self, *args):
        self.selectedCombobox.setFocus()
        self.selectedCombobox.lineEdit().insert(self.uiTable_characteristics.currentItem().text())
            
    @catch_exceptions(logger=logger)
    def closeFile(self, *args):
        self.rawlog = Rawlog()
        self.hideSearchOrGoto()
        self.selectedCombobox = self.uiCombobox_filterInput
        self.file = None
        self.currentFilterQuery = None
        self.toggleUiItems()
        self.hideInspectLine()

    @catch_exceptions(logger=logger)
    def preferences(self, *args):
        preInstance = {
            "formatter": SettingsSingleton().getCurrentFormatterCode(),
            "style": SettingsSingleton()["uiStyle"]
        }
        
        self.preferencesDialog = PreferencesDialog()
        self.preferencesDialog.show()
        result = self.preferencesDialog.exec_()
        if result:
            self.rebuildUi(preInstance)

    @catch_exceptions(logger=logger)
    def openSearchWidget(self, *args):
        self.uiFrame_goToRow.hide()
        self.uiFrame_search.show()
        self.uiCombobox_searchInput.setFocus()
        self.uiCombobox_searchInput.lineEdit().selectAll()

    @catch_exceptions(logger=logger)
    def setComboboxStatusColor(self, combobox, status):
        combobox.setStyleSheet("background-color: rgb(%s); color: %s;" % (
            ", ".join([str(x) for x in self.queryStatus2colorMapping[status]]),
            sharedUiHelpers.getCssContrastColor(self.queryStatus2colorMapping[status])
        ))

    @catch_exceptions(logger=logger)
    def listViewClicked(self, *args):
        if self.search == None:
            return
        # if no logline is selected, let the search implementation continue where it left of
        if len(self.getRealSelectedIndexes()) > 0:
            self.search.resetStartIndex(self.getRealSelectedIndexes()[0].row())
    
    def searchNext(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.next)

    def searchPrevious(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.previous)

    def _search(self, func):
        query = self.uiCombobox_searchInput.currentText().strip()

        if query == "":
            self.search = None
            self.uiCombobox_searchInput.setStyleSheet("")
        elif self.search != None and self.search.getQuery() == query:
            if len(self.getRealSelectedIndexes()) != 0 and self.getRealSelectedIndexes()[0].row() != self.search.getPosition():
                self.search.resetStartIndex(self.getRealSelectedIndexes()[0].row())
        else:
            self._prepareSearch()   # create search instance (to be bound below)
        
        result = None
        if self.search != None:
            result = func(self.search)  # bind self (first arg) using our (newly created) self.search
            logger.info("Current search result in line (%s): %s" % (str(self.search.getStatus()), str(result)))
            self.setComboboxStatusColor(self.uiCombobox_searchInput, self.search.getStatus())

        # if current line is hidden switch to next line
        if self.uiWidget_listView.isRowHidden(result):
            result = None
            if func == Search.next:
                self.searchNext()
            else:
                self.searchPrevious()
        else:
            if result != None:
                self.lazyItemModel.setVisible(max(0, result-100), min(result+100, len(self.rawlog)))
                self._setCurrentRow(result)

                self.uiWidget_listView.setFocus()
        
                self._updateStatusbar()

    def _prepareSearch(self):
        query = self.uiCombobox_searchInput.currentText().strip()

        progressbar, update_progressbar = self.progressDialog("Searching...", query, True)
        try:
            # let our new search begin at the currently selected line (if any)
            startIndex = 0       # if no logline is selected, let the search implementation begin at our list start
            if len(self.getRealSelectedIndexes()) > 0:
                startIndex = self.getRealSelectedIndexes()[0].row()
            self.search = Search(self.rawlog, query, startIndex, update_progressbar)
            if self.search.getStatus() == QueryStatus.QUERY_ERROR:
                self.checkQueryResult(self.search.getError(), 0, self.uiCombobox_searchInput)
        except AbortSearch:
            self.search = None

        progressbar.hide()
        self.updateComboboxHistory(query, self.uiCombobox_searchInput)
    
    @catch_exceptions(logger=logger)
    def hideSearchOrGoto(self):
        self.uiFrame_search.hide()
        self.uiFrame_goToRow.hide()
        self.search = None
        self.uiCombobox_searchInput.setStyleSheet("")
        self._updateStatusbar()
    
    @catch_exceptions(logger=logger)
    def clearFilter(self, *args):
        if self.currentFilterQuery != None and len(self.currentFilterQuery) > 0:
            currentSelectetLine = None
            if len(self.getRealSelectedIndexes()) != 0:
                currentSelectetLine = self.getRealSelectedIndexes()[0].row()
                
            self.uiCombobox_filterInput.setCurrentText("")
            self.uiCombobox_filterInput.setStyleSheet("")

            progressbar, update_progressbar = self.progressDialog("Clearing filter...", "")
            QtWidgets.QApplication.processEvents()

            self.cancelFilter()

            progressbar.hide()
            self.currentFilterQuery = None
            self.statusbar.showDynamicText("Filter cleared")
            self._updateStatusbar()

            if currentSelectetLine:
                self._setCurrentRow(currentSelectetLine)

            self.toggleUiItems()
    
    @catch_exceptions(logger=logger)
    def filter(self, *args):
        query = self.uiCombobox_filterInput.currentText().strip()
        if query == "":
            self.clearFilter()
            return
        if query == self.currentFilterQuery:
            return
        
        self.updateComboboxHistory(query, self.uiCombobox_filterInput)
        self.currentFilterQuery = query

        selectedLine = None
        if len(self.getRealSelectedIndexes()) != 0:
            selectedLine = self.getRealSelectedIndexes()[0].row()

        progressbar, update_progressbar = self.progressDialog("Filtering...", query, True)
        error = None
        visibleCounter = 0
        filterMapping = {}
        for rawlogPosition in range(len(self.rawlog)):
            # To achieve a successful filter every row has to be loaded 
            loadRows = QtCore.QModelIndex()
            loadRows.child(rawlogPosition, 1)
            self.rawlogModel.fetchMore(loadRows)

            result = matchQuery(query, self.rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            if result["status"] == QueryStatus.QUERY_OK:
                filterMapping[rawlogPosition] = not result["matching"]
            else:
                error = result["error"]
                filterMapping[rawlogPosition] = True            # hide all entries having filter errors
            visibleCounter += 1 if result["matching"] else 0
            if update_progressbar(rawlogPosition, len(self.rawlog)) == True:
                self.cancelFilter()
                break
        self.checkQueryResult(error, visibleCounter, self.uiCombobox_filterInput)
        
        progressbar.setLabelText("Rendering Filter...")
        QtWidgets.QApplication.processEvents()
        
        # this has to be done outside of our filter loop above, to not slow down our filter process significantly
        for rawlogPosition, hidden in filterMapping.items():
            self.uiWidget_listView.setRowHidden(rawlogPosition, hidden)
        
        if self.currentDetailIndex != None and self.uiWidget_listView.isRowHidden(self.currentDetailIndex):
            self.hideInspectLine()

        progressbar.hide()

        self.toggleUiItems()

        # scroll to selected line, if still visible or to next visible line, if not
        # (if there is no next visible line, scroll to previous visible line)
        if selectedLine != None:
            found = False
            for index in range(selectedLine, len(self.rawlog), 1):
                if self.uiWidget_listView.isRowHidden(index) == False:
                    self._setCurrentRow(index)
                    found = True
                    break 
            if not found:
                for index in range(len(self.rawlog)-1, selectedLine, -1):
                    if self.uiWidget_listView.isRowHidden(index) == False:
                        self._setCurrentRow(index)
                        found = True
                        break 
            if not found:
                logger.debug("No visible line to scroll to!")

        self._updateStatusbar()

    @catch_exceptions(logger=logger)
    def openGoToRowWidget(self, *args):
        if self.uiFrame_goToRow.isHidden():
            self.hideSearchOrGoto()
            self.uiFrame_goToRow.show()
            self.uiSpinBox_goToRow.setFocus()
            self.uiSpinBox_goToRow.selectAll()
        else:
            self.uiFrame_goToRow.hide()
            self.selectedCombobox.setFocus()

    @catch_exceptions(logger=logger)
    def goToRow(self, *args):
        if self.uiFrame_goToRow.isHidden():
            return
        
        # prevent switching to row if that row is already selected
        rowIndex = self.uiSpinBox_goToRow.value()
        if len(self.getRealSelectedIndexes()) == 0 or rowIndex != self.getRealSelectedIndexes()[0].row():
            self.lazyItemModel.setVisible(max(0, rowIndex-100), min(rowIndex+100, len(self.rawlog)))
            self._setCurrentRow(rowIndex)
    
    def checkQueryResult(self, error = None, visibleCounter = 0, combobox=None):
        if error != None:
            QtWidgets.QMessageBox.critical(
                self,
                "Monal Log Viewer | ERROR", 
                "Exception in query:\n%s: %s" % (str(type(error).__name__), str(error)),
                QtWidgets.QMessageBox.Ok
            )
            self.setComboboxStatusColor(combobox, QueryStatus.QUERY_ERROR)
        elif visibleCounter == 0:
            self.setComboboxStatusColor(combobox, QueryStatus.QUERY_EMPTY)
        else:
            self.setComboboxStatusColor(combobox, QueryStatus.QUERY_OK)

    @catch_exceptions(logger=logger)
    def uiCombobox_inputChanged(self, *args):
        self.toggleUiItems()

    @catch_exceptions(logger=logger)
    def progressDialog(self, title, label, hasCancelButton=False):
        progressbar = QtWidgets.QProgressDialog(label, "Cancel", 0, 100, self)
        progressbar.setWindowTitle(title)
        progressbar.setGeometry(200, 200, 650, 100)
        if not hasCancelButton:
            progressbar.setCancelButton(None)
        progressbar.setAutoClose(False)
        progressbar.setValue(0)

        # we need to do this because we can't write primitive datatypes from within our closure
        oldpercentage = {"value": 0}

        def update_progressbar(pos, total):
            # cancel loading if the progress dialog was canceled
            if progressbar.wasCanceled():
                return True
            
            currentpercentage = int(pos/total*100)
            if currentpercentage != oldpercentage["value"]:
                progressbar.setValue(currentpercentage)
                QtWidgets.QApplication.processEvents()
            oldpercentage["value"] = currentpercentage

        progressbar.show()
        return (progressbar, update_progressbar)
    
    @catch_exceptions(logger=logger)
    def goToFirstRow(self, *args):
        # set first row as current row
        self.uiWidget_listView.scrollToTop()
        self.uiWidget_listView.setCurrentIndex(self.rawlogModel.createIndex(0, 0))
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to first row: %d" % index))

    @catch_exceptions(logger=logger)
    def goToLastRow(self, *args):
        # set last row as current row 
        self.lazyItemModel.setVisible(len(self.rawlog)-100, len(self.rawlog))
        self.uiWidget_listView.scrollToBottom()
        self.uiWidget_listView.setCurrentIndex(self.rawlogModel.createIndex(self.lazyItemModel.rowCount(-1)-1, 0))


    @catch_exceptions(logger=logger)
    def goToFirstRowInViewport(self, *args):
        if len(self.getRealSelectedIndexes()) == 0:
            return
        startIndex = self.getRealSelectedIndexes()[0].row()

        visualItemRect = self.uiWidget_listView.visualRect(self.rawlogModel.createIndex(startIndex, 0))
        top = self.uiWidget_listView.indexAt(visualItemRect.topLeft())
        self._setCurrentRow(top.row())
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the first line in the viewport: %d" % lastIndex))

    @catch_exceptions(logger=logger)
    def goToLastRowInViewport(self, *args):
        if len(self.getRealSelectedIndexes()) == 0:
            return
        startIndex = self.getRealSelectedIndexes()[0].row()
        
        visualItemRect = self.uiWidget_listView.visualRect(self.rawlogModel.createIndex(startIndex, 0))
        #Note that for historical reasons this function returns top() + height() - 1; use y() + height() to retrieve the true y-coordinate.
        #See: https://doc.qt.io/qtforpython-5/PySide2/QtCore/QRect.html#PySide2.QtCore.PySide2.QtCore.QRect.bottom
        bottom = self.uiWidget_listView.indexAt(QtCore.QPoint(visualItemRect.y()+visualItemRect.height(), 0))

        self._setCurrentRow(bottom.row())
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the last line in the viewport: %d" % lastIndex))
    
    def cancelFilter(self):
        for index in range(len(self.rawlog)):
            if self.uiWidget_listView.isRowHidden(index):
                self.uiWidget_listView.setRowHidden(index, False)
            # this slows down significantly
            #update_progressbar(index, len(self.rawlog))
        self.currentFilterQuery = None
    
    @catch_exceptions(logger=logger)
    def pushStack(self, *args):
        selectedLine = None
        if self.getRealSelectedIndexes():
            selectedLine = self.getRealSelectedIndexes()[0].row()

        currentSearchResult = None
        if self.search:
            currentSearchResult = self.search.getCurrentResult()

        searchSelectionStart = self.uiCombobox_searchInput.lineEdit().selectionStart()
        searchSelectionLength = self.uiCombobox_searchInput.lineEdit().selectionLength()
        filterSelectionStart = self.uiCombobox_filterInput.lineEdit().selectionStart()
        filterSelectionLength = self.uiCombobox_filterInput.lineEdit().selectionLength()

        state = {
            "selectedLine": selectedLine,
            "scrollPosVertical": self.uiWidget_listView.verticalScrollBar().value(),
            "scrollPosHorizontal": self.uiWidget_listView.horizontalScrollBar().value(),
            "selectedCombobox": self.selectedCombobox,
            "listViewFocus": self.uiWidget_listView.hasFocus(),
            "detail": {
                "isOpen": not self.uiTable_characteristics.isHidden(), 
                "size": self.uiTable_characteristics.height(), 
                "currentDetailIndex": self.currentDetailIndex
            }, 
            "search": {
                "isOpen": not self.uiFrame_search.isHidden(),
                "instance": self.search, 
                "currentText": self.uiCombobox_searchInput.currentText(), 
                "currentLine": currentSearchResult,
                "selection": {"start": searchSelectionStart, "length": searchSelectionLength},
            },
            "filter": {
                "currentFilterQuery": self.currentFilterQuery, 
                "currentText": self.uiCombobox_filterInput.currentText(),
                "selection": {"start": filterSelectionStart, "length": filterSelectionLength},
            },
            "goToRow": {
                "isOpen": not self.uiFrame_goToRow.isHidden(),
                "currentInt": self.uiSpinBox_goToRow.value(),
            }
        }
        self.stack.append(state)
        self._updateStatusbar()
        self.statusbar.showDynamicText("State saved ✓")
        self.toggleUiItems()
    
    @catch_exceptions(logger=logger)
    def popStack(self, *args):
        if len(self.stack) < 1:
            self.statusbar.showDynamicText("Unable to load state ✗")
            return
        
        stack = self.stack.pop()

        # unpacking filter
        self.uiCombobox_filterInput.setCurrentText(stack["filter"]["currentText"])
        self.uiCombobox_filterInput.lineEdit().setSelection(stack["filter"]["selection"]["start"], stack["filter"]["selection"]["length"])
        if stack["filter"]["currentFilterQuery"]:
            self.filter()

        # unpacking search
        if stack["search"]["isOpen"]:
            self.uiCombobox_searchInput.setCurrentText(stack["search"]["currentText"])
            self.uiCombobox_searchInput.lineEdit().setSelection(stack["search"]["selection"]["start"], stack["search"]["selection"]["length"])
            if stack["search"]["instance"]:
                # Before continuing the search, we set the row so that the search starts at the correct index
                self._setCurrentRow(stack["search"]["currentLine"])
                self.search = stack["search"]["instance"]
                self.searchNext()
                self.searchPrevious()

        # unpacking goToRow
        if stack["goToRow"]["isOpen"]:
            self.uiFrame_goToRow.show()
            self.uiSpinBox_goToRow.setValue(stack["goToRow"]["currentInt"])
                
        # unpacking details
        if stack["detail"]["isOpen"]:
            self._setCurrentRow(stack["detail"]["currentDetailIndex"])
            self.inspectLine()
            self.uiTable_characteristics.setFixedHeight(stack["detail"]["size"])
            if stack["detail"]["size"] == 0:
                self.uiTable_characteristics.setFixedHeight(800)

        # unpacking selected items and scroll position
        if stack["selectedLine"]:
            self._setCurrentRow(stack["selectedLine"])
        self.uiWidget_listView.verticalScrollBar().setValue(stack["scrollPosVertical"])
        self.uiWidget_listView.horizontalScrollBar().setValue(stack["scrollPosHorizontal"])

        if stack["selectedCombobox"]:
            stack["selectedCombobox"].lineEdit().setFocus()
        
        if stack["listViewFocus"]:
            self.uiWidget_listView.setFocus()

        self._updateStatusbar()
        #self.statusbar.showDynamicText("State loaded ✓")
        self.toggleUiItems()

    @catch_exceptions(logger=logger)
    def _updateStatusbar(self, *args):
        text = ""

        if len(self.rawlog) > 0:
            text += "%s:" % os.path.basename(self.file)

        if self.currentFilterQuery != None:
            text += " %d/%d" % (
                len([index for index in range(len(self.rawlog)) if not self.uiWidget_listView.isRowHidden(index)]),
                len(self.rawlog)
            )
        else:
            text += " %d" % len(self.rawlog)
            
        if self.search != None and not self.uiFrame_search.isHidden() and len(self.uiCombobox_searchInput.currentText().strip()) > 0:
            if len(self.search) != 0:
                text += ", search: %d/%d" % (self.search.getPosition(), len(self.search))
            else:
                text += ", search: no result!"

        if len(self.stack) != 0:
            text += ", stack: %d" % len(self.stack)

        self.statusbar.setText(text)

    @catch_exceptions(logger=logger)
    def rebuildUi(self, preInstance):
        def rebuildCombobox(combobox):
            if len(SettingsSingleton().getComboboxHistory(combobox)) != len([combobox.itemText(i) for i in range(combobox.count())]):
                currentText = combobox.lineEdit().text()
                self.loadComboboxHistory(combobox)
                self.updateComboboxHistory(currentText, combobox)
            
        rebuildCombobox(self.uiCombobox_filterInput)
        rebuildCombobox(self.uiCombobox_searchInput)

        if preInstance["style"] != SettingsSingleton()["uiStyle"]:
            sharedUiHelpers.applyStyle(SettingsSingleton()["uiStyle"])
    
    def loadComboboxHistory(self, combobox):
        combobox.clear()
        combobox.addItems(SettingsSingleton().getComboboxHistory(combobox))
        combobox.setCurrentIndex(-1)

    def updateComboboxHistory(self, query, combobox):
        logger.debug("update combobox history with: '%s'..." % str(query))
        if query == None or query.strip() == "":
            logger.debug("returning early...")
            return

        # remove query from combobox (if it exists) and reinsert it at top position
        if combobox.findText(query) != -1:
            combobox.removeItem(combobox.findText(query))
        combobox.insertItem(0, query)

        # store this new combobox ordering into our settings
        SettingsSingleton().setComboboxHistory(combobox, [combobox.itemText(i) for i in range(combobox.count()) if combobox.itemText(i).strip() != ""])
        
        # make sure that the topmost combobox entry is always an empty string but still select our query
        self.loadComboboxHistory(combobox)  # reload from settings to get rid of empty entries and make sure we always reflect in ui what is saved
        combobox.insertItem(0, "")
        combobox.setCurrentIndex(1)         # after adding an empty row, the current query is at index 1

    def copyToClipboard(self):
        data = None
        if self.uiWidget_listView.hasFocus():
            data = self.rawlog[self.getRealSelectedIndexes()[0].row()]["data"]["__formattedMessage"]
        if self.uiTable_characteristics.hasFocus():
            data = self.uiTable_characteristics.currentItem().text()
        
        if data != None:
            # copy to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.clear(mode=clipboard.Clipboard)
            clipboard.setText(data, mode=clipboard.Clipboard)
            self.statusbar.showDynamicText(str("Done ✓ | Copied to clipboard"))

    def _setCurrentRow(self, row):
        index = self.lazyItemModel.createIndex(row, 0)
        logger.info(f"Setting row {row} to index {index.row()}")
        #self.uiWidget_listView.scrollTo(index, hint=QtWidgets.QAbstractItemView.PositionAtCenter)
        self.uiWidget_listView.setCurrentIndex(self.lazyItemModel.mapFromSource(index))
    
    def getRealSelectedIndexes(self):
        return [self._resolveIndex(self.uiWidget_listView.model(), index) for index in self.uiWidget_listView.selectedIndexes()]
    
    def _resolveIndex(self, model, index):
        # recursively map index in proxy model chain to get real rawlog index
        if not hasattr(model, "sourceModel") or not hasattr(model, "mapToSource"):
            return index
        return self._resolveIndex(model.sourceModel(), model.mapToSource(index))
