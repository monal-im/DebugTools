from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os, functools

from LogViewer.storage import SettingsSingleton
from LogViewer.utils import Search, AbortSearch, QueryStatus, matchQuery
import LogViewer.utils.helpers as helpers
from LogViewer.utils.version import VERSION
from .utils import Completer, MagicLineEdit, Statusbar
from .preferences_dialog import PreferencesDialog
from shared.storage import Rawlog, AbortRawlogLoading
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
        self.logflag2colorMapping = {v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}

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
        self.uiAction_about.triggered.connect(functools.partial(sharedUiHelpers.action_about, VERSION))
        self.uiAction_pushStack.triggered.connect(self.pushStack)
        self.uiAction_popStack.triggered.connect(self.popStack)
        self.uiAction_goToRow.triggered.connect(self.openGoToRowWidget)
        self.uiAction_firstRow.triggered.connect(self.goToFirstRow)
        self.uiAction_lastRow.triggered.connect(self.goToLastRow)
        self.uiAction_firstRowInViewport.triggered.connect(self.goToFirstRowInViewport)
        self.uiAction_lastRowInViewport.triggered.connect(self.goToLastRowInViewport)

        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiWidget_listView.clicked.connect(self.listViewClicked)
        self.uiFrame_search.hide()

        self.uiButton_goToRow.setIcon(self.style().standardIcon(getattr(QStyle, "SP_CommandLink")))
        self.uiButton_goToRow.clicked.connect(self.goToRow)
        self.uiSpinBox_goToRow.valueChanged.connect(self.goToRow)
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
                status = self.rawlog.export_file(file, custom_store_callback = lambda entry: entry["data"] if not entry["uiItem"].isHidden() else None, formatter = lambda entry: self.createFormatterText(formatter, entry))
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Log export was successful"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not export log"))

    def save(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this rawlog logfile", SettingsSingleton().getLastPath(), "Compressed Monal rawlog (*.rawlog.gz)(*.rawlog.gz);;Monal rawlog (*.rawlog)(*.rawlog);;All files (*)")
            if check:
                SettingsSingleton().setLastPath(os.path.dirname(os.path.abspath(file)))
                status = self.rawlog.store_file(file, custom_store_callback = lambda entry: entry["data"] if not entry["uiItem"].isHidden() else None)
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
        formatter = self.createFormatter()
        self.rawlog = Rawlog()
        self.search = None
        
        def loader(entry):
            itemFont = SettingsSingleton().getQFont()
            # directly warn about file corruptions when they happen to allow the user to abort the loading process
            # using the cancel button in the progressbar window
            if "__warning" in entry and entry["__warning"] == True:
                QtWidgets.QMessageBox.warning(self, "File corruption detected", entry["message"])

            formattedEntry = self.createFormatterText(formatter, entry)
            entry["__formattedMessage"] = formattedEntry
            
            # return None if our formatter filtered out that entry
            if formattedEntry == None:
                return None
            
            item_with_color = helpers.wordWrapLogline(formattedEntry)   
            fg, bg = SettingsSingleton().getQColorTuple(self.logflag2colorMapping[entry["flag"]])
            item_with_color = QtWidgets.QListWidgetItem(item_with_color)
            item_with_color.setFont(itemFont)
            item_with_color.setForeground(fg)
            if bg == None:
                bg = QtGui.QBrush()     # default color (usually transparent)
            item_with_color.setBackground(bg)
            
            return {"uiItem": item_with_color, "data": entry}
        
        progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: %s" % os.path.basename(file), True)
        # don't pretend something was loaded if the loading was aborted
        if self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader) != True:
            self.closeFile()        # reset our ui to a sane state
            progressbar.hide()
            self.statusbar.setText("")
            return

        self.statusbar.setText("Rendering File: '%s'..." % os.path.basename(file))
        progressbar.setLabelText("Rendering File: '%s'..." % os.path.basename(file))
        progressbar.setCancelButton(None)       # disable cancel button when rendering our file
        QtWidgets.QApplication.processEvents()
        error = None
        visibleCounter = 0
        
        # Add uiItems and apply the filter manually as it's faster to do both things at the same time
        self.currentFilterQuery = self.uiCombobox_filterInput.currentText().strip()
        for index in range(len(self.rawlog)):
            self.uiWidget_listView.addItem(self.rawlog[index]["uiItem"])
            if len(self.currentFilterQuery ) != 0:
                result = matchQuery(self.currentFilterQuery , self.rawlog, index, usePython=SettingsSingleton()["usePythonFilter"])
                if result["status"] != QueryStatus.QUERY_ERROR:
                    self.rawlog[index]["uiItem"].setHidden(not result["matching"])
                else:
                    error = result["error"]
                visibleCounter += 1 if result["matching"] else 0
        if len(self.currentFilterQuery) != 0:
            self.checkQueryResult(error, visibleCounter, self.uiCombobox_filterInput)
        QtWidgets.QApplication.processEvents()
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
        completer.setCompletionMode(Completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combobox.setCompleter(completer)
    
    def createFormatterText(self, formatter, entry, ignoreError=False):        
        try:
            # this will make sure the log formatter does not change our log entry, but it makes loading slower
            # formattedEntry = formatter({value: entry[value] for value in entry.keys()})
            return formatter(entry)
        except Exception as e:
            logger.exception("Exception while calling log formatter for: %s" % entry)
            if not ignoreError:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Monal Log Viewer | ERROR", 
                    "Exception in formatter code:\n%s: %s\n%s" % (str(type(e).__name__), str(e), entry),
                    QtWidgets.QMessageBox.Ok
                )
            raise AbortRawlogLoading()       # abort loading

    def createFormatter(self):
        # first of all: try to compile our log formatter code and abort, if this isn't generating a callable formatter function
        try:
            return self.compileLogFormatter(SettingsSingleton().getCurrentFormatterCode())
        except Exception as e:
            logger.exception("Exception while compiling log formatter")
            QtWidgets.QMessageBox.critical(
                self,
                "Monal Log Viewer | ERROR",
                "Exception in formatter code:\n%s: %s" % (str(type(e).__name__), str(e)),
                QtWidgets.QMessageBox.Ok
            )
            return

    def compileLogFormatter(self, code):
        # compile our code by executing it
        loc = {}
        exec(code, {}, loc)
        if "formatter" not in loc or not callable(loc["formatter"]):
            logger.error("Formatter code did not evaluate to formatter() function!")
            raise RuntimeError("Log formatter MUST define a function following this signature: formatter(e, **g)")
        # bind all local variables (code imported, other defined functions etc.) onto our log formatter to be used later
        return functools.partial(loc["formatter"], **loc)

    @catch_exceptions(logger=logger)
    def inspectLine(self, *args):
        if len(self.uiWidget_listView.selectedIndexes()) != 0:
            if self.currentDetailIndex != self.uiWidget_listView.selectedIndexes()[0].row():
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
                
                selectedEntry = self.rawlog[self.uiWidget_listView.selectedIndexes()[0].row()].get("data")
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
                self.currentDetailIndex = self.uiWidget_listView.selectedIndexes()[0].row()
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
        self.uiWidget_listView.clear()
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
            "color": {},
            "staticLineWrap": SettingsSingleton()["staticLineWrap"],
            "font": SettingsSingleton().getQFont(),
            "formatter": SettingsSingleton().getCurrentFormatterCode(),
            "style": SettingsSingleton()["uiStyle"]
        }
        for colorName in SettingsSingleton().getColorNames():
            preInstance["color"][colorName] = SettingsSingleton().getQColorTuple(colorName)
        
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
        if len(self.uiWidget_listView.selectedIndexes()) > 0:
            self.search.resetStartIndex(self.uiWidget_listView.selectedIndexes()[0].row())
    
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
            if self.uiWidget_listView.selectedIndexes()[0].row() != self.search.getPosition:
                self.search.resetStartIndex(self.uiWidget_listView.selectedIndexes()[0].row())
        else:
            self._prepareSearch()   # create search instance (to be bound below)
        
        result = None
        if self.search != None:
            result = func(self.search)  # bind self (first arg) using our (newly created) self.search
            logger.info("Current search result in line (%s): %s" % (str(self.search.getStatus()), str(result)))
            self.setComboboxStatusColor(self.uiCombobox_searchInput, self.search.getStatus())

        if result != None:
            self.uiWidget_listView.setCurrentRow(result)
            self.uiWidget_listView.setFocus()
        
        self._updateStatusbar()

    def _prepareSearch(self):
        query = self.uiCombobox_searchInput.currentText().strip()

        progressbar, update_progressbar = self.progressDialog("Searching...", query, True)
        try:
            # let our new search begin at the currently selected line (if any)
            startIndex = 0       # if no logline is selected, let the search implementation begin at our list start
            if len(self.uiWidget_listView.selectedIndexes()) > 0:
                startIndex = self.uiWidget_listView.selectedIndexes()[0].row()
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
            if len(self.uiWidget_listView.selectedIndexes()) != 0:
                currentSelectetLine = self.uiWidget_listView.selectedIndexes()[0].row()
                
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
                self.uiWidget_listView.scrollToItem(self.rawlog[currentSelectetLine]["uiItem"], QtWidgets.QAbstractItemView.PositionAtCenter)

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
        if len(self.uiWidget_listView.selectedIndexes()) != 0:
            selectedLine = self.uiWidget_listView.selectedIndexes()[0].row()

        progressbar, update_progressbar = self.progressDialog("Filtering...", query, True)
        error = None
        visibleCounter = 0
        filterMapping = {}
        for rawlogPosition in range(len(self.rawlog)):
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
            self.rawlog[rawlogPosition]["uiItem"].setHidden(hidden)
        
        if self.currentDetailIndex != None and self.rawlog[self.currentDetailIndex]["uiItem"].isHidden():
            self.hideInspectLine()

        progressbar.hide()

        self.toggleUiItems()

        # scroll to selected line, if still visible or to next visible line, if not
        # (if there is no next visible line, scroll to previous visible line)
        if selectedLine != None:
            found = False
            for index in range(selectedLine, len(self.rawlog), 1):
                if self.rawlog[index]["uiItem"].isHidden() == False:
                    self.uiWidget_listView.scrollToItem(self.rawlog[index]["uiItem"], QtWidgets.QAbstractItemView.PositionAtCenter)
                    found = True
                    break 
            if not found:
                for index in range(len(self.rawlog)-1, selectedLine, -1):
                    if self.rawlog[index]["uiItem"].isHidden() == False:
                        self.uiWidget_listView.scrollToItem(self.rawlog[index]["uiItem"], QtWidgets.QAbstractItemView.PositionAtCenter)
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
        if len(self.uiWidget_listView.selectedIndexes()) == 0 or rowIndex != self.uiWidget_listView.selectedIndexes()[0].row():
            self.uiWidget_listView.setCurrentRow(rowIndex)
    
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
        for index in range(len(self.rawlog)):
            if not self.rawlog[index]["uiItem"].isHidden():
                self.uiWidget_listView.setCurrentRow(index)
                #self.statusbar.showDynamicText(str("Done ✓ | Switched to first row: %d" % index))
                break

    @catch_exceptions(logger=logger)
    def goToLastRow(self, *args):
        # set last row as current row 
        for index in range(len(self.rawlog)-1, -1, -1):
            self.uiWidget_listView.setCurrentRow(index)
            #self.statusbar.showDynamicText(str("Done ✓ | Switched to last row: %d" % index))
            break

    @catch_exceptions(logger=logger)
    def goToFirstRowInViewport(self, *args):
        if len(self.uiWidget_listView.selectedIndexes()) == 0:
            return;
        lastIndex = self.uiWidget_listView.selectedIndexes()[0].row()
        # Counts backwards from the current entry
        for index in range(self.uiWidget_listView.selectedIndexes()[0].row(), -1, -1):
            # If the item is not fully visible (e.g. y-position is not in our viewport anymore),
            # the previous one must have been the last one in our viewport --> use that
            visualItemRect = self.uiWidget_listView.visualItemRect(self.rawlog[index]["uiItem"])
            if visualItemRect.y() < 0:
                break
            else:
                lastIndex = index
        self.uiWidget_listView.setCurrentRow(lastIndex)
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the first line in the viewport: %d" % lastIndex))

    @catch_exceptions(logger=logger)
    def goToLastRowInViewport(self, *args):
        if len(self.uiWidget_listView.selectedIndexes()) == 0:
            return;
        lastIndex = self.uiWidget_listView.selectedIndexes()[0].row()
        # Counts upwards from the current entry
        for index in range(self.uiWidget_listView.selectedIndexes()[0].row(), len(self.rawlog)):
            # If the item is not fully visible (e.g. y-position + height is not in our viewport anymore),
            # the previous one must have been the last one in our viewport --> use that
            visualItemRect = self.uiWidget_listView.visualItemRect(self.rawlog[index]["uiItem"])
            if visualItemRect.y() + visualItemRect.height() > self.uiWidget_listView.height():
                break
            else:
                lastIndex = index
        self.uiWidget_listView.setCurrentRow(lastIndex)
        #self.statusbar.showDynamicText(str("Done ✓ | Switched to the last line in the viewport: %d" % lastIndex))
    
    def cancelFilter(self):
        for index in range(len(self.rawlog)):
            if self.rawlog[index]["uiItem"].isHidden():
                self.rawlog[index]["uiItem"].setHidden(False)
            # this slows down significantly
            #update_progressbar(index, len(self.rawlog))
        self.currentFilterQuery = None
    
    @catch_exceptions(logger=logger)
    def pushStack(self, *args):
        selectedLine = None
        if self.uiWidget_listView.selectedIndexes():
            selectedLine = self.uiWidget_listView.selectedIndexes()[0].row()

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
        #self.statusbar.showDynamicText("State saved ✓")
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
                self.uiWidget_listView.setCurrentRow(stack["search"]["currentLine"])
                self.search = stack["search"]["instance"]
                self.searchNext()
                self.searchPrevious()

        # unpacking goToRow
        if stack["goToRow"]["isOpen"]:
            self.uiFrame_goToRow.show()
            self.uiSpinBox_goToRow.setValue(stack["goToRow"]["currentInt"])
                
        # unpacking details
        if stack["detail"]["isOpen"]:
            self.uiWidget_listView.setCurrentRow(stack["detail"]["currentDetailIndex"])
            self.inspectLine()
            self.uiTable_characteristics.setFixedHeight(stack["detail"]["size"])
            if stack["detail"]["size"] == 0:
                self.uiTable_characteristics.setFixedHeight(800)

        # unpacking selected items and scroll position
        if stack["selectedLine"]:
            self.uiWidget_listView.setCurrentRow(stack["selectedLine"])
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
                len([item for item in self.rawlog if not item["uiItem"].isHidden()]),
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

        def rebuildFormatter():
            formatter = self.createFormatter()

            ignoreError = False
            for entry in self.rawlog:
                try:
                    entry["data"]["__formattedMessage"] = self.createFormatterText(formatter, entry["data"], ignoreError)
                except Exception as e:
                    entry["data"]["__formattedMessage"] = "E R R O R"
                    ignoreError = True
                entry["uiItem"].setText(helpers.wordWrapLogline(entry["data"]["__formattedMessage"]))
                rebuildFont(entry)
                rebuildColor(entry)
            
        def rebuildColor(entry):
            colorName = self.logflag2colorMapping[entry["data"]["flag"]]
            fg, bg = SettingsSingleton().getQColorTuple(colorName)
            if fg != preInstance["color"][colorName][0] or bg != preInstance["color"][colorName][1]:
                entry["uiItem"].setForeground(fg)
                if bg == None:
                    bg = QtGui.QBrush()     # default color (usually transparent)
                entry["uiItem"].setBackground(bg)
                            

        def rebuildFont(item):
            item["uiItem"].setFont(SettingsSingleton().getQFont())
            
        rebuildCombobox(self.uiCombobox_filterInput)
        rebuildCombobox(self.uiCombobox_searchInput)

        if preInstance["style"] != SettingsSingleton()["uiStyle"]:
            sharedUiHelpers.applyStyle(SettingsSingleton()["uiStyle"])

        if self.file != None:
            if preInstance["formatter"] != SettingsSingleton().getCurrentFormatterCode():
                rebuildFormatter()
            else:
                if preInstance["staticLineWrap"] != SettingsSingleton()["staticLineWrap"]:
                    for entry in range(len(self.rawlog)):
                        self.rawlog[entry]["uiItem"].setText(helpers.wordWrapLogline(self.rawlog[entry]["data"]["__formattedMessage"]))
                if preInstance["font"] != SettingsSingleton().getQFont():
                    for item in self.rawlog:
                        rebuildFont(item)
                for entry in self.rawlog:
                    rebuildColor(entry)
    
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
            data = self.rawlog[self.uiWidget_listView.selectedIndexes()[0].row()]["data"]["__formattedMessage"]
        if self.uiTable_characteristics.hasFocus():
            data = self.uiTable_characteristics.currentItem().text()
        
        if data != None:
            # copy to clipboard
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.clear(mode=clipboard.Clipboard)
            clipboard.setText(data, mode=clipboard.Clipboard)
            self.statusbar.showDynamicText(str("Done ✓ | Copied to clipboard"))
