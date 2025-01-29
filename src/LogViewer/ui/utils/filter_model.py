from LogViewer.storage import SettingsSingleton
from LogViewer.utils import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, sourceModel, parent=None):
        super().__init__(sourceModel, parent, handledSignals=[])
        self.clearFilter()

        self.rowsAboutToBeInserted.connect(self.processRowsAboutToBeInserted)
        self.rowsInserted.connect(self.processRowsInserted)

    def processRowsAboutToBeInserted(self):
        self.start = self.sourceModel().rowCount(None)

    def processRowsInserted(self):
        self.filterNewUpdEntries(self.start)

    def rowCount(self, index):
        return self.visibleCounter
    
    def isRowVisible(self, index):
        if index < 0 or index >= self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index)
    
    def filterNewUpdEntries(self, start):
        self.filterTemplate(self.query, start=start)
    
    def filter(self, query, update_progressbar=None):
        self.query = query
        self.visibleCounter = 0   

        self._initVisibilityList()
        return self.filterTemplate(self.query, start=0, update_progressbar=update_progressbar)

    def filterTemplate(self, query, start=0, update_progressbar=None):
        error = None

        for rawlogPosition in range(start, self.sourceModel().rowCount(None)):
            result = matchQuery(query, self.sourceModel().rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            if result["status"] == QueryStatus.QUERY_OK:
                self._addToVisibilityList(rawlogPosition, result["matching"])
            else:
                error = result["error"]
                self._addToVisibilityList(rawlogPosition, False)

            self.visibleCounter += 1 if result["matching"] else 0
            if update_progressbar != None:
                if update_progressbar(rawlogPosition, self.sourceModel().rowCount(None)) == True:
                    self.clearFilter()
                    break
        visibilityList = self._sealVisibilityList(rawlogPosition)

        if error != None:
            self.clearFilter()
            return (error, self.visibleCounter) 

        for item in visibilityList[-start:]:
            if item["visibility"]:
                self.beginInsertRows(self.parent(), item["start"], item["end"])
                for index in range(item["start"], item["end"]):
                    if self.proxyData.getVisibility(index) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endInsertRows()                    
            else:
                self.beginRemoveRows(self.parent(), item["start"], item["end"])
                for index in range(item["start"], item["end"]):
                    if self.proxyData.getVisibility(index) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endRemoveRows()
                return (error, self.visibleCounter) 

        return (error, self.visibleCounter) 
    
    def clearFilter(self):
        # The query must be of string type
        self.query = "True"
        self.visibleCounter = self.sourceModel().rowCount(None)
        self.beginInsertRows(self.parent(), 0, self.visibleCounter+1)
        self.proxyData.clear(True)
        self.endInsertRows()
        self._initVisibilityList()
