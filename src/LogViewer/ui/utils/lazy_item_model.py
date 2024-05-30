from PyQt5 import QtWidgets, QtCore, QtGui

from .proxy_data import ProxyData

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(QtCore.QAbstractProxyModel):
    def __init__(self, rawlogModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(rawlogModel)
        self.proxyData = ProxyData(self)
        self.rawlogModel = rawlogModel

        #self.proxyData.setVisible(0, 100)
        #self.proxyData.setVisible(baseModel.realRowCount()-100, baseModel.realRowCount())

    def mapFromSource(self, sourceIndex):
        # from rawlog index to proxy index  
        return self.rawlogModel.createIndex(self.proxyData.getNextVisibleProxyIndex(sourceIndex), 0)

    def mapToSource(self, proxyIndex):
        # from proxy index to rawlog index
        if proxyIndex.row() == -1:
            return proxyIndex

        return self.rawlogModel.createIndex(self.proxyData.getNextVisibleIndex(proxyIndex.row()), 0)
    
    def data(self, index, role):
        source = self.mapToSource(index)
        if source.isValid():
            return source.data(role)
        return None
    
    def index(self, row, column, parent=None):
        res = self.rawlogModel.match(self.rawlogModel.index(0, 0), QtCore.Qt.DisplayRole, row, flags=QtCore.Qt.MatchExactly)
        if res:
            return res[0].sibling(res[0].row(), column)
        return self.createIndex(row, column)

    def rowCount(self, index):
        return self.proxyData.getRowCount()

    def columnCount(self, index):
        return 1
    
    def setProxyData(self, start, end):
        self.proxyData.setVisible(start, end)