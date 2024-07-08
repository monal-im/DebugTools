from LogViewer.storage import SettingsSingleton
from LogViewer.utils import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, sourceModel, parent=None):
        super().__init__(sourceModel, parent)
        self.clearFilter()

    def rowCount(self, index):
        return self.visibleCounter
    
    def isRowVisible(self, index):
        if index < 0 or index >= self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index, index+1)

    def filter(self, query, update_progressbar):
        self.visibleCounter = 0        
        error = None

        for rawlogPosition in range(self.sourceModel().rowCount(None)):
            result = matchQuery(query, self.sourceModel().rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            if result["status"] == QueryStatus.QUERY_OK:
                self.proxyData.setVisibilityAtIndex(rawlogPosition, result["matching"]) 

            else:
                error = result["error"]
                self.proxyData.setVisibilityAtIndex(rawlogPosition, False) # hide all entries having filter errors
            self.visibleCounter += 1 if result["matching"] else 0
            if update_progressbar(rawlogPosition, self.sourceModel().rowCount(None)) == True:
                self.clearFilter()
                break

        return (error, self.visibleCounter) 
    
    def clearFilter(self):
        self.proxyData.clear(True)
        self.visibleCounter = self.sourceModel().rowCount(None)
