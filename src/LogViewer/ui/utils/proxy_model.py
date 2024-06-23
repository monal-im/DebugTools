from PyQt5 import QtCore

from .proxy_data import ProxyData

import logging
logger = logging.getLogger(__name__)

class ProxyModel(QtCore.QAbstractProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxyData = ProxyData(self)

    def parent(self, index):
        # this method logs errors if not implemented, so simply return an invalid index to make qt happy
        return QtCore.QModelIndex()
    
    def index(self, row, column, parent=None):
        # this method logs errors if not implemented and is needed for qt to show content
        return self.createIndex(row, column, parent)
    
    def mapFromSource(self, sourceIndex):
        # from rawlog index to proxy index
        nextVisibleProxyIndex = self.proxyData.getNextVisibleProxyIndex(sourceIndex)
        return self.createIndex(nextVisibleProxyIndex, 0)

    def mapToSource(self, proxyIndex):
        # from proxy index to rawlog index
        if not proxyIndex.isValid():
            return QtCore.QModelIndex()
        nextVisibleRow = self.proxyData.getNextVisibleIndex(proxyIndex.row())
        try:
            return self.sourceModel().createIndex(nextVisibleRow, 0)
        except:
            logger.exception(f" {nextVisibleRow = } {proxyIndex.row() = }")
            raise

    def rowCount(self, index):
        return self.proxyData.getRowCount()

    def columnCount(self, index):
        return self.sourceModel().columnCount(index)
    
    def listView(self):
        return self.sourceModel().listView()