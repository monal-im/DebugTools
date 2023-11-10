#!/usr/bin/python3

# file created at 25.06.2023

from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QStyle
import sys, os, functools
import textwrap

from storage import Rawlog, AbortRawlogLoading, SettingsSingleton
from utils import catch_exceptions, Search, QueryStatus, matchQuery, paths
from ui.utils import Completer, MagicLineEdit, Statusbar
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
        self.file = None

        self.search = None
        self.statusbar = Statusbar(self.uistatusbar_state)

        #???[lower] don't use these lists but a method that decides which element to enable/disable based on current state (e.g. various self.xxx vars)
        self.toggleUiActions = [self.uiAction_close, self.uiAction_export, self.uiAction_pushStack, 
                         self.uiAction_popStack, self.uiAction_search, self.uiAction_save]
        self.toggleUiButtons = [self.uiButton_previous, self.uiButton_next, self.uiButton_filterClear]
        self.toggleUiComboboxes = [self.uiCombobox_searchInput, self.uiCombobox_filterInput]
        self.toggleUiItems(False)
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

        self.uiWidget_listView.doubleClicked.connect(self.inspectLine)
        self.uiWidget_listView.itemSelectionChanged.connect(self.loglineSelectionChanged)
        self.uiTable_characteristics.hide()
        self.uiFrame_search.hide()
        self.uiAction_inspectLine.setData(False)

        self.uiTable_characteristics.doubleClicked.connect(self.pasteDetailItem)
        MagicLineEdit(self.uiCombobox_searchInput)
        MagicLineEdit(self.uiCombobox_filterInput)

        self.queryStatus2colorMapping = {
            QueryStatus.EOF_REACHED:    SettingsSingleton().getCssColor("combobox-eof_reached"),
            QueryStatus.QUERY_ERROR:    SettingsSingleton().getCssColor("combobox-query_error"),
            QueryStatus.QUERY_OK:       SettingsSingleton().getCssColor("combobox-query_ok"),
            QueryStatus.QUERY_EMPTY:    SettingsSingleton().getCssColor("combobox-query_empty"),
        }
        self.logflag2colorMapping = {v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}

        QtWidgets.QShortcut(QtGui.QKeySequence("ESC"), self).activated.connect(self.hideSearch)
        self.uiCombobox_searchInput.activated[str].connect(self.searchNext)

        self.uiButton_filterClear.clicked.connect(self.clearFilter)
        self.uiCombobox_filterInput.activated[str].connect(self.filter)

        QtWidgets.QApplication.instance().focusChanged.connect(self.focusChangedEvent)
        self.uiSplitter_inspectLine.splitterMoved.connect(functools.partial(SettingsSingleton().storeState, self.uiSplitter_inspectLine))
        SettingsSingleton().loadState(self.uiSplitter_inspectLine)

        self.uiAction_pushStack.triggered.connect(self.pushStack)
        self.uiAction_popStack.triggered.connect(self.popStack)
        self.stack = []

        self.currentDetailIndex = None
        self.currentFilterQuery = None
    
    def quit(self):
        sys.exit()

    def closeEvent(self, event):
        sys.exit()

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        SettingsSingleton().storeDimension(self)

    def toggleUiItems(self, switchBool):
        for item in self.toggleUiActions:
            item.setEnabled(switchBool)
        for item in self.toggleUiButtons:
            item.setEnabled(switchBool)
        for item in self.toggleUiComboboxes:
            item.setEnabled(switchBool)
        self.setEnabled = switchBool

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
        formatter = self.createFormatter()
        
        self.statusbar.setText("Loading File: '%s'..." % os.path.basename(file))
        self.rawlog = Rawlog()
        self.uiWidget_listView.clear()
        self.toggleUiItems(True)
        
        def loader(entry):
            itemFont = QtGui.QFont(SettingsSingleton().getFont(), SettingsSingleton().getFontSize())
            # directly warn about file corruptions when they happen to allow the user to abort the loading process
            # using the cancel button in the progressbar window
            if "__warning" in entry and entry["__warning"] == True:
                QtWidgets.QMessageBox.warning(self, "File corruption detected", entry["message"])

            formattedEntry = self.createFormatterText(formatter, entry)
            entry["__formattedMessage"] = formattedEntry
            
            # return None if our formatter filtered out that entry
            if formattedEntry == None:
                return None
            #??? code duplication!!
            item_with_color = "\n".join([textwrap.fill(line, SettingsSingleton()["staticLineWrap"],
                expand_tabs=False,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=True,
                break_on_hyphens=True,
                max_lines=None
            ) if len(line) > SettingsSingleton()["staticLineWrap"] else line for line in formattedEntry.strip().splitlines(keepends=False)])
            
            fg, bg = tuple(SettingsSingleton().getQColorTuple(self.logflag2colorMapping[entry["flag"]]))
            item_with_color = QtWidgets.QListWidgetItem(item_with_color)
            item_with_color.setFont(itemFont)
            item_with_color.setForeground(fg)
            if bg != None:
                item_with_color.setBackground(bg)
            return {"uiItem": item_with_color, "data": entry}

        progressbar, updateProgressbar = self.progressDialog("Opening File...", "Opening File: "+ file, True)
        # don't pretend something was loaded if the loading was aborted
        if self.rawlog.load_file(file, progress_callback=updateProgressbar, custom_load_callback=loader) != True:
            self.closeFile()        # reset our ui to a sane state
            progressbar.hide()
            return

        self.statusbar.setText("Rendering File: '%s'..." % file)
        progressbar.setLabelText("Rendering File: '%s'..." % file)
        progressbar.setCancelButton(None)       # disable cancel button when rendering our file
        QtWidgets.QApplication.processEvents()
        for index in range(len(self.rawlog)):
            self.uiWidget_listView.addItem(self.rawlog[index]["uiItem"])
        QtWidgets.QApplication.processEvents()
        progressbar.hide()

        self.file = file
        self.filesize = os.stat(file).st_size#??? don't use filesize for progress!
        self.statusbar.showDynamicText(str("Done ✓ | file opened: " + os.path.basename(file)))

        self.setCompleter(self.uiCombobox_filterInput)
        self.setCompleter(self.uiCombobox_searchInput)

        self._updateStatusbar()

        #??? don't filter after loading, but integrate filtering into loading!
        if self.uiCombobox_filterInput.currentText() != "":
            self.filter()
    
    def createFormatterText(self, formatter, entry):        
        try:
            # this will make sure the log formatter does not change our log entry, but it makes loading slower
            # formattedEntry = formatter({value: entry[value] for value in entry.keys()})
            return formatter(entry)
        except Exception as e:
            logger.exception("Exception while calling log formatter")
            QtWidgets.QMessageBox.critical(
                self,
                "Monal Log Viewer | ERROR", 
                "Exception in formatter code:\n%s: %s" % (str(type(e).__name__), str(e)),
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
        self.uiTable_characteristics.hide()
        self.uiTable_characteristics.hide()
        self.uiFrame_search.hide()
        self.file = None

        self.toggleUiItems(False)

    @catch_exceptions(logger=logger)
    def preferences(self, *args):
        preInstance = {"color": {}, "staticLineWrap": None, "font": None, "formatter": None}
        for colorName in SettingsSingleton().getColorNames():
            colorTuple = SettingsSingleton().getQColorTuple(colorName)
            if len(colorTuple) > 1:#??? why > 1? it's a coincidence that logline colors have >1 while other colors don't --> this will break as soon as we add other >1 colors somewhere else in this project!!
                preInstance["color"][colorName] = colorTuple
        preInstance["staticLineWrap"] = SettingsSingleton()["staticLineWrap"]
        preInstance["font"] = [SettingsSingleton().getFont(), SettingsSingleton().getFontSize()]
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
        if self.setEnabled == False:
            return
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
        if self.setEnabled == False:
            return
        
        query = self.uiCombobox_filterInput.currentText()

        result = matchQuery(query, self.rawlog)
        self.setComboboxStatusColor(self.uiCombobox_filterInput, result["status"])
        self.updateComboboxHistory(query, self.uiCombobox_filterInput)

        progressBar, update_progressbar = self.progressDialog("Filtering...", query)

        #??? BUG: (rawlogPosition / self.filesize) will not generate the correct percent value!! that's comparing apples with oranges!
        for rawlogPosition in range(len(self.rawlog)):
            self.rawlog[rawlogPosition]["uiItem"].setHidden(rawlogPosition not in result["entries"])
            update_progressbar(rawlogPosition, self.filesize)
        progressBar.hide()

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
    def progressDialog(self, title, label, hasCancelButton=False):
        progressBar = QtWidgets.QProgressDialog(label, "Cancel", 0, 100, self)
        progressBar.setWindowTitle(title)
        progressBar.setGeometry(200, 200, 650, 100)
        if not hasCancelButton:
            progressBar.setCancelButton(None)
        progressBar.setAutoClose(False)
        progressBar.setValue(0)

        # we need to do this because we can't write primitive datatypes from within our closure
        oldpercentage = {"value": 0}

        def update_progressbar(readsize, filesize):
            # cancel loading if the progress dialog was canceled
            if progressBar.wasCanceled():
                return True
            
            currentpercentage = int(readsize/filesize*100)
            if currentpercentage != oldpercentage["value"]:
                progressBar.setValue(currentpercentage)
                QtWidgets.QApplication.processEvents()
            oldpercentage["value"] = currentpercentage

        progressBar.show()
        return (progressBar, update_progressbar)
    
    def pushStack(self):
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

    def popStack(self):
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
            if len(SettingsSingleton().getComboboxHistory(combobox)) != combobox:
                combobox.clear()
                combobox.addItems(SettingsSingleton().getComboboxHistory(combobox))
                combobox.lineEdit().setText("")

        def rebuildFormatter():
            formatter = self.createFormatter()
            for index in range(len(self.rawlog)):#??? why index? just iterate over our entry directly instead of using self.rawlog[index] everywhere
                formattedEntry = self.createFormatterText(formatter, self.rawlog[index]["data"])
                self.rawlog[index]["data"]["__formattedMessage"] = formattedEntry

        def rebuildLineWrap():
            for entry in range(len(self.rawlog)):
                #??? code duplication!!
                uiItem = "\n".join([textwrap.fill(line, SettingsSingleton()["staticLineWrap"],
                    expand_tabs=False,
                    replace_whitespace=False,
                    drop_whitespace=False,
                    break_long_words=True,
                    break_on_hyphens=True,
                    max_lines=None
                ) if len(line) > SettingsSingleton()["staticLineWrap"]  else line for line in self.rawlog[entry]["data"]["__formattedMessage"].strip().splitlines(keepends=False)])
                #??? simply change text instead of recreating item! --> self.rawlog[entry]["uiItem"].setText()
                uiItem = QtWidgets.QListWidgetItem(uiItem)
                self.uiWidget_listView.takeItem(entry)
                self.uiWidget_listView.insertItem(entry, uiItem)
                self.rawlog[entry]["uiItem"] = uiItem

        def rebuildColor():
            #??? this is not performant at all: only iterate over self.rawlog and color names once!
            for colorName in SettingsSingleton().getColorNames():
                colorTuple = SettingsSingleton().getQColorTuple(colorName)
                if colorName in preInstance["color"] and colorTuple != preInstance["color"][colorName]:
                    for index in range(len(self.rawlog)):
                        uiItem = self.rawlog[index]["uiItem"]
                        if self.logflag2colorMapping[self.rawlog[index]["data"]["flag"]] == colorName:
                            fg, bg = tuple(SettingsSingleton().getQColorTuple(colorName))
                            uiItem.setForeground(fg)
                            if bg != None:
                                uiItem.setBackground(bg)

        def rebuildFont():
            for item in self.rawlog:
                item["uiItem"].setFont(QtGui.QFont(SettingsSingleton().getFont(), SettingsSingleton().getFontSize()))  

        rebuildCombobox(self.uiCombobox_filterInput)
        rebuildCombobox(self.uiCombobox_searchInput)

        if self.file != None:
            if preInstance["formatter"] != SettingsSingleton().getCurrentFormatterCode():
                #??? this is not performant and will iterate over self.rawlog multiple times!
                rebuildFormatter()#??? rebuildFormatter should integrate rebuildLineWrap
                rebuildLineWrap()
                rebuildFont()#??? not needed if only the formatter changed (and if setText() is used)
            elif preInstance["staticLineWrap"] != SettingsSingleton()["staticLineWrap"]:
                rebuildLineWrap()
            elif preInstance["font"] != [SettingsSingleton().getFont(), SettingsSingleton().getFontSize()]:
                rebuildFont()
            rebuildColor()#??? should be integrated into rebuildFormatter (except if the formatter did not change)
#??? files should end with an empty line
