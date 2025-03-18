from LogViewer.storage import SettingsSingleton
from LogViewer.utils import QueryStatus, matchQuery

import logging
logger = logging.getLogger(__name__)

from .proxy_model import ProxyModel

class FilterModel(ProxyModel):
    def __init__(self, sourceModel, parent=None):
        logger.debug(f"Creating new filter model for source: {sourceModel.__class__.__name__}")
        super().__init__(sourceModel, parent, handledSignals=[
            "rowsAboutToBeInserted",
            "rowsInserted"
        ])
        self.last_insert_event = None
        self.clearFilter()

        self.sourceModel().rowsAboutToBeInserted.connect(self.processRowsAboutToBeInserted)
        self.sourceModel().rowsInserted.connect(self.processRowsInserted)

    def processRowsAboutToBeInserted(self, parent, start, end):
        # we will delay emiting our rowsAboutToBeInserted signal until our underlying model
        # inserted all rows and we manged to filter them
        logger.debug(f"New rows from underlying model are about to be inserted: {start=}, {end=}")
        self.last_insert_event = {"start": start, "end": end}

    def processRowsInserted(self, *args):
        logger.debug("New rows from underlying model were inserted, filtering now...")
        # set default value for these new rows to False to make sure they are inserted by our _filterTemplate
        self.proxyData.insertRows(self.last_insert_event["start"], self.last_insert_event["end"], False)
        # make sure we only handle NEW items to not handle everything n-times because fill up our visibility list
        self._initVisibilityList()
        # this will call beginInsertRows() (thus emit rowsAboutToBeInserted)
        # and endInsertRows() (thus emit rowsInserted)
        # end values are inclusive (see https://doc.qt.io/qt-6/qabstractitemmodel.html#rowsAboutToBeInserted), but range() is exclusive
        # --> fix this by adding 1
        self._filterTemplate(self.query, start=self.last_insert_event["start"], end=self.last_insert_event["end"]+1)

    def rowCount(self, index):
        return self.visibleCounter
    
    def isRowVisible(self, index):
        if index < 0 or index >= self.sourceModel().rowCount(None):
            return False
        return self.proxyData.getVisibility(index)

    def filter(self, query, update_progressbar=None):
        self.query = query
        self.visibleCounter = 0
        
        self._initVisibilityList()
        return self._filterTemplate(self.query, start=0, end=self.sourceModel().rowCount(None), update_progressbar=update_progressbar)

    def _filterTemplate(self, query, start, end, update_progressbar=None):
        logger.debug(f"Filtering from {start=} to {end=} on a model having {self.sourceModel().rowCount(None)} rows using query: {query}")
        error = None
        for rawlogPosition in range(start, end):
            result = matchQuery(query, self.sourceModel().rawlog, rawlogPosition, usePython=SettingsSingleton()["usePythonFilter"])
            #logger.debug(f"{rawlogPosition}: {result}")
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
        visibilityList = self._sealVisibilityList(self.sourceModel().rowCount(None))

        if error != None:
            self.clearFilter()
            return (error, self.visibleCounter) 

        logger.debug(f"Our visibility list[{self.visibleCounter}] is now: {visibilityList}")
        for item in visibilityList:
            if item["visibility"]:
                self.beginInsertRows(self.parent(), item["start"], item["end"])
                for index in range(item["start"], item["end"]+1):
                    if self.proxyData.getVisibility(index) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endInsertRows()                    
            else:
                self.beginRemoveRows(self.parent(), item["start"], item["end"])
                for index in range(item["start"], item["end"]+1):
                    if self.proxyData.getVisibility(index) != item["visibility"]:
                        self.proxyData.setVisibilityAtIndex(index, item["visibility"])
                self.endRemoveRows()

        return (error, self.visibleCounter) 
    
    def clearFilter(self):
        # The query must be of string type
        self.query = "True"
        self._initVisibilityList()
        self.visibleCounter = self.sourceModel().rowCount(None)
        self.beginInsertRows(self.parent(), 0, self.visibleCounter+1)
        self.proxyData.clear(True)
        self.endInsertRows()
