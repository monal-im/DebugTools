from PyQt5 import QtCore

from .proxy_data import ProxyData

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(QtCore.QAbstractProxyModel):
    def __init__(self, rawlogModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(rawlogModel)
        self.proxyData = ProxyData(self)

    def mapFromSource(self, sourceIndex):
        # from rawlog index to proxy index  
        return self.createIndex(self.proxyData.getNextVisibleProxyIndex(sourceIndex), 0)

    def mapToSource(self, proxyIndex):
        # from proxy index to rawlog index
        if proxyIndex.row() == -1:
            return proxyIndex

        return self.sourceModel().createIndex(self.proxyData.getNextVisibleIndex(proxyIndex.row()), 0)
    
    def data(self, index, role):
        index = self.mapToSource(index)
        if index.isValid():
            # data(role) is called on index, because the index also holds the UiItem
            # Without this the uiItem would be blanc
            return index.data(role)
        return None
    
    def index(self, row, column, parent=None):
        # This function is needed to provide the right index for self.data()
        resultIndex = self.sourceModel().match(self.sourceModel().index(0, 0), QtCore.Qt.DisplayRole, row, flags=QtCore.Qt.MatchExactly)
        if resultIndex:
            return resultIndex[0].sibling(resultIndex[0].row(), column)
        return self.createIndex(row, column)

    def rowCount(self, index):
        return self.proxyData.getRowCount()

    def columnCount(self, index):
        return 1
    
    def setVisible(self, start, end):
        self.layoutAboutToBeChanged.emit()
        self.proxyData.setVisible(start, end)
        self.layoutChanged.emit()
