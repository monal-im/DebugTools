from PyQt5 import QtCore
import functools

from .proxy_data import ProxyData
from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

# this class only caches methods that return static values
class ProxyModel(QtCore.QAbstractProxyModel):
    @catch_exceptions(logger=logger)
    def __init__(self, sourceModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(sourceModel)
        self.proxyData = ProxyData(self)
        # proxy signals, too
        signals = [
            "columnsAboutToBeInserted", "columnsAboutToBeMoved", "columnsAboutToBeRemoved",
            "columnsInserted", "columnsMoved", "columnsRemoved", "dataChanged", "headerDataChanged",
            "layoutAboutToBeChanged", "layoutChanged", "modelAboutToBeReset", "modelReset",
            "rowsAboutToBeInserted", "rowsAboutToBeMoved", "rowsAboutToBeRemoved", "rowsInserted",
            "rowsMoved", "rowsRemoved",
        ]
        def emitter(signal, *args):
            logger.debug(f"Proxying signal '{signal}' from parent model with args: {args}")
            getattr(self, signal).emit(*args)
        
        for signal in signals:
            getattr(sourceModel, signal).connect(functools.partial(emitter, signal))

    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def parent(self, index):
        # this method logs errors if not implemented, so simply return an invalid index to make qt happy
        return QtCore.QModelIndex()
    
    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def index(self, row, column, parent=None):
        # this method logs errors if not implemented and is needed for qt to show content
        return self.createIndex(row, column, parent)
    
    @catch_exceptions(logger=logger)
    def mapFromSource(self, sourceIndex):
        # from rawlog index to proxy index
        return self.createIndex(self.proxyData.getNextVisibleProxyRow(sourceIndex.row()), 0)

    @catch_exceptions(logger=logger)
    def mapToSource(self, proxyIndex):
        # from proxy index to rawlog index
        if not proxyIndex.isValid():
            return QtCore.QModelIndex()
        nextVisibleRow = self.proxyData.getNextVisibleRow(proxyIndex.row())
        try:
            return self.sourceModel().createIndex(nextVisibleRow, 0)
        except:
            logger.exception(f"Exception with data: {nextVisibleRow = } {proxyIndex.row() = }")
            raise

    @catch_exceptions(logger=logger)
    def rowCount(self, index):
        return self.proxyData.getRowCount()

    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def columnCount(self, index):
        return self.sourceModel().columnCount(index)
    
    @functools.lru_cache(typed=True)
    @catch_exceptions(logger=logger)
    def listView(self):
        return self.sourceModel().listView()
