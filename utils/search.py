import logging
from .queryhelpers import QueryStatus, matchQuery

logger = logging.getLogger(__name__)

class Search:
    PREVIOUS = -1
    NEXT = 1

    def __init__(self, rawlog, query):
        super().__init__()
        self.query = query
        self.filteredList = []
        self.status = QueryStatus.QUERY_OK
        for index in range(len(rawlog)):
            # Presearch filter is expecting a finished rawlog loading
            result = matchQuery(query, rawlog, index, preSearchFilter=self._preSearchFilter)
            if result["matching"]:
                self.filteredList.append(index)
            if result["status"] == QueryStatus.QUERY_ERROR:
                self.status = result["status"]
        if len(self.filteredList) == 0:
            self.status = QueryStatus.QUERY_EMPTY

        self.resultIndex = -1           # don't jump over the first result on start
        self.resultStartIndex = 0       # the initial EOF point is the first result (e.g. result index 0)

    def _preSearchFilter(self, resultIndex, rawlog):
        if rawlog[resultIndex]["uiItem"].isHidden() == False:
            return True
        return False

    def _setStartIndex(self, startIndex, direction):
        self.resultIndex = 0
        if direction == Search.NEXT:
            indexList = range(len(self.filteredList)-1, -1, -1)
        elif direction == Search.PREVIOUS:
            indexList = range(len(self.filteredList))
        else:
            raise RuntimeError("Unexpected search direction: %s" % str(direction))
        for resultIndex in indexList:
            if (direction == Search.NEXT and self.filteredList[resultIndex] <= startIndex) or (direction == Search.PREVIOUS and self.filteredList[resultIndex] >= startIndex):
                self.resultIndex = resultIndex
                self.resultStartIndex = resultIndex
                break

    def next(self, startIndex=None):
        if len(self.filteredList) == 0:
            return None
        
        # if no (new) start index is provided, we just return the next result starting from our current result
        if startIndex != None:
            self._setStartIndex(startIndex, Search.NEXT)

        self.resultIndex += 1
        if self.resultIndex >= len(self.filteredList):
            self.resultIndex = 0

        if self.resultIndex == self.resultStartIndex:
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()
    
    def previous(self, startIndex=None):
        if len(self.filteredList) == 0:
            return None
        
        # if no (new) start index is provided, we just return the next result starting from our current result
        if startIndex != None:
            self._setStartIndex(startIndex, Search.PREVIOUS)

        self.resultIndex -= 1
        if self.resultIndex < 0:
            self.resultIndex = len(self.filteredList) - 1

        if self.resultIndex == self.resultStartIndex:
            self.status = QueryStatus.EOF_REACHED

        return self.getCurrentResult()

    def getStatus(self):
        return self.status
    
    def getQuery(self):
        return self.query
    
    def getCurrentResult(self):
        if len(self.filteredList) == 0:
            return None
        return self.filteredList[self.resultIndex]
    
    def __len__(self):
        return len(self.filteredList)

    def getPosition(self):
        return self.resultIndex + 1
