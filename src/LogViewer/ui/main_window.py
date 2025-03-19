from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os, functools, json
import datetime

from LogViewer.storage import SettingsSingleton
from LogViewer.storage import GlobalSettingsSingleton
from LogViewer.utils import Search, AbortSearch, QueryStatus, UdpServer
from LogViewer.utils import loader
import LogViewer.utils.helpers as helpers
from .utils import Completer, MagicLineEdit, Statusbar, RawlogModel, LazyItemModel, FilterModel
from .preferences_dialog import PreferencesDialog
from .udp_window import UdpWindow
from .stack_pop_window import StackPopWindow
from .stack_push_window import StackPushWindow
from .new_profile_dialog import NewProfileDialog
from shared.storage import Rawlog
from shared.ui.utils import UiAutoloader
from shared.ui.utils import catch_exceptions
from shared.utils import Paths
import shared.ui.utils.helpers as sharedUiHelpers
                
import logging
logger = logging.getLogger(__name__)

LOAD_CONTEXT = 150
LAZY_DISTANCE = 400
LAZY_LOADING = 100

@UiAutoloader
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        self.rawlog = Rawlog()
        self.file = None
        self.udpServer = None
        self.search = None
        self.statusbar = Statusbar(self, self.uiMenuBar_main)
        self.currentFilterQuery = None
        self.stack = {}
        self.selectedCombobox = self.uiCombobox_filterInput

        self.rawlogModel = None
        
        SettingsSingleton().loadDimensions(self)

        self.profiles = {}
        for name in GlobalSettingsSingleton().getProfiles():
            displayName = GlobalSettingsSingleton().getProfileDisplayName(name)
            profileAction = QtWidgets.QAction(displayName,self)
            profileAction.triggered.connect(functools.partial(self.switchToProfile, name)) 
            self.uiMenu_profiles.addAction(profileAction)
            self.profiles[name] = {"profileAction": profileAction, "displayName": displayName}

        self.switchToProfile(GlobalSettingsSingleton().getActiveProfile())

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
        self.uiAction_close.triggered.connect(self.close)
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
        self.uiAction_listenUdpStream.triggered.connect(self.createUdpWindow)
        self.uiAction_stopUdpStream.triggered.connect(self.stopUdpStream)

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
        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearchAndGoToRow)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

        self.loadComboboxHistory(self.uiCombobox_filterInput)
        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)
        self.uiSplitter_inspectLine.splitterMoved.connect(functools.partial(SettingsSingleton().storeState, self.uiSplitter_inspectLine))
        SettingsSingleton().loadState(self.uiSplitter_inspectLine)

        self.hideInspectLine()

        self.uiAction_cloneCurrentProfile.triggered.connect(self.cloneCurrentProfile)
        self.uiAction_addNewProfile.triggered.connect(self.addNewProfile)
        self.uiAction_deleteCurrentProfile.triggered.connect(self.deleteCurrentProfile)
        self.uiAction_exportCurrentProfile.triggered.connect(self.exportCurrentProfile)
        self.uiAction_importCurrentProfile.triggered.connect(self.importCurrentProfile)

    @catch_exceptions(logger=logger)
    def quit(self, dummy):
        sys.exit()

    @catch_exceptions(logger=logger)
    def closeEvent(self, event):
        sys.exit()

    @catch_exceptions(logger=logger)
    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        SettingsSingleton().storeDimension(self)
    
    def toggleUiItems(self):
        self.uiAction_close.setEnabled(self.rawlog != None)
        self.uiAction_quit.setEnabled(True)
        self.uiAction_open.setEnabled(self.udpServer == None)
        self.uiAction_inspectLine.setEnabled(self.rawlog != None)
        self.uiAction_preferences.setEnabled(True)
        self.uiAction_export.setEnabled(self.rawlog != None)
        self.uiAction_pushStack.setEnabled(self.rawlog != None)
        self.uiAction_popStack.setEnabled((self.rawlog != None) and len(self.stack) != 0)
        self.uiAction_search.setEnabled(self.rawlog != None)
        self.uiAction_save.setEnabled(self.rawlog != None)
        self.uiAction_goToRow.setEnabled(self.rawlog != None)
        self.uiAction_firstRow.setEnabled(self.rawlog != None)
        self.uiAction_lastRow.setEnabled(self.rawlog != None)
        self.uiButton_previous.setEnabled((self.rawlog != None) and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_next.setEnabled((self.rawlog != None) and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_filterClear.setEnabled((self.rawlog != None) and self.currentFilterQuery != None)
        self.uiButton_goToRow.setEnabled(self.rawlog != None)
        self.uiSpinBox_goToRow.setEnabled(self.rawlog != None)
        self.uiCombobox_searchInput.setEnabled(self.rawlog != None)
        self.uiCombobox_filterInput.setEnabled(self.rawlog != None)
        self.uiAction_lastRowInViewport.setEnabled(self.rawlog != None)
        self.uiAction_firstRowInViewport.setEnabled(self.rawlog != None)
        self.uiAction_listenUdpStream.setEnabled(self.file == None and self.udpServer == None)
        self.uiAction_stopUdpStream.setEnabled(self.udpServer != None)

    def export(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this text logfile", SettingsSingleton().getLastPath(), "Compressed logfile (*.log.gz)(*.log.gz);;Logfile (*.log)(*.log);;All files (*)")
            if check:
                SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
                formatter = self.rawlogModel.createFormatter()
                status = self.rawlog.export_file(file, custom_store_callback = lambda entry: entry if self.filterModel.isRowVisible(self.rawlog.getItemIndex(entry)) else None, formatter = lambda entry: self.rawlogModel.createFormatterText(formatter, entry))
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Log export was successful"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not export log"))

    def save(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this rawlog logfile", SettingsSingleton().getLastPath(), "Compressed Monal rawlog (*.rawlog.gz)(*.rawlog.gz);;Monal rawlog (*.rawlog)(*.rawlog);;All files (*)")
            if check:
                SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
                status = self.rawlog.store_file(file, custom_store_callback = lambda entry: entry if self.filterModel.isRowVisible(self.rawlog.getItemIndex(entry)) else None)
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
        self.close()
        self.udpServer = None
        
        self.statusbar.setText("Loading File: '%s'..." % os.path.basename(file))
        self.rawlog = Rawlog()
        self.search = None
        
        progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: %s" % os.path.basename(file), True)
        try:
            # don't pretend something was loaded if the loading was aborted
            if self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader) != True:
                self.close()        # reset our ui to a sane state
                progressbar.hide()
                self.statusbar.setText("")
                return
        except Exception as error:
            progressbar.hide()
            QtWidgets.QMessageBox.warning(
                self,
                "Monal Log Viewer | ERROR", 
                "Exception in query:\n%s: %s" % (str(type(error).__name__), str(error)),
                QtWidgets.QMessageBox.Ok
            )
            return
        
        self._initModels()
        
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

        self.setWindowTitle(f"{file} - Monal Log Viewer")

        self._updateStatusbar()
        self.toggleUiItems()
    
    def setCompleter(self, combobox):
        wordlist = self.rawlog.getCompleterList(lambda entry: entry)
        wordlist += ["True", "False", "true", "false"] + list(SettingsSingleton().getLoglevelNames())

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
                
                selectedEntry = self.rawlog[self.getRealSelectedIndexes()[0].row()]
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
    def close(self, *args):
        self.uiWidget_listView.setModel(None)
        self.rawlog = Rawlog()
        self.udpServer = None
        self.hideSearchAndGoToRow()
        self.selectedCombobox = self.uiCombobox_filterInput
        self.file = None
        self.currentFilterQuery = None
        self.toggleUiItems()
        self.hideInspectLine()
        self.setWindowTitle(f"Monal Log Viewer")

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

        if result == None:
            return
        
        # if current line is hidden switch to next line
        if not self.filterModel.isRowVisible(result):
            result = None
            if func == Search.next:
                self.searchNext()
            else:
                self.searchPrevious()
        else:
            if result != None:
                self.uiWidget_listView.model().setCurrentRow(self.filterModel.mapFromSource(self.filterModel.createIndex(result, 0)).row())

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
    def hideSearchAndGoToRow(self):
        self.uiFrame_search.hide()
        self.uiFrame_goToRow.hide()
        self.search = None
        self.uiCombobox_searchInput.setStyleSheet("")
        self._updateStatusbar()

    def cancelFilter(self):
        self.uiSpinBox_goToRow.setMaximum(len(self.rawlog) - 1)
        self.currentFilterQuery = None
        self.filterModel.clearFilter()
    
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
            self.statusbar.showDynamicText("Filter cleared")
            self._updateStatusbar()

            if currentSelectetLine:
                self.uiWidget_listView.model().setCurrentRow(currentSelectetLine)

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

        currentIndexBefore = self.uiWidget_listView.model().mapToSource(self.uiWidget_listView.currentIndex())

        progressbar, update_progressbar = self.progressDialog("Filtering...", query, True)
        error, visibleCounter = self.filterModel.filter(query, update_progressbar=update_progressbar)
        self.checkQueryResult(error, visibleCounter, self.uiCombobox_filterInput)

        self.uiSpinBox_goToRow.setMaximum(visibleCounter)

        if error != None:
            self.clearFilter()
            progressbar.hide()
            return

        progressbar.setLabelText("Rendering Filter...")
        QtWidgets.QApplication.processEvents()

        progressbar.hide()
        self.toggleUiItems()

        # scroll to selected line, if still visible or to next visible line, if not
        # (if there is no next visible line, scroll to previous visible line)
        if currentIndexBefore.isValid():
            self.uiWidget_listView.setCurrentIndex(self.uiWidget_listView.model().mapFromSource(currentIndexBefore))
        
        self.triggeredProgramatically = False
        self._updateStatusbar()

    def checkQueryResult(self, error = None, visibleCounter = 0, combobox=None):
        if error != None:
            QtWidgets.QMessageBox.warning(
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
    def openGoToRowWidget(self, *args):
        if self.uiFrame_goToRow.isHidden():
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
        rowIndex = self.filterModel.mapFromSource(self.filterModel.createIndex(self.uiSpinBox_goToRow.value(), 0)).row()
        if self.filterModel.isRowVisible(rowIndex):
            self.uiWidget_listView.model().setCurrentRow(rowIndex)
        else:
            self.statusbar.showDynamicText(str("Error ✗ | This is not visible"))  

    @catch_exceptions(logger=logger)
    def goToFirstRow(self, *args):
        # set first row as current row
        for index in range(len(self.rawlog)):
            if self.filterModel.isRowVisible(index):
                break
        with self.lazyItemModel.triggerScrollChanges():
            self.uiWidget_listView.model().setCurrentRow(index)
            self.uiWidget_listView.scrollToTop()
            #self.statusbar.showDynamicText(str("Done ✓ | Switched to first row: %d" % index))

    @catch_exceptions(logger=logger)
    def goToLastRow(self, *args):
        # set last row as current row

        # As the lazyItemModel isn't functional yet, the lazyItemModel can't be used here
        # with self.lazyItemModel.triggerScrollChanges():
        self.uiWidget_listView.model().setCurrentRow(self.filterModel.rowCount(None)-1)
        self.uiWidget_listView.scrollToBottom()
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to first row: %d" % index))

    @catch_exceptions(logger=logger)
    def goToFirstRowInViewport(self, *args):
        if len(self.getRealSelectedIndexes()) == 0:
            return

        visualItemRect = self.uiWidget_listView.indexAt(self.uiWidget_listView.viewport().contentsRect().topLeft()).row()
        self.uiWidget_listView.model().setCurrentRow(visualItemRect)
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the first line in the viewport: %d" % lastIndex))

    @catch_exceptions(logger=logger)
    def goToLastRowInViewport(self, *args):
        if len(self.getRealSelectedIndexes()) == 0:
            return
        
        visualItemRect = self.uiWidget_listView.indexAt(self.uiWidget_listView.viewport().contentsRect().bottomLeft()).row()
        self.uiWidget_listView.model().setCurrentRow(visualItemRect)
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the last line in the viewport: %d" % lastIndex))
    
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
            "timeStamp": datetime.datetime.now().strftime("%H:%M:%S"),
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

        self.stackPushWindow = StackPushWindow(list(self.stack.keys()))
        self.stackPushWindow.show()
        result = self.stackPushWindow.exec_()
        if result:
            name = self.stackPushWindow.getName()
            self.stack[name] = state
            self._updateStatusbar()
            self.statusbar.showDynamicText("State saved ✓")
            self.toggleUiItems()
        else:
            self.statusbar.showDynamicText("Failed to save state ✗")
    
    @catch_exceptions(logger=logger)
    def popStack(self, *args):
        if len(self.stack) < 1:
            self.statusbar.showDynamicText("No state saved ✗")
            return

        self.stackPopWindow = StackPopWindow({k:self.stack[k]["timeStamp"] for k in self.stack})
        self.stackPopWindow.show()
        result = self.stackPopWindow.exec_()
        if not result:
            self.statusbar.showDynamicText("Failed to load state ✗")
            return

        stack = self.stack[self.stackPopWindow.getIndex()]
        self.statusbar.showDynamicText("State loaded ✓")

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
                self.uiWidget_listView.model().setCurrentRow(stack["search"]["currentLine"])
                self.search = stack["search"]["instance"]
                self.searchNext()
                self.searchPrevious()

        # unpacking goToRow
        if stack["goToRow"]["isOpen"]:
            self.uiFrame_goToRow.show()
            self.uiSpinBox_goToRow.setValue(stack["goToRow"]["currentInt"])
                
        # unpacking details
        if stack["detail"]["isOpen"]:
            self.uiWidget_listView.model().setCurrentRow(stack["detail"]["currentDetailIndex"])
            self.inspectLine()
            self.uiTable_characteristics.setFixedHeight(stack["detail"]["size"])
            if stack["detail"]["size"] == 0:
                self.uiTable_characteristics.setFixedHeight(800)

        # unpacking selected items and scroll position
        if stack["selectedLine"]:
            self.uiWidget_listView.model().setCurrentRow(stack["selectedLine"])
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

        if len(self.rawlog) > 0 and self.file != None:
            text += "%s:" % os.path.basename(self.file)
        elif self.udpServer != None:
            if self.udpServer.getLastRemote() == None:
                text += "<remote unknown>"
            else:
                text += "%s:%d:" % self.udpServer.getLastRemote()

        if self.currentFilterQuery != None:
            text += " %d/%d" % (
                self.filterModel.rowCount(None),
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

        if self.rawlogModel != None:
            self.rawlogModel.reloadSettings()
    
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

    @catch_exceptions(logger=logger)
    def copyToClipboard(self):
        data = None
        if self.uiWidget_listView.hasFocus():
            data = self.rawlog[self.getRealSelectedIndexes()[0].row()]["__formattedMessage"]
        if self.uiTable_characteristics.hasFocus():
            data = self.uiTable_characteristics.currentItem().text()
        
        if data != None:
            # copy to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.clear(mode=clipboard.Clipboard)
            clipboard.setText(data, mode=clipboard.Clipboard)
            self.statusbar.showDynamicText(str("Done ✓ | Copied to clipboard"))

    def getRealSelectedIndexes(self):
        return [self._resolveIndex(self.uiWidget_listView.model(), index) for index in self.uiWidget_listView.selectedIndexes()]

    @catch_exceptions(logger=logger)
    def cloneCurrentProfile(self):
        self._createNewProfileFromFile(Paths.get_conf_filepath(GlobalSettingsSingleton().getActiveProfile()))

    @catch_exceptions(logger=logger)
    def addNewProfile(self):
        self._createNewProfileFromFile(Paths.get_default_conf_filepath(GlobalSettingsSingleton().getDefaultProfile()))

    @catch_exceptions(logger=logger)
    def switchToProfile(self, profile):
        # remove all icons
        for profileName in self.profiles:
            self.profiles[profileName]["profileAction"].setIcon(QtGui.QIcon(""))
            # set icon for active profile
            if profileName == profile:
                self.profiles[profile]["profileAction"].setIcon(self.style().standardIcon(getattr(QStyle, "SP_DialogYesButton")))
        GlobalSettingsSingleton().setActiveProfile(profile)

        # reload ui
        SettingsSingleton().reload()
        if self.file != None:
            self.openLogFile(self.file)
        self.update

    @catch_exceptions(logger=logger)
    def createUdpWindow(self, dummy):
        self.udpWindow = UdpWindow()
        self.udpWindow.show()
        result = self.udpWindow.exec_()
        if result:
            self.close()
            try:
                self.udpServer = UdpServer(SettingsSingleton().getUdpEncryptionKey(), host=SettingsSingleton().getUdpHost(), port=SettingsSingleton().getUdpPort())
            except Exception as error:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Monal Log Viewer | ERROR", 
                    "Exception while starting UDP receiver:\n%s: %s" % (str(type(error).__name__), str(error)),
                    QtWidgets.QMessageBox.Ok
                )
                self.udpServer = None
                return

            self._initModels(self.udpServer)

            self.setWindowTitle(f"Listening on {SettingsSingleton().getUdpHost()}:{SettingsSingleton().getUdpPort()} - Monal Log Viewer")
            self._updateStatusbar()
            self.toggleUiItems()

    @catch_exceptions(logger=logger)
    def stopUdpStream(self, dummy):
        self.udpServer.stop()
        self.udpServer = None
        self.toggleUiItems()

    def _createNewProfileFromFile(self, pathToParentProfile):
        self.newProfileDialog = NewProfileDialog()
        self.newProfileDialog.show()
        result = self.newProfileDialog.exec_()
        if result:
            displayName = self.newProfileDialog.getName()
            profileName = GlobalSettingsSingleton().getFileNameFromDisplayName(displayName)
            GlobalSettingsSingleton().createFileFromParentProfile(pathToParentProfile, displayName)

            profileAction = QtWidgets.QAction(displayName, self)
            profileAction.triggered.connect(functools.partial(self.switchToProfile, profileName)) 
            self.uiMenu_profiles.addAction(profileAction)
            self.profiles[profileName] = {}
            self.profiles[profileName]["profileAction"] = profileAction
            self.profiles[profileName]["displayName"] = displayName

            self.switchToProfile(profileName)
    
    @catch_exceptions(logger=logger)
    def deleteCurrentProfile(self, profile):
        if len(self.profiles) > 1:
            profileName = GlobalSettingsSingleton().getActiveProfile()
            self.profiles[profileName]["profileAction"].setVisible(False)
            del self.profiles[profileName]
            self.switchToProfile(list(self.profiles.keys())[0])
            os.remove(Paths.get_conf_filepath(profileName))
            self.statusbar.showDynamicText(str("Done ✓ | Profile deleted!"))  
        else:
            self.statusbar.showDynamicText(str("Error ✗ | You need more than one profile to delete one!"))  

    @catch_exceptions(logger=logger)
    def exportCurrentProfile(self):
        file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Export Profile", SettingsSingleton().getLastPath(), "Json (*.json);;All files (*)")
        if check:
            fileName = file.split("/")[-1]
            with open(Paths.get_conf_filepath(GlobalSettingsSingleton().getActiveProfile()), 'rb') as fp:
                data = json.load(fp)

            with open(file, 'w+') as fp:
                json.dump(data, fp)

            self.statusbar.showDynamicText(str("Done ✓ | Profile exported!"))
        else:
            self.statusbar.showDynamicText(str("Error ✗ | Something went wrong exporting the profile!"))

    @catch_exceptions(logger=logger)
    def importCurrentProfile(self):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Import Profile", SettingsSingleton().getLastPath(), "Json (*.json);;All files (*)")
        if check:
            self._createNewProfileFromFile(file)
            self.statusbar.showDynamicText(str("Done ✓ | Profile imported!"))
        
    def _initModels(self, udpServer=None):
        # List reasons why it is stacked like this
        self.rawlogModel = RawlogModel(self.rawlog, parent=self.uiWidget_listView, udpServer=udpServer)
        # To apply the right formatter the rawlogModel is reloaded
        self.rawlogModel.reloadSettings()
        # connect all needed signals to our rawlog model
        self.rawlogModel.rowsInserted.connect(self._processRowsAboutToBeInserted)
        self.rawlogModel.rowsInserted.connect(self._processRowsInserted)
        # create filter model
        self.filterModel = FilterModel(self.rawlogModel)
        # Disable functions that use the lazyItemModel until it is fixed
        #self.lazyItemModel = LazyItemModel(self.filterModel, LOAD_CONTEXT, LAZY_DISTANCE, LAZY_LOADING)
        #self.uiWidget_listView.setModel(self.lazyItemModel)
        self.uiWidget_listView.setModel(self.filterModel)

    @catch_exceptions(logger=logger)
    def _processRowsAboutToBeInserted(self, parent, start, end, *args):
        self.last_insert_event = {"start": start, "end": end}
    
    @catch_exceptions(logger=logger)
    def _processRowsInserted(self, *args):
        self._updateStatusbar()
        if self.search != None:
            # our search is using an exclusive end value, but Qt's rowsAboutToBeInserted uses an inclusive end value
            self.search.searchMatchingEntries(self.last_insert_event["start"], self.last_insert_event["end"]+1)
    
    def _resolveIndex(self, model, index):
        # recursively map index in proxy model chain to get real rawlog index
        if not hasattr(model, "sourceModel") or not hasattr(model, "mapToSource"):
            return index
        return self._resolveIndex(model.sourceModel(), model.mapToSource(index))
