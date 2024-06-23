from LogViewer.storage import SettingsSingleton
from LogViewer.utils import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, sourceModel, parent=None):
        super().__init__(sourceModel, parent)
        self.proxyData.clear(True)
        self.visibleCounter = self.sourceModel().rowCount(None)

    def clearFilter(self):
        start = self.proxyData.getNextIndexWithState(self.createIndex(0, 0))
        end = self.proxyData.getPreviousIndexWithState(self.createIndex(self.sourceModel().rowCount(None), 0))
        self.beginInsertRows(self.createIndex(0, 0), start, end)
        self.proxyData.clear(True)
        self.visibleCounter = self.sourceModel().rowCount(None)
        self.endInsertRows()

    def rowCount(self, index):
        return self.visibleCounter
    
    def isRowVisible(self, index):
        if index < 0 or index >= self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index, index+1)

    def filter(self, query, update_progressbar):
        self.visibleCounter = 0        
        error = None
        firstInvisibileRow = None
        lastInvisibileRow = self.sourceModel().rowCount(None)
        for rawlogPosition in range(self.sourceModel().rowCount(None)):
            result = matchQuery(query, self.sourceModel().rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            if result["status"] == QueryStatus.QUERY_OK:
                self.proxyData.setVisibilityAtIndex(rawlogPosition, result["matching"]) 
                if result["matching"]:
                    lastInvisibileRow = rawlogPosition
                    if firstInvisibileRow == None:
                        firstInvisibileRow = rawlogPosition
            else:
                error = result["error"]
                self.proxyData.setVisibilityAtIndex(rawlogPosition, False) # hide all entries having filter errors
                lastInvisibileRow = rawlogPosition
                if firstInvisibileRow == None:
                    firstInvisibileRow = rawlogPosition
            self.visibleCounter += 1 if result["matching"] else 0
            if update_progressbar(rawlogPosition, self.sourceModel().rowCount(None)) == True:
                self.cancelFilter()
                break

        firstInvisibileRow = firstInvisibileRow if firstInvisibileRow != None else 0
        self.beginRemoveRows(self.createIndex(0, 0), firstInvisibileRow, lastInvisibileRow)
        self.endRemoveRows()

        return (error, self.visibleCounter) 