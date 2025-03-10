from PyQt5 import QtWidgets, QtCore, QtGui
import functools
import inspect

from LogViewer.storage import SettingsSingleton
from LogViewer.utils import loader
import LogViewer.utils.helpers as helpers
from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

LRU_MAXSIZE = 1024*1024

class RawlogModel(QtCore.QAbstractListModel):
    updateStatusbar = QtCore.pyqtSignal()

    @catch_exceptions(logger=logger)
    def __init__(self, rawlog, parent=None, udpServer=None):
        super().__init__(parent)
        self.parent = parent
        self.rawlog = rawlog
        self.formatter = self.createFormatter()
        self.lastRowCount = 0
        self.ignoreError = False

        if udpServer != None:
            self.rawlog.finishInsertRows.connect(self.endAppendEntries)
            udpServer.newMessage.connect(self.beginAppendEntries)
            self.ignoreError = True
    
    @catch_exceptions(logger=logger)
    def reloadSettings(self):
        self.layoutAboutToBeChanged.emit()
        self.formatter = self.createFormatter()
        for entry in self.rawlog:
            if "__formattedMessage" in entry["data"]:
                del entry["data"]["__formattedMessage"]
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, "cache_parameters"):
                #logger.debug(f"Cache effects for {member.__name__}: {member.cache_info()}")
                member.cache_clear()
        self.layoutChanged.emit()
    
    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    @catch_exceptions(logger=logger)
    def _getQFont(self):
        return SettingsSingleton().getQFont()
    
    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    @catch_exceptions(logger=logger)
    def _getQColorTuple(self, index):
        entry = self.rawlog[index]["data"]
        try:
            for fieldName in SettingsSingleton().getFieldNames():
                if eval(SettingsSingleton().getLoglevel(fieldName), {
                    "true" : True,
                    "false": False,
                }, entry):
                    return SettingsSingleton().getLoglevelQColorTuple(fieldName)
        except:
            pass
        return (QtGui.QColor(0, 0, 0), None)
    
    @catch_exceptions(logger=logger)
    def headerData(self, *args):
        return None
    
    @functools.lru_cache(maxsize=LRU_MAXSIZE, typed=True)
    @catch_exceptions(logger=logger)
    def data(self, index, role):
        if index.isValid() or (0 <= index.row() < len(self.rawlog)):
            if role == QtCore.Qt.DisplayRole:
                entry = self.rawlog[index.row()]
                if "__formattedMessage" not in entry["data"]:
                    try:
                        formattedEntry = self.createFormatterText(self.formatter, entry["data"], ignoreError=self.ignoreError)
                        entry["data"]["__formattedMessage"] = formattedEntry
                    except:
                        # ignore error and return empty string (already catched and displayed to user by createFormatterText() itself)
                        return ""
                else:
                    formattedEntry = entry["data"]["__formattedMessage"]
                return helpers.wordWrapLogline(formattedEntry, SettingsSingleton()["staticLineWrap"])
            elif role == QtCore.Qt.FontRole:
                return self._getQFont()
            elif role == QtCore.Qt.BackgroundRole:
                fg, bg = self._getQColorTuple(index.row())
                if bg == None:
                    bg = QtGui.QBrush()     # default color (usually transparent)
                return bg
            elif role == QtCore.Qt.ForegroundRole:
                fg, bg = self._getQColorTuple(index.row())
                return fg
        else:
            logger.info(f"Data called with invalid index: {index.row()}")
        return None
    
    @catch_exceptions(logger=logger)
    def rowCount(self, index):
        return len(self.rawlog)

    @catch_exceptions(logger=logger)
    def columnCount(self, index):
        return 1

    def createFormatterText(self, formatter, entry, ignoreError=False):        
        try:
            # this will make sure the log formatter does not change our log entry, but it makes loading slower
            # formattedEntry = formatter({value: entry[value] for value in entry.keys()})
            
            return formatter(entry)
        except Exception as e:
            logger.exception("Exception while calling log formatter for: %s" % entry)
            if not ignoreError:
                QtWidgets.QMessageBox.critical(
                    self.parent,
                    "Monal Log Viewer | ERROR", 
                    "Exception in formatter code:\n%s: %s\n%s" % (str(type(e).__name__), str(e), entry),
                    QtWidgets.QMessageBox.Ok
                )
            raise

    def createFormatter(self):
        # first of all: try to compile our log formatter code and abort, if this isn't generating a callable formatter function
        try:
            return self.compileLogFormatter(SettingsSingleton().getCurrentFormatterCode())
        except Exception as e:
            logger.exception("Exception while compiling log formatter")
            if not self.ignoreError:
                QtWidgets.QMessageBox.critical(
                    self.parent,
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
    def listView(self):
        return self.parent

    @catch_exceptions(logger=logger)
    def setCurrentRow(self, row):
        index = self.createIndex(row, 0)
        logger.info(f"Setting row {row} to index {index.row()}")
        self.listView().setCurrentIndex(index)

    @catch_exceptions(logger=logger)
    def beginAppendEntries(self, entries):
        newRowCount = len(self.rawlog)+len(entries)
        self.beginInsertRows(self.createIndex(newRowCount - len(self.rawlog), 0), len(self.rawlog), newRowCount)
        self.rawlog.appendEntries(entries, custom_load_callback=loader)

    @catch_exceptions(logger=logger)
    def endAppendEntries(self):
        self.endInsertRows()
        self.updateStatusbar.emit()
