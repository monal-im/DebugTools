from PyQt5 import QtCore

from .proxy_model import ProxyModel

import logging
logger = logging.getLogger(__name__)

class LazyItemModel(ProxyModel):
    def __init__(self, baseModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(baseModel)
        self.scrollbarData = {"top": 0, "bottom": 0, "triggeredProgramatically": False}
    
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

    def clear(self):
        self.beginRemoveRows(self.index(0, 1), 0, self.sourceModel().rowCount(None));
        self.proxyData.clear(False)
        self.endRemoveRows()