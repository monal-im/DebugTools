from PyQt5 import QtWidgets, QtCore, QtGui
import functools

from LogViewer.storage import SettingsSingleton
import LogViewer.utils.helpers as helpers
from shared.utils.constants import LOGLEVELS

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(QtCore.QAbstractListModel):
    def __init__(self, rawlog, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.loadedRowsCount = 0
        self.logflag2colorMapping = {v: "logline-%s" % k.lower() for k, v in LOGLEVELS.items()}
        self.rawlog = rawlog
        self.formatter = self.createFormatter()
    
    def canFetchMore(self, index):
        logger.info(f"canFetchMore called at index: {index.row()}")
        return self.loadedRowsCount < len(self.rawlog)
    
    def fetchMore(self, index):
        logger.info(f"fetchMore called at index: {index.row()}")
        itemsToFetch = min(len(self.rawlog) - self.loadedRowsCount, 10)
        if itemsToFetch <= 0:
            return
        
        self.beginInsertRows(index, self.loadedRowsCount, self.loadedRowsCount + itemsToFetch - 1);
        self.loadedRowsCount += itemsToFetch
        self.endInsertRows();
    
    def data(self, index, role):
        if index.isValid() or (0 <= index.row() < len(self.rawlog)):
            if role == QtCore.Qt.DisplayRole:
                #logger.info(f"Requesting DisplayRole: {index.row()}")
                entry = self.rawlog[index.row()]
                formattedEntry = self.createFormatterText(self.formatter, entry["data"])
                entry["data"]["__formattedMessage"] = formattedEntry
                return helpers.wordWrapLogline(formattedEntry)
            # elif role == QtCore.Qt.DecorationRole:
            #     logger.info(f"Requesting DecorationRole: {index.row()}")
            # elif role == QtCore.Qt.EditRole:
            #     logger.info(f"Requesting EditRole: {index.row()}")
            # elif role == QtCore.Qt.ToolTipRole:
            #     logger.info(f"Requesting ToolTipRole: {index.row()}")
            # elif role == QtCore.Qt.StatusTipRole:
            #     logger.info(f"Requesting StatusTipRole: {index.row()}")
            # elif role == QtCore.Qt.WhatsThisRole:
            #     logger.info(f"Requesting WhatsThisRole: {index.row()}")
            # elif role == QtCore.Qt.SizeHintRole:
            #     logger.info(f"Requesting SizeHintRole: {index.row()}")
            elif role == QtCore.Qt.FontRole:
                # logger.info(f"Requesting FontRole: {index.row()}")
                return SettingsSingleton().getQFont()
            # elif role == QtCore.Qt.TextAlignmentRole:
            #     logger.info(f"Requesting TextAlignmentRole: {index.row()}")
            elif role == QtCore.Qt.BackgroundRole:
                # logger.info(f"Requesting BackgroundRole: {index.row()}")
                entry = self.rawlog[index.row()]
                fg, bg = SettingsSingleton().getQColorTuple(self.logflag2colorMapping[entry["data"]["flag"]])
                if bg == None:
                    bg = QtGui.QBrush()     # default color (usually transparent)
                return bg
            # elif role == QtCore.Qt.BackgroundColorRole:
            #     logger.info(f"Requesting BackgroundColorRole: {index.row()}")
            elif role == QtCore.Qt.ForegroundRole:
                # logger.info(f"Requesting ForegroundRole: {index.row()}")
                entry = self.rawlog[index.row()]
                fg, bg = SettingsSingleton().getQColorTuple(self.logflag2colorMapping[entry["data"]["flag"]])
                return fg
            # elif role == QtCore.Qt.TextColorRole:
            #     logger.info(f"Requesting TextColorRole: {index.row()}")
            # elif role == QtCore.Qt.CheckStateRole:
            #     logger.info(f"Requesting CheckStateRole: {index.row()}")
            # elif role == QtCore.Qt.InitialSortOrderRole:
            #     logger.info(f"Requesting InitialSortOrderRole: {index.row()}")
            # elif role == QtCore.Qt.AccessibleTextRole:
            #     logger.info(f"Requesting AccessibleTextRole: {index.row()}")
            # elif role == QtCore.Qt.AccessibleDescriptionRole:
            #     logger.info(f"Requesting AccessibleDescriptionRole: {index.row()}")
            # else:
            #     logger.warning(f"Requesting unknown role {role}: {index.row()}")
        else:
            logger.info(f"data called with invalid index: {index.row()}")
        return None
    
    def rowCount(self, index):
        # logger.info(f"Returning row count at index: {index.row()}")
        return self.loadedRowsCount

    def columnCount(self, index):
        return 1
    
    def loadDataUpTo(self, index):
        itemsToFetch = index.row() - self.loadedRowsCount
        if itemsToFetch <= 0:
            return
        self.beginInsertRows(index, self.loadedRowsCount, self.loadedRowsCount + itemsToFetch - 1);
        self.loadedRowsCount += itemsToFetch
        self.endInsertRows();
    
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
            raise AbortRawlogLoading()       # abort loading

    def createFormatter(self):
        # first of all: try to compile our log formatter code and abort, if this isn't generating a callable formatter function
        try:
            return self.compileLogFormatter(SettingsSingleton().getCurrentFormatterCode())
        except Exception as e:
            logger.exception("Exception while compiling log formatter")
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
