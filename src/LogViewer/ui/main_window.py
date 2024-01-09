#!/usr/bin/python3

# file created at 25.06.2023

from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os, functools
import textwrap

from LogViewer.storage import SettingsSingleton
from LogViewer.utils import Search, QueryStatus, matchQuery
from LogViewer.utils.version import VERSION
from .utils import Completer, MagicLineEdit, Statusbar, StyleManager
from .preferences_dialog import PreferencesDialog
from shared.storage import Rawlog, AbortRawlogLoading
from shared.ui.about_dialog import AboutDialog
from shared.ui.utils import UiAutoloader
from shared.utils import catch_exceptions, Paths
from shared.utils.constants import LOGLEVELS
                
import logging
logger = logging.getLogger(__name__)

@UiAutoloader
@StyleManager.styleDecorator
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        SettingsSingleton().loadDimensions(self)
        self.rawlog = Rawlog()
        self.file = None

        self.search = None
        self.statusbar = Statusbar(self.uiStatusbar_main, self.uiMenuBar_main)

        self.toggleUiItems()
        self.selectedCombobox = self.uiCombobox_filterInput

        self.uiButton_previous.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowBack")))
        self.uiButton_previous.clicked.connect(self.searchPrevious)
        self.uiButton_next.setIcon(self.style().standardIcon(getattr(QStyle, "SP_ArrowForward")))
        self.uiButton_next.clicked.connect(self.searchNext)

        self.uiAction_open.triggered.connect(self.openFileBrowser)
        self.uiAction_close.triggered.connect(self.closeFile)
        self.uiAction_quit.triggered.connect(self.quit)
        self.uiAction_preferences.triggered.connect(self.preferences)
        self.uiAction_search.triggered.connect(self.openSearchwidget)
        self.uiAction_export.triggered.connect(self.export)
        self.uiAction_save.triggered.connect(self.save)
        self.uiAction_inspectLine.triggered.connect(self.inspectLine)
        self.uiAction_about.triggered.connect(self.action_about)

        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiFrame_search.hide()

        self.uiTable_characteristics.doubleClicked.connect(self.pasteDetailItem)
        MagicLineEdit(self.uiCombobox_searchInput)
        MagicLineEdit(self.uiCombobox_filterInput)

        self.uiCombobox_searchInput.currentTextChanged.connect(self.uiCombobox_searchInputChanged)
        self.uiCombobox_filterInput.currentTextChanged.connect(self.uiCombobox_filterInputChanged)

        self.queryStatus2colorMapping = {
            QueryStatus.EOF_REACHED:    SettingsSingleton().getCssColor("combobox-eof_reached"),
            QueryStatus.QUERY_ERROR:    SettingsSingleton().getCssColor("combobox-query_error"),
            QueryStatus.QUERY_OK:       SettingsSingleton().getCssColor("combobox-query_ok"),
            QueryStatus.QUERY_EMPTY:    SettingsSingleton().getCssColor("combobox-query_empty"),
        }
        self.logflag2colorMapping = {v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}

        self.loadComboboxHistory(self.uiCombobox_searchInput)
        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearch)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

        self.loadComboboxHistory(self.uiCombobox_filterInput)
        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)
        self.uiSplitter_inspectLine.splitterMoved.connect(functools.partial(SettingsSingleton().storeState, self.uiSplitter_inspectLine))
        SettingsSingleton().loadState(self.uiSplitter_inspectLine)

        self.uiAction_pushStack.triggered.connect(self.pushStack)
        self.uiAction_popStack.triggered.connect(self.popStack)
        self.stack = []
   
        self.currentFilterQuery = None

        self.hideInspectLine()

    def quit(self):
        sys.exit()

    def closeEvent(self, event):
        sys.exit()

    @catch_exceptions(logger=logger)
    def action_about(self, *args):
        logger.info("Showing About Dialog...")
        self.about = AboutDialog(VERSION)
        self.about.show()
        result = self.about.exec_()

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
        self.uiButton_previous.setEnabled(self.file != None and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_next.setEnabled(self.file != None and len(self.uiCombobox_searchInput.currentText().strip()) != 0)
        self.uiButton_filterClear.setEnabled(self.file != None and len(self.uiCombobox_filterInput.currentText().strip()) != 0)
        self.uiCombobox_searchInput.setEnabled(self.file != None)
        self.uiCombobox_filterInput.setEnabled(self.file != None)

    def export(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this text logfile", "", "Compressed logfile (*.log.gz)(*.log.gz);;Logfile (*.log)(*.log);;All files (*)")
            if check:
                status = self.rawlog.export_file(file, custom_store_callback = lambda entry: entry["data"] if not entry["uiItem"].isHidden() else None)
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Log export was successful"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not export log"))

    def save(self):
        if self.rawlog:
            file, check = QtWidgets.QFileDialog.getSaveFileName(None, "Choose where to save this rawlog logfile", "", "Compressed Monal rawlog (*.rawlog.gz)(*.rawlog.gz);;Monal rawlog (*.rawlog)(*.rawlog);;All files (*)")
            if check:
                status = self.rawlog.store_file(file, custom_store_callback = lambda entry: entry["data"] if not entry["uiItem"].isHidden() else None)
                if status:
                    self.statusbar.showDynamicText(str("Done ✓ | Rawlog saved successfully"))
                else:
                    self.statusbar.showDynamicText(str("Error ✗ | Could not save warlow"))   

    def setCompleter(self, combobox):
        wordlist = self.rawlog.getCompleterList(lambda entry: entry["data"])
        wordlist += ["True", "False", "true", "false", "__index", "__rawlog"] + list(LOGLEVELS.keys())

        completer = Completer(wordlist, self)
        completer.setCompletionMode(Completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combobox.setCompleter(completer)

    @catch_exceptions(logger=logger)
    def openFileBrowser(self, *args):
        file, check = QtWidgets.QFileDialog.getOpenFileName(None, "Open rawlog logfile", "", "Monal rawlog (*.rawlog.gz *.rawlog)(*.rawlog.gz *.rawlog);;All files (*)")
        if check:
            self.openLogFile(file)

    def openLogFile(self, file):
        self.closeFile()
        
        self.statusbar.setText("Loading File: '%s'..." % os.path.basename(file))
        formatter = self.createFormatter()
        self.rawlog = Rawlog()
        
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
            
            item_with_color = self.wordWrapLogline(formattedEntry)   
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
        filterQuery = self.uiCombobox_filterInput.currentText().strip()
        for index in range(len(self.rawlog)):
            self.uiWidget_listView.addItem(self.rawlog[index]["uiItem"])
            if len(filterQuery) != 0:
                result = matchQuery(filterQuery, self.rawlog, index, usePython=SettingsSingleton()["usePythonFilter"])
                if result["status"] != QueryStatus.QUERY_ERROR:
                    self.rawlog[index]["uiItem"].setHidden(not result["matching"])
                else:
                    error = result["error"]
                visibleCounter += 1 if result["matching"] else 0
        if len(filterQuery) != 0:
            self.checkFilterResult(error, visibleCounter)
        QtWidgets.QApplication.processEvents()
        progressbar.hide()

        self.file = file
        self.statusbar.showDynamicText(str("Done ✓ | file opened: " + os.path.basename(file)))

        self.setCompleter(self.uiCombobox_filterInput)
        self.setCompleter(self.uiCombobox_searchInput)

        self._updateStatusbar()
        self.toggleUiItems()
    
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
                                "name": path[0] + "".join(map(lambda value: "[%s]" % self.pythonize(value), path[1:])),
                                "value": self.pythonize(value)
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
        self.hideSearch()
        self.selectedCombobox = self.uiCombobox_filterInput
        self.file = None
        self.currentFilterQuery = None
        self.toggleUiItems()
        self.hideInspectLine()

    @catch_exceptions(logger=logger)
    def preferences(self, *args):
        preInstance = {"color": {}, "staticLineWrap": None, "font": None, "formatter": None, "style": SettingsSingleton()["uiStyle"]}
        for colorName in SettingsSingleton().getColorNames():
            preInstance["color"][colorName] = SettingsSingleton().getQColorTuple(colorName)
        preInstance["staticLineWrap"] = SettingsSingleton()["staticLineWrap"]
        preInstance["font"] = SettingsSingleton().getQFont()
        preInstance["formatter"] = SettingsSingleton().getCurrentFormatterCode()
        
        self.preferencesDialog = PreferencesDialog()
        self.preferencesDialog.show()
        result = self.preferencesDialog.exec_()
        if result:
            self.rebuildUi(preInstance)

    @catch_exceptions(logger=logger)
    def openSearchwidget(self, *args):
        self.uiFrame_search.show()
        self.uiCombobox_searchInput.setFocus()  

    @catch_exceptions(logger=logger)
    def setComboboxStatusColor(self, combobox, status):
        combobox.setStyleSheet("background-color: %s" % self.queryStatus2colorMapping[status])

    def searchNext(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.next)

    def searchPrevious(self):
        # use unbound function, self will be bound in _search() later on after the instance was created
        self._search(Search.previous)

    def _search(self, func):
        self._prepareSearch()   # create search instance (to be bound below)
        
        startIndex = None       # if no logline is selected, let the search implementation continue where it left of
        if len(self.uiWidget_listView.selectedIndexes()) > 0:
            startIndex = self.uiWidget_listView.selectedIndexes()[0].row()
        result = func(self.search, startIndex)  # bind self (first arg) using our (newly created) self.search

        logger.info("Current search result in line: %s" % str(result))
        if result != None:
            self.uiWidget_listView.setCurrentRow(result)
        self.setComboboxStatusColor(self.uiCombobox_searchInput, self.search.getStatus())

        self._updateStatusbar()

    def _prepareSearch(self):
        query = self.uiCombobox_searchInput.currentText().strip()
        if self.search != None:
            if self.search.getQuery() == query:
                return
        progressbar, update_progressbar = self.progressDialog("Searching...", query)
        self.search = Search(self.rawlog, query, update_progressbar)
        progressbar.hide()
        self.updateComboboxHistory(query, self.uiCombobox_searchInput)
    
    @catch_exceptions(logger=logger)
    def hideSearch(self):
        self.uiFrame_search.hide()
        self.search = None
    
    def clearFilter(self):
        self.uiCombobox_filterInput.setCurrentText("")
        self.uiCombobox_filterInput.setStyleSheet("")

        progressbar, update_progressbar = self.progressDialog("Clearing filter...", "")
        self._updateStatusbar()
        QtWidgets.QApplication.processEvents()
        for index in range(len(self.rawlog)):
            if self.rawlog[index]["uiItem"].isHidden():
                self.rawlog[index]["uiItem"].setHidden(False)
            # this slows down significantly
            #update_progressbar(index, len(self.rawlog))
        progressbar.hide()
        self.currentFilterQuery = None
        self.statusbar.showDynamicText("Filter cleared")
        self._updateStatusbar()
    
    @catch_exceptions(logger=logger)
    def filter(self, *args):
        query = self.uiCombobox_filterInput.currentText().strip()
        if query == self.currentFilterQuery:
            return
        
        progressbar, update_progressbar = self.progressDialog("Filtering...", query)
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
            update_progressbar(rawlogPosition, len(self.rawlog))
        self.checkFilterResult(error, visibleCounter)
        
        progressbar.setLabelText("Rendering Filter...")
        QtWidgets.QApplication.processEvents()
        for rawlogPosition in range(len(self.rawlog)):
            self.rawlog[rawlogPosition]["uiItem"].setHidden(filterMapping[rawlogPosition])

        
        if self.currentDetailIndex != None and self.rawlog[self.currentDetailIndex]["uiItem"].isHidden():
            self.hideInspectLine()

        progressbar.hide()
        
        self.updateComboboxHistory(query, self.uiCombobox_filterInput)
        self.currentFilterQuery = query

        self._updateStatusbar()
    
    def checkFilterResult(self, error = None, visibleCounter = 0):
        if error != None:
            QtWidgets.QMessageBox.critical(
                self,
                "Monal Log Viewer | ERROR", 
                "Exception in filter:\n%s: %s" % (str(type(error).__name__), str(error)),
                QtWidgets.QMessageBox.Ok
            )
            self.setComboboxStatusColor(self.uiCombobox_filterInput, QueryStatus.QUERY_ERROR)
        elif visibleCounter == 0:
            self.setComboboxStatusColor(self.uiCombobox_filterInput, QueryStatus.QUERY_EMPTY)
        else:
            self.setComboboxStatusColor(self.uiCombobox_filterInput, QueryStatus.QUERY_OK)

    def updateComboboxHistory(self, query, combobox):
        if query.strip() == "":
            return

        if combobox.findText(query) != -1:
            combobox.removeItem(combobox.findText(query))
        combobox.insertItem(0, query)
        combobox.setCurrentIndex(0)
        SettingsSingleton().setComboboxHistory(combobox, [combobox.itemText(i) for i in range(combobox.count())])

    @catch_exceptions(logger=logger)
    def uiCombobox_searchInputChanged(self, *args):
        self.toggleUiItems()

    @catch_exceptions(logger=logger)
    def uiCombobox_filterInputChanged(self, *args):
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
    def pushStack(self, *args):
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
        self.toggleUiItems()
    
    @catch_exceptions(logger=logger)
    def popStack(self, *args):
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
            if stack["search"]["instance"]:
                self.search = stack["search"]["instance"]
                self.searchNext()
                self.searchPrevious()

        #unpacking filter
        self.uiCombobox_filterInput.setCurrentText(stack["filter"]["currentText"])
        if stack["filter"]["currentFilterQuery"]:
            self.filter()

        self.statusbar.showDynamicText("State loaded ✓")
        self.toggleUiItems()

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

    @catch_exceptions(logger=logger)
    def rebuildUi(self, preInstance):
        def rebuildCombobox(combobox):
            if len(SettingsSingleton().getComboboxHistory(combobox)) != len([combobox.itemText(i) for i in range(combobox.count())]):
                currentText = combobox.lineEdit().text()
                combobox.clear()
                combobox.addItems(SettingsSingleton().getComboboxHistory(combobox))
                combobox.lineEdit().setText(currentText)

                if currentText not in SettingsSingleton().getComboboxHistory(combobox):
                    combobox.insertItem(0, currentText)
                    SettingsSingleton().setComboboxHistory(combobox, [combobox.itemText(i) for i in range(combobox.count())])

        def rebuildFormatter():
            formatter = self.createFormatter()

            ignoreError = False
            for entry in self.rawlog:
                try:
                    entry["data"]["__formattedMessage"] = self.createFormatterText(formatter, entry["data"], ignoreError)
                except Exception as e:
                    entry["data"]["__formattedMessage"] = "E R R O R"
                    ignoreError = True
                entry["uiItem"].setText(self.wordWrapLogline(entry["data"]["__formattedMessage"]))
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
            StyleManager.updateStyle(self)

        if self.file != None:
            if preInstance["formatter"] != SettingsSingleton().getCurrentFormatterCode():
                rebuildFormatter()
            else:
                if preInstance["staticLineWrap"] != SettingsSingleton()["staticLineWrap"]:
                    for entry in range(len(self.rawlog)):
                        self.rawlog[entry]["uiItem"].setText(self.wordWrapLogline(self.rawlog[entry]["data"]["__formattedMessage"]))
                if preInstance["font"] != SettingsSingleton().getQFont():
                    for item in self.rawlog:
                        rebuildFont(item)
                for entry in self.rawlog:
                    rebuildColor(entry)

    def wordWrapLogline(self, formattedMessage):
        uiItem = "\n".join([textwrap.fill(line, SettingsSingleton()["staticLineWrap"],
            expand_tabs=False,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=True,
            max_lines=None
        ) if len(line) > SettingsSingleton()["staticLineWrap"]  else line for line in formattedMessage.strip().splitlines(keepends=False)])
        return uiItem
    
    def loadComboboxHistory(self, combobox):
        combobox.clear()
        combobox.addItems(SettingsSingleton().getComboboxHistory(combobox))
        combobox.lineEdit().setText("")
