import logging
from LogViewer.utils.queryhelpers import QueryStatus, matchQuery

logger = logging.getLogger(__name__)

class Search:
    PREVIOUS = -1
    NEXT = 1

    def __init__(self, rawlog, query, update_progressbar=None):
        super().__init__()
        self.query = query
        self.resultList = []
        self.status = QueryStatus.QUERY_OK

        for index in range(len(rawlog)):
            # Presearch filter is expecting a finished rawlog loading
            result = matchQuery(query, rawlog, index, preSearchFilter=self._preSearchFilter)
            if result["matching"]:
                self.resultList.append(index)
            if result["status"] == QueryStatus.QUERY_ERROR:
                self.status = result["status"]
            if update_progressbar != None:
                update_progressbar(index, len(rawlog))
        if len(self.resultList) == 0:
            self.status = QueryStatus.QUERY_EMPTY

        self.resultIndex = -1           # don't jump over the first result on start
        self.resultStartIndex = 0       # the initial EOF point is the first result (e.g. result index 0)

    def _preSearchFilter(self, resultIndex, rawlog):
        if rawlog[resultIndex]["uiItem"].isHidden() == False:
            return True
        return False

    def _setResultStartIndex(self):
        # TODO: only set this if the user clicked on a logline, not when jumping to next search result
        self.resultStartIndex = self.resultIndex
    
    def _setStartIndex(self, startIndex, direction):
        if direction == Search.NEXT:
            resultIndexList = range(len(self.resultList)-1, -1, -1)
        elif direction == Search.PREVIOUS:
            resultIndexList = range(len(self.resultList))
        else:
            raise RuntimeError("Unexpected search direction: %s" % str(direction))
        found = False
        for resultIndex in resultIndexList:
            if (direction == Search.NEXT and self.resultList[resultIndex] <= startIndex) or (direction == Search.PREVIOUS and self.resultList[resultIndex] >= startIndex):
                self.resultIndex = resultIndex
                self._setResultStartIndex()
                found = True
                break
        # if we could not find any search result preceeding (for NEXT) or following (for PREVIOUS) our current startIndex,
        # we have to round wrap and select the last search result one (for NEXT) or the first one (for PREVIOS)
        # --> searching will again round wrap increment/decrement the self.resultIndex to the first result (for NEXT) or last result (for PREVIOS)
        if not found:
            if direction == Search.NEXT:
                self.resultIndex = len(self.resultList)-1
                self._setResultStartIndex()
            elif direction == Search.PREVIOUS:
                self.resultIndex = 0
                self._setResultStartIndex()
            else:
                raise RuntimeError("Unexpected search direction: %s" % str(direction))

    def next(self, startIndex=None):
        if len(self.resultList) == 0:
            return None
        
        # if no (new) start index is provided, we just return the next result starting from our current result
        if startIndex != None:
            self._setStartIndex(startIndex, Search.NEXT)

        self.resultIndex += 1
        if self.resultIndex >= len(self.resultList):
            self.resultIndex = 0

        if self.resultIndex == self.resultStartIndex:
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()
    
    def previous(self, startIndex=None):
        if len(self.resultList) == 0:
            return None
        
        # if no (new) start index is provided, we just return the next result starting from our current result
        if startIndex != None:
            self._setStartIndex(startIndex, Search.PREVIOUS)

        self.resultIndex -= 1
        if self.resultIndex < 0:
            self.resultIndex = len(self.resultList) - 1

        if self.resultIndex == self.resultStartIndex:
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()

    def getStatus(self):
        return self.status
    
    def getQuery(self):
        return self.query
    
    def getCurrentResult(self):
        if len(self.resultList) == 0:
            return None
        return self.resultList[self.resultIndex]
    
    def __len__(self):
        return len(self.resultList)

    def getPosition(self):
        return self.resultIndex + 1
    