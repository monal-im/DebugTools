import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, baseModel, parent=None):
        super().__init__(parent)
        self.setSourceModel(baseModel)
        self.proxyData.clear(True)
        self.rowCounter = self.sourceModel().rowCount(None)

    def setVisibility(self, filterList):
        self.beginRemoveRows(self.index(0, 1), 0, len(filterList))
        self.rowCounter  = 0
        for index in filterList:
            if not filterList[index]:
                self.rowCounter += 1
            self.proxyData.setVisibilityAtIndex(index, not filterList[index])
        self.endInsertRows()

    def clearFilter(self):
        self.proxyData.clear(True)
        self.rowCounter = self.sourceModel().rowCount(None)

    def rowCount(self, index):
        return self.rowCounter
    
    def isRowVisible(self, index):
        if index < 0 or index > self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index, index+1)