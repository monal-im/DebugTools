from PyQt5 import QtCore

from .proxy_data import ProxyData

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(QtCore.QAbstractProxyModel):
    def __init__(self, baseModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(baseModel)
        self.proxyData = ProxyData(self)
        self.scrollbarData = {"top": 0, "bottom": 0, "triggeredProgramatically": False}

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
        return self.sourceModel().createIndex(nextVisibleRow, 0)

    def rowCount(self, index):
        return self.proxyData.getRowCount()

    def columnCount(self, index):
        return self.sourceModel().columnCount(index)
    
    def listView(self):
        return self.sourceModel().listView()
    
    def setVisible(self, start, end):
        self.beginInsertRows(self.index(start, 1), start, end);
        self.proxyData.setVisible(start, end)
        self.endInsertRows();

    def scrollbarMoved(self):
        # If triggeredProgramatically is True the scrollbar wasn't moved by the user and shouldn't load anymore rows
        # This is used for example by goToLastRow, which scrolls to the bottom 
        if self.scrollbarData["triggeredProgramatically"] != False:
            return
        
        topItem     = self.sourceModel().listView().indexAt(self.sourceModel().listView().viewport().contentsRect().topLeft()).row()
        topIndex    = self.mapToSource(self.createIndex(topItem, 0)).row()

        bottomItem  = self.sourceModel().listView().indexAt(self.sourceModel().listView().viewport().contentsRect().bottomLeft()).row()
        bottomIndex  = self.mapToSource(self.createIndex(bottomItem, 0)).row()

        self.changeTriggeredProgramatically(True)
        if self.scrollbarData["top"]-110 >= topIndex:
            self.setVisible(max(topIndex-150, 0), topIndex)
            self.scrollbarData = {"top": topIndex, "bottom": bottomIndex}

        if self.scrollbarData["bottom"]+110 <= bottomIndex:
            self.setVisible(bottomIndex, min(bottomIndex+150, self.sourceModel().rowCount(None)))
            self.scrollbarData = {"top": topIndex, "bottom": bottomIndex}
        self.changeTriggeredProgramatically(False)

    def changeTriggeredProgramatically(self, value):
        self.scrollbarData["triggeredProgramatically"] = value