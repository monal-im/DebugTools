from LogViewer.storage import SettingsSingleton
from LogViewer.utils import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, sourceModel, parent=None):
        super().__init__(sourceModel, parent)
        self.clearFilter()
        self.visibilityList = []

    def rowCount(self, index):
        return self.visibleCounter
    
    def isRowVisible(self, index):
        if index < 0 or index >= self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index, index+1)

    def filter(self, query, update_progressbar):
        self.clearFilter()
        self.visibleCounter = 0        
        error = None

        for rawlogPosition in range(self.sourceModel().rowCount(None)):
            result = matchQuery(query, self.sourceModel().rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            if result["status"] == QueryStatus.QUERY_OK:
                self.addToVisibilityList(rawlogPosition, result["matching"])

            else:
                error = result["error"]
                self.addToVisibilityList(rawlogPosition, False)

            self.visibleCounter += 1 if result["matching"] else 0
            if update_progressbar(rawlogPosition, self.sourceModel().rowCount(None)) == True:
                self.clearFilter()
                break
        self.visibilityList[-1]["end"] = rawlogPosition

        if error != None:
            self.clearFilter()
            return (error, self.visibleCounter) 

        for item in self.visibilityList:
            if item["visibility"]:
                self.beginInsertRows(self.createIndex(0, 0), item["start"], item["end"]+1)
                for index in range(item["start"], item["end"]+1):
                    if self.proxyData.getVisibility(index, index+1) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endInsertRows()                    
            else:
                self.beginRemoveRows(self.createIndex(0, 0), item["start"], item["end"]+1)
                for index in range(item["start"], item["end"]+1):
                    if self.proxyData.getVisibility(index, index+1) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endRemoveRows()

        return (error, self.visibleCounter) 
    
    def clearFilter(self):
        self.visibilityList = []
        self.visibleCounter = self.sourceModel().rowCount(None)

        self.beginInsertRows(self.createIndex(0, 0), 0, self.visibleCounter+1)
        for index in range(self.visibleCounter+1):
            if self.proxyData.getVisibility(index, index+1) != True:
                self.proxyData.setVisibilityAtIndex(index, True)
        self.endInsertRows()

    def addToVisibilityList(self, index, visibility):
        if len(self.visibilityList) == 0:
            self.visibilityList.append({"start": index, "end": None, "visibility": visibility})
        elif self.visibilityList[-1]["visibility"] != visibility:
            self.visibilityList[-1]["end"] = index-1
            self.visibilityList.append({"start": index, "end": None, "visibility": visibility})